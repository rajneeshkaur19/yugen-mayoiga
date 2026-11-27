"""Story Context Builder for the Yūgen Mayoiga AI subsystem.

Responsibilities
----------------
- Read the current story, scene, state, characters, relationships,
  memories and recent player history from the database.
- Assemble a clean, serialisable :class:`StoryAIContext` object.
- Delegate memory retrieval to the existing ``memory_service`` so the
  DSA-based retrieval algorithm is reused, not duplicated.

Guarantees
----------
- **Read-only**: this module never writes to the database or mutates any
  model, engine, or service state.
- **No raw ORM objects** flow into the returned context — every field is a
  plain Python value or a Pydantic model.
- **Graceful degradation**: optional fields (scene, characters, memories,
  relationships, history) are omitted or left empty when not available.
  Real database errors are **not** swallowed.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ai.schemas import (
    CharacterContext,
    CharacterEmotionContext,
    CharacterTraitsContext,
    HistoryEntryContext,
    MemoryContext,
    PlayerInputContext,
    RelationshipContext,
    SceneContext,
    StoryAIContext,
    StoryRuntimeContext,
)
from backend.app.models.character import Character
from backend.app.models.character_traits import CharacterTraits
from backend.app.models.choice import Choice
from backend.app.models.relationship import Relationship
from backend.app.models.scene import Scene
from backend.app.models.story import Story
from backend.app.models.story_state import StoryState
from backend.app.models.user_choices_log import UserChoicesLog
from backend.app.services.emotion_engine import get_character_emotions_dict
from backend.app.services.memory_service import retrieve_relevant_memories
from backend.app.services.world_state_engine import get_all_world_vars


# ---------------------------------------------------------------------------
# Public constants (can be overridden per-call)
# ---------------------------------------------------------------------------

DEFAULT_MEMORY_LIMIT: int = 5
"""Maximum number of memories retrieved per context build."""

DEFAULT_HISTORY_LIMIT: int = 5
"""Maximum number of recent turns included in context."""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_scene_context(scene: Scene) -> SceneContext:
    """Convert a SQLAlchemy Scene row to a SceneContext."""
    return SceneContext(
        id=scene.id,
        story_id=scene.story_id,
        scene_number=scene.scene_number,
        location=scene.location,
        mood=scene.mood,
        content=scene.content,
        haiku=scene.haiku,
        is_ending=scene.is_ending,
    )


def _build_traits_context(traits: CharacterTraits) -> CharacterTraitsContext:
    """Convert a SQLAlchemy CharacterTraits row to a CharacterTraitsContext."""
    return CharacterTraitsContext(
        openness=traits.openness,
        conscientiousness=traits.conscientiousness,
        extraversion=traits.extraversion,
        agreeableness=traits.agreeableness,
        neuroticism=traits.neuroticism,
    )


def _build_character_context(
    db: Session,
    story_id: int,
    character: Character,
) -> CharacterContext:
    """Build a full CharacterContext from a Character row + live emotion data."""
    emotions_dict = get_character_emotions_dict(db, story_id, character.id)
    emotions = CharacterEmotionContext(
        fear=emotions_dict["fear"],
        anxiety=emotions_dict["anxiety"],
        anger=emotions_dict["anger"],
        sadness=emotions_dict["sadness"],
        happiness=emotions_dict["happiness"],
        trust=emotions_dict["trust"],
    )

    raw_traits = db.get(CharacterTraits, character.id)
    traits = _build_traits_context(raw_traits) if raw_traits is not None else None

    return CharacterContext(
        id=character.id,
        name=character.name,
        role=character.role,
        age=character.age,
        background=character.background,
        goals=list(character.goals),
        fears=list(character.fears),
        secrets=list(character.secrets),
        emotions=emotions,
        traits=traits,
    )


def _build_relationship_contexts(
    db: Session,
    story_id: int,
    name_map: dict[int, str],
) -> list[RelationshipContext]:
    """Return all directed relationships for the story as RelationshipContext objects."""
    rows = list(
        db.scalars(
            select(Relationship)
            .where(Relationship.story_id == story_id)
            .order_by(Relationship.id)
        ).all()
    )
    result: list[RelationshipContext] = []
    for rel in rows:
        result.append(
            RelationshipContext(
                from_character_id=rel.from_character,
                from_character_name=name_map.get(rel.from_character, f"char_{rel.from_character}"),
                to_character_id=rel.to_character,
                to_character_name=name_map.get(rel.to_character, f"char_{rel.to_character}"),
                trust=rel.trust,
                friendship=rel.friendship,
                suspicion=rel.suspicion,
                fear=rel.fear,
                dependency=rel.dependency,
            )
        )
    return result


def _build_memory_query(scene: Optional[Scene], player_input: Optional[PlayerInputContext]) -> str:
    """Compose a plain-text query string for the memory retrieval algorithm.

    The query is derived from available scene and player input data.
    When nothing is available a minimal fallback is returned.
    """
    parts: list[str] = []
    if scene is not None:
        parts.append(scene.location)
        parts.append(scene.mood)
        # Include first 50 chars of scene content for keyword overlap
        parts.append(scene.content[:50])
    if player_input is not None:
        if player_input.choice_text:
            parts.append(player_input.choice_text[:80])
        elif player_input.free_text:
            parts.append(player_input.free_text[:80])
        elif player_input.parsed_action:
            parts.append(player_input.parsed_action)
    return " ".join(parts) if parts else "story"


def _build_memory_contexts(
    db: Session,
    story_id: int,
    current_turn: int,
    name_map: dict[int, str],
    query: str,
    limit: int,
) -> list[MemoryContext]:
    """Retrieve top-k relevant memories and convert them to MemoryContext."""
    scored = retrieve_relevant_memories(
        db=db,
        story_id=story_id,
        query=query,
        current_turn=current_turn,
        k=limit,
    )
    result: list[MemoryContext] = []
    for memory, score in scored:
        result.append(
            MemoryContext(
                id=memory.id,
                character_id=memory.character_id,
                character_name=name_map.get(memory.character_id),
                event=memory.event,
                type=memory.type,  # type: ignore[arg-type]
                importance=memory.importance,
                emotional_weight=memory.emotional_weight,
                status=memory.status,  # type: ignore[arg-type]
                created_turn=memory.created_turn,
                relevance_score=round(score, 6),
            )
        )
    return result


def _build_history_contexts(
    db: Session,
    story_id: int,
    limit: int,
) -> list[HistoryEntryContext]:
    """Retrieve the most recent player actions (bounded by *limit*) with choices and scene locations."""
    rows = list(
        db.scalars(
            select(UserChoicesLog)
            .where(
                UserChoicesLog.story_id == story_id,
                UserChoicesLog.undone.is_(False),
            )
            .order_by(UserChoicesLog.turn_number.desc())
            .limit(limit)
        ).all()
    )
    # Return in ascending turn order so the AI sees history chronologically
    rows.reverse()

    choice_ids = [r.choice_id for r in rows if r.choice_id is not None]
    scene_ids = [r.scene_id for r in rows if r.scene_id is not None]

    choice_map: dict[int, str] = {}
    if choice_ids:
        choice_rows = list(
            db.scalars(select(Choice).where(Choice.id.in_(choice_ids))).all()
        )
        choice_map = {c.id: c.choice_text for c in choice_rows}

    scene_map: dict[int, str] = {}
    if scene_ids:
        scene_rows = list(
            db.scalars(select(Scene).where(Scene.id.in_(scene_ids))).all()
        )
        scene_map = {s.id: s.location for s in scene_rows}

    result: list[HistoryEntryContext] = []
    for row in rows:
        resolved_choice = (
            choice_map.get(row.choice_id)
            if row.choice_id is not None
            else None
        )
        result.append(
            HistoryEntryContext(
                turn_number=row.turn_number,
                scene_id=row.scene_id,
                scene_location=scene_map.get(row.scene_id),
                choice_text=resolved_choice,
                free_text=row.free_text,
                parsed_action=row.parsed_action,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class StoryContextBuilder:
    """Assembles a :class:`StoryAIContext` from live database state.

    Usage::

        builder = StoryContextBuilder(db)
        context = builder.build(story_id=42, player_input=player_input)

    The resulting :class:`StoryAIContext` is fully serialisable and contains
    no SQLAlchemy objects.  It is safe to pass to any AI provider adapter.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def build(
        self,
        story_id: int,
        *,
        player_input: Optional[PlayerInputContext] = None,
        memory_limit: int = DEFAULT_MEMORY_LIMIT,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> StoryAIContext:
        """Build and return a :class:`StoryAIContext` for the given story.

        Parameters
        ----------
        story_id:
            The story playthrough to build context for.
        player_input:
            Optional description of the player's most recent action.
        memory_limit:
            Maximum number of relevant memories to include.
        history_limit:
            Maximum number of recent turns to include in history.

        Returns
        -------
        StoryAIContext
            A fully populated, serialisable AI context.

        Raises
        ------
        ValueError
            If the story with *story_id* does not exist.
        """
        db = self._db

        # ── 1. Load story ────────────────────────────────────────────────────
        story: Optional[Story] = db.get(Story, story_id)
        if story is None:
            raise ValueError(f"Story {story_id} not found.")

        # ── 2. Load runtime state (may be None for brand-new stories) ────────
        story_state: Optional[StoryState] = db.scalar(
            select(StoryState).where(StoryState.story_id == story_id)
        )

        turn_number: int = story_state.turn_number if story_state is not None else 0
        yugen_meter: int = story_state.yugen_meter if story_state is not None else 0
        hidden_variables: dict[str, Any] = (
            dict(story_state.hidden_variables) if story_state is not None else {}
        )
        world_state: dict[str, Any] = get_all_world_vars(db, story_id)

        runtime = StoryRuntimeContext(
            turn_number=turn_number,
            yugen_meter=yugen_meter,
            hidden_variables=hidden_variables,
            world_state=world_state,
        )

        # ── 3. Load current and preceding scenes ──────────────────────────────
        current_scene: Optional[SceneContext] = None
        previous_scene: Optional[SceneContext] = None
        raw_scene: Optional[Scene] = None
        if story_state is not None:
            raw_scene = db.scalar(
                select(Scene).where(
                    Scene.id == story_state.current_scene_id,
                    Scene.story_id == story_id,
                )
            )
            if raw_scene is not None:
                current_scene = _build_scene_context(raw_scene)

        # Inspect last action log entry to identify preceding scene if transitioned
        last_log = db.scalar(
            select(UserChoicesLog)
            .where(
                UserChoicesLog.story_id == story_id,
                UserChoicesLog.undone.is_(False),
            )
            .order_by(UserChoicesLog.turn_number.desc())
            .limit(1)
        )
        if (
            last_log is not None
            and story_state is not None
            and last_log.scene_id != story_state.current_scene_id
        ):
            raw_prev = db.scalar(
                select(Scene).where(
                    Scene.id == last_log.scene_id,
                    Scene.story_id == story_id,
                )
            )
            if raw_prev is not None:
                previous_scene = _build_scene_context(raw_prev)

        # ── 4. Load characters ────────────────────────────────────────────────
        raw_characters: list[Character] = list(
            db.scalars(
                select(Character)
                .where(Character.story_id == story_id)
                .order_by(Character.id)
            ).all()
        )
        character_contexts: list[CharacterContext] = [
            _build_character_context(db, story_id, char)
            for char in raw_characters
        ]
        # Build a name lookup for relationships and memories
        name_map: dict[int, str] = {c.id: c.name for c in raw_characters}

        # ── 5. Load relationships ─────────────────────────────────────────────
        relationship_contexts = _build_relationship_contexts(db, story_id, name_map)

        # ── 6. Retrieve relevant memories via existing memory service ─────────
        memory_query = _build_memory_query(raw_scene, player_input)
        memory_contexts = _build_memory_contexts(
            db=db,
            story_id=story_id,
            current_turn=turn_number,
            name_map=name_map,
            query=memory_query,
            limit=memory_limit,
        )

        # ── 7. Load recent history ────────────────────────────────────────────
        history_contexts = _build_history_contexts(db, story_id, history_limit)

        # ── 8. Assemble and return ────────────────────────────────────────────
        return StoryAIContext(
            story_id=story.id,
            story_title=story.title,
            story_theme=story.theme,
            story_genre=story.genre,
            story_tone=story.tone,
            story_season=story.season,
            story_length=story.length,
            story_language=story.story_language or "English",
            story_status=story.status,
            current_scene=current_scene,
            previous_scene=previous_scene,
            runtime=runtime,
            characters=character_contexts,
            relationships=relationship_contexts,
            relevant_memories=memory_contexts,
            recent_history=history_contexts,
            player_input=player_input,
            memory_limit=memory_limit,
            history_limit=history_limit,
        )
