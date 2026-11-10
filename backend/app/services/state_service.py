"""Service operations for story state management."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.story_state import StoryState
from backend.app.models.scene import Scene


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
) -> StoryState:
    if not _scene_in_story(db, story_id, current_scene_id):
        raise ValueError("Current scene does not belong to this story")

    state = StoryState(
        story_id=story_id,
        current_scene_id=current_scene_id,
    )
    try:
        db.add(state)
        db.commit()
        db.refresh(state)
        return state
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A story state already exists for this playthrough"
        ) from exc
    except Exception:
        db.rollback()
        raise


def advance_story_state(
    db: Session,
    story_id: int,
    new_scene_id: int,
    hidden_variables: dict | None = None,
    yugen_meter_delta: int = 0,
) -> StoryState | None:
    """Advance turn, move to new scene, optionally update hidden variables."""
    state = get_story_state(db, story_id)
    if state is None:
        return None

    if not _scene_in_story(db, story_id, new_scene_id):
        raise ValueError("Target scene does not belong to this story")

    try:
        state.current_scene_id = new_scene_id
        state.turn_number += 1
        state.yugen_meter = max(
            0, min(100, state.yugen_meter + yugen_meter_delta)
        )
        if hidden_variables:
            merged = dict(state.hidden_variables)
            merged.update(hidden_variables)
            state.hidden_variables = merged
        state.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(state)
        return state
    except Exception:
        db.rollback()
        raise
