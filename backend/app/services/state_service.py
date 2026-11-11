"""Service operations for story state, hidden variables, and Yūgen Meter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from algorithms.state_store import clamp
from backend.app.models.character import Character
from backend.app.models.character_state import CharacterState
from backend.app.models.relationship import Relationship
from backend.app.models.scene import Scene
from backend.app.models.story_state import StoryState
from backend.app.models.world_state import WorldState
from backend.app.services.emotion_engine import get_character_emotions_dict
from backend.app.services.world_state_engine import get_all_world_vars


def _scene_in_story(db: Session, story_id: int, scene_id: int) -> bool:
    return (
        db.scalar(
            select(Scene.id).where(
                Scene.id == scene_id,
                Scene.story_id == story_id,
            )
        )
        is not None
    )


def get_story_state(db: Session, story_id: int) -> StoryState | None:
    return db.scalar(
        select(StoryState).where(StoryState.story_id == story_id)
    )



def create_story_state(
    db: Session,
    story_id: int,
    current_scene_id: int,
    initial_hidden_variables: dict[str, Any] | None = None,
    initial_yugen_meter: int = 50,
    commit: bool = True,
) -> StoryState:
    if not _scene_in_story(db, story_id, current_scene_id):
        raise ValueError("Current scene does not belong to this story")

    state = StoryState(
        story_id=story_id,
        current_scene_id=current_scene_id,
        hidden_variables=initial_hidden_variables or {},
        yugen_meter=clamp(initial_yugen_meter),
    )
    try:
        db.add(state)
        if commit:
            db.commit()
            db.refresh(state)
        else:
            db.flush()
        return state
    except IntegrityError as exc:
        if commit:
            db.rollback()
        raise ValueError(
            "A story state already exists for this playthrough"
        ) from exc
    except Exception:
        if commit:
            db.rollback()
        raise




def get_or_create_story_state(
    db: Session,
    story_id: int,
    fallback_scene_id: int | None = None,
    commit: bool = True,
) -> StoryState:
    """Retrieve existing story state or initialize from the story's first scene."""
    state = get_story_state(db, story_id)
    if state is not None:
        return state

    scene_id = fallback_scene_id
    if scene_id is None:
        first_scene = db.scalar(
            select(Scene)
            .where(Scene.story_id == story_id)
            .order_by(Scene.scene_number)
        )
        if first_scene is None:
            raise ValueError(f"Story {story_id} has no scenes defined.")
        scene_id = first_scene.id

    return create_story_state(db, story_id, scene_id, commit=commit)



def update_hidden_variables(
    db: Session,
    story_id: int,
    deltas_or_updates: dict[str, Any],
) -> dict[str, Any]:
    """Update hidden variables in story_states."""
    state = get_or_create_story_state(db, story_id)
    curr = dict(state.hidden_variables)
    for k, v in deltas_or_updates.items():
        if k.endswith("_delta") and isinstance(v, (int, float)):
            actual_key = k[:-6]
            curr[actual_key] = curr.get(actual_key, 0) + v
        else:
            curr[k] = v

    state.hidden_variables = curr
    state.updated_at = datetime.now(timezone.utc)
    return curr


def update_yugen_meter(
    db: Session,
    story_id: int,
    delta: int,
) -> int:
    """Adjust the Yūgen Meter (0-100) representing unresolved mystery."""
    state = get_or_create_story_state(db, story_id)
    new_meter = clamp(state.yugen_meter + delta)
    state.yugen_meter = new_meter
    state.updated_at = datetime.now(timezone.utc)
    return new_meter


def get_unified_story_state(
    db: Session,
    story_id: int,
    include_hidden: bool = True,
) -> dict[str, Any]:
    """Build a unified dictionary of all runtime states for evaluation or API display.

    Combines:
    - story_state: turn_number, current_scene_id, yugen_meter
    - world_state: all key-values
    - character_emotions: latest for each character
    - relationships: directed pairs
    - hidden_variables: if include_hidden is True
    """
    state_row = get_or_create_story_state(db, story_id)
    world = get_all_world_vars(db, story_id)

    # Characters in story
    characters = list(
        db.scalars(
            select(Character).where(Character.story_id == story_id)
        ).all()
    )

    char_states: dict[int, dict[str, Any]] = {}
    primary_emotions: dict[str, int] = {}
    for c in characters:
        emos = get_character_emotions_dict(db, story_id, c.id)
        char_states[c.id] = {
            "name": c.name,
            "role": c.role,
            "emotions": emos,
        }
        # First character or protagonist emotions used as top-level fallback
        if not primary_emotions:
            primary_emotions = emos

    # Relationships in story
    rels = list(
        db.scalars(
            select(Relationship).where(Relationship.story_id == story_id)
        ).all()
    )
    rel_map: dict[str, dict[str, int]] = {}
    for r in rels:
        rel_map[f"{r.from_character}->{r.to_character}"] = {
            "trust": r.trust,
            "friendship": r.friendship,
            "suspicion": r.suspicion,
            "fear": r.fear,
            "dependency": r.dependency,
        }

    unified: dict[str, Any] = {
        "story_id": story_id,
        "current_scene_id": state_row.current_scene_id,
        "turn_number": state_row.turn_number,
        "yugen_meter": state_row.yugen_meter,
        "world_state": world,
        "characters": char_states,
        "relationships": rel_map,
    }

    # Flatten common emotion and world keys at top-level for simple condition evaluation
    unified.update(primary_emotions)
    unified.update(world)

    if include_hidden:
        unified["hidden_variables"] = state_row.hidden_variables
        unified.update(state_row.hidden_variables)

    return unified
