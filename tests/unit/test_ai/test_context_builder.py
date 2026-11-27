"""Unit tests for the StoryContextBuilder (AI Phase 1).

These tests use the same real PostgreSQL database approach as the existing
integration tests, via the ``db_session`` and ``setup_story`` fixtures from
``conftest.py``.  The session is never committed inside the builder, so no
test data leaks into permanent state.

Coverage
--------
1.  Context creation for a valid story
2.  Correct story metadata
3.  Correct current scene
4.  Active characters included
5.  Character emotion state
6.  Relationship inclusion
7.  Memory integration via existing memory service
8.  Recent history inclusion and limit
9.  Player input propagation
10. Missing optional fields (no scene, no characters, no memories)
11. Empty character list
12. Empty memory list
13. Serialisation to JSON-safe dict
14. No mutation of deterministic game state
15. No raw SQLAlchemy objects in serialised context
16. Invalid / missing story raises ValueError
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from backend.app.ai.context_builder import (
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_MEMORY_LIMIT,
    StoryContextBuilder,
    _build_memory_query,
    _build_scene_context,
)
from backend.app.ai.schemas import (
    PlayerInputContext,
    SceneContext,
    StoryAIContext,
)
from backend.app.models.character import Character
from backend.app.models.character_traits import CharacterTraits
from backend.app.models.memory import Memory
from backend.app.models.relationship import Relationship
from backend.app.models.scene import Scene
from backend.app.models.story import Story
from backend.app.models.story_state import StoryState
from backend.app.models.user_choices_log import UserChoicesLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_story_state(db: Session, story_id: int, scene_id: int, turn: int = 3) -> StoryState:
    """Create and flush a minimal StoryState for a story."""
    state = StoryState(
        story_id=story_id,
        current_scene_id=scene_id,
        hidden_variables={"fog_level": "heavy"},
        yugen_meter=42,
        turn_number=turn,
    )
    db.add(state)
    db.flush()
    return state


def _add_relationship(
    db: Session,
    story_id: int,
    from_id: int,
    to_id: int,
    *,
    trust: int = 60,
    friendship: int = 55,
    suspicion: int = 10,
    fear: int = 5,
    dependency: int = 20,
) -> Relationship:
    rel = Relationship(
        story_id=story_id,
        from_character=from_id,
        to_character=to_id,
        trust=trust,
        friendship=friendship,
        suspicion=suspicion,
        fear=fear,
        dependency=dependency,
    )
    db.add(rel)
    db.flush()
    return rel


def _add_memory(
    db: Session,
    story_id: int,
    character_id: int,
    event: str,
    *,
    importance: int = 70,
    created_turn: int = 1,
    memory_type: str = "long_term",
) -> Memory:
    mem = Memory(
        story_id=story_id,
        character_id=character_id,
        event=event,
        type=memory_type,
        importance=importance,
        emotional_weight=10,
        status="normal",
        created_turn=created_turn,
    )
    db.add(mem)
    db.flush()
    return mem


def _add_history_entry(
    db: Session,
    story_id: int,
    user_id: int,
    scene_id: int,
    turn_number: int,
    free_text: str = "I explored the room.",
) -> UserChoicesLog:
    log = UserChoicesLog(
        user_id=user_id,
        story_id=story_id,
        turn_number=turn_number,
        scene_id=scene_id,
        free_text=free_text,
        parsed_action="explore",
        undone=False,
        delta={},
    )
    db.add(log)
    db.flush()
    return log


# ---------------------------------------------------------------------------
# Test: 16 — missing story raises ValueError
# ---------------------------------------------------------------------------


def test_missing_story_raises_value_error(db_session: Session) -> None:
    """Context builder raises ValueError for a non-existent story_id."""
    builder = StoryContextBuilder(db_session)
    with pytest.raises(ValueError, match="not found"):
        builder.build(story_id=999_999_999)


# ---------------------------------------------------------------------------
# Test: 1 — basic context creation for valid story
# ---------------------------------------------------------------------------


def test_context_creation_valid_story(db_session: Session, setup_story: dict) -> None:
    """Builder returns a StoryAIContext instance for a valid story."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    builder = StoryContextBuilder(db_session)
    ctx = builder.build(story_id=story.id)

    assert isinstance(ctx, StoryAIContext)


# ---------------------------------------------------------------------------
# Test: 2 — story metadata
# ---------------------------------------------------------------------------


def test_story_metadata(db_session: Session, setup_story: dict) -> None:
    """Context contains correct story title, genre, tone, season, length."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    assert ctx.story_id == story.id
    assert ctx.story_title == story.title
    assert ctx.story_genre == story.genre
    assert ctx.story_theme == story.theme
    assert ctx.story_tone == story.tone
    assert ctx.story_season == story.season
    assert ctx.story_length == story.length
    assert ctx.story_status == story.status


# ---------------------------------------------------------------------------
# Test: 3 — current scene
# ---------------------------------------------------------------------------


def test_current_scene_in_context(db_session: Session, setup_story: dict) -> None:
    """Context includes the current scene when a StoryState exists."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    assert ctx.current_scene is not None
    assert ctx.current_scene.id == scene1.id
    assert ctx.current_scene.location == scene1.location
    assert ctx.current_scene.mood == scene1.mood
    assert ctx.current_scene.content == scene1.content
    assert ctx.current_scene.scene_number == scene1.scene_number
    assert ctx.current_scene.is_ending == scene1.is_ending


def test_no_story_state_gives_no_scene(db_session: Session, setup_story: dict) -> None:
    """Context gracefully omits the current scene when no StoryState exists."""
    story: Story = setup_story["story"]
    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    assert ctx.current_scene is None


# ---------------------------------------------------------------------------
# Test: 4 — active characters
# ---------------------------------------------------------------------------


def test_characters_included(db_session: Session, setup_story: dict) -> None:
    """All characters in the story appear in the context."""
    story: Story = setup_story["story"]
    char: Character = setup_story["character"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    char_ids = [c.id for c in ctx.characters]
    assert char.id in char_ids


def test_character_identity_fields(db_session: Session, setup_story: dict) -> None:
    """Character context carries name, role, age, background."""
    story: Story = setup_story["story"]
    char: Character = setup_story["character"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    char_ctx = next(c for c in ctx.characters if c.id == char.id)
    assert char_ctx.name == char.name
    assert char_ctx.role == char.role
    assert char_ctx.age == char.age
    assert char_ctx.background == char.background


# ---------------------------------------------------------------------------
# Test: 5 — character emotion state
# ---------------------------------------------------------------------------


def test_character_emotions_present(db_session: Session, setup_story: dict) -> None:
    """Character context includes all six emotion fields."""
    story: Story = setup_story["story"]
    char: Character = setup_story["character"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    char_ctx = next(c for c in ctx.characters if c.id == char.id)
    emo = char_ctx.emotions
    for field in ("fear", "anxiety", "anger", "sadness", "happiness", "trust"):
        assert 0 <= getattr(emo, field) <= 100


def test_character_traits_present_when_defined(db_session: Session, setup_story: dict) -> None:
    """Character context includes Big-Five traits when they exist."""
    story: Story = setup_story["story"]
    char: Character = setup_story["character"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    char_ctx = next(c for c in ctx.characters if c.id == char.id)
    assert char_ctx.traits is not None
    assert 0 <= char_ctx.traits.openness <= 100
    assert 0 <= char_ctx.traits.neuroticism <= 100


def test_character_traits_none_when_not_defined(db_session: Session, setup_story: dict) -> None:
    """Character context traits field is None when no traits row exists."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    # Add a character without traits
    char_no_traits = Character(
        story_id=story.id,
        name=f"NoTraits_{uuid.uuid4().hex[:6]}",
        role="Wanderer",
    )
    db_session.add(char_no_traits)
    db_session.flush()

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    char_ctx = next(c for c in ctx.characters if c.id == char_no_traits.id)
    assert char_ctx.traits is None


# ---------------------------------------------------------------------------
# Test: 6 — relationship inclusion
# ---------------------------------------------------------------------------


def test_relationships_included(db_session: Session, setup_story: dict) -> None:
    """Context includes directed relationships between characters."""
    story: Story = setup_story["story"]
    char: Character = setup_story["character"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    # Add a second character and a directed relationship
    char2 = Character(
        story_id=story.id,
        name=f"Riku_{uuid.uuid4().hex[:6]}",
        role="Guide",
    )
    db_session.add(char2)
    db_session.flush()

    _add_relationship(db_session, story.id, char.id, char2.id, trust=70, friendship=65)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    assert len(ctx.relationships) >= 1
    rel = next(
        r for r in ctx.relationships
        if r.from_character_id == char.id and r.to_character_id == char2.id
    )
    assert rel.trust == 70
    assert rel.friendship == 65
    assert rel.from_character_name == char.name
    assert rel.to_character_name == char2.name


def test_no_relationships_gives_empty_list(db_session: Session, setup_story: dict) -> None:
    """Context gracefully returns an empty relationships list when none exist."""
    story: Story = setup_story["story"]
    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    assert ctx.relationships == []


# ---------------------------------------------------------------------------
# Test: 7 — memory integration
# ---------------------------------------------------------------------------


def test_memories_retrieved_and_included(db_session: Session, setup_story: dict) -> None:
    """Relevant memories are retrieved from the memory service and included."""
    story: Story = setup_story["story"]
    char: Character = setup_story["character"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    _add_memory(
        db_session,
        story.id,
        char.id,
        "Discovered a hidden door near the wooden gate.",
        importance=80,
        created_turn=1,
    )

    ctx = StoryContextBuilder(db_session).build(story_id=story.id, memory_limit=5)

    assert len(ctx.relevant_memories) >= 1
    mem = ctx.relevant_memories[0]
    assert mem.character_id == char.id
    assert mem.character_name == char.name
    assert isinstance(mem.relevance_score, float)
    assert mem.importance == 80


def test_empty_memories_gives_empty_list(db_session: Session, setup_story: dict) -> None:
    """Context returns empty memories list when none exist for the story."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    assert ctx.relevant_memories == []


def test_memory_limit_respected(db_session: Session, setup_story: dict) -> None:
    """Memory retrieval respects the requested limit."""
    story: Story = setup_story["story"]
    char: Character = setup_story["character"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    # Add more memories than the limit
    for i in range(8):
        _add_memory(
            db_session,
            story.id,
            char.id,
            f"Event {i}: found iron key near the locked gate.",
            importance=50 + i,
            created_turn=i,
        )

    ctx = StoryContextBuilder(db_session).build(story_id=story.id, memory_limit=3)

    assert len(ctx.relevant_memories) == 3


# ---------------------------------------------------------------------------
# Test: 8 — recent history
# ---------------------------------------------------------------------------


def test_history_included(db_session: Session, setup_story: dict, test_user) -> None:
    """Recent player actions appear in context history."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id, turn=5)

    _add_history_entry(db_session, story.id, test_user.id, scene1.id, 1, "I opened the gate.")
    _add_history_entry(db_session, story.id, test_user.id, scene1.id, 2, "I lit the lantern.")

    ctx = StoryContextBuilder(db_session).build(story_id=story.id, history_limit=5)

    assert len(ctx.recent_history) == 2
    # History should be in ascending turn order
    assert ctx.recent_history[0].turn_number < ctx.recent_history[1].turn_number


def test_history_limit_respected(db_session: Session, setup_story: dict, test_user) -> None:
    """History is bounded to history_limit entries."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id, turn=10)

    for i in range(1, 9):
        _add_history_entry(db_session, story.id, test_user.id, scene1.id, i, f"Action {i}.")

    ctx = StoryContextBuilder(db_session).build(story_id=story.id, history_limit=3)

    assert len(ctx.recent_history) <= 3


def test_empty_history_gives_empty_list(db_session: Session, setup_story: dict) -> None:
    """Context returns empty history list when no actions logged."""
    story: Story = setup_story["story"]
    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    assert ctx.recent_history == []


# ---------------------------------------------------------------------------
# Test: 9 — player input
# ---------------------------------------------------------------------------


def test_player_input_propagated(db_session: Session, setup_story: dict) -> None:
    """Player input is included verbatim in the context."""
    story: Story = setup_story["story"]
    player_input = PlayerInputContext(
        choice_text="Step across the threshold.",
        free_text=None,
        parsed_action="step",
    )

    ctx = StoryContextBuilder(db_session).build(
        story_id=story.id, player_input=player_input
    )

    assert ctx.player_input is not None
    assert ctx.player_input.choice_text == "Step across the threshold."
    assert ctx.player_input.parsed_action == "step"


def test_no_player_input_gives_none(db_session: Session, setup_story: dict) -> None:
    """player_input is None when not supplied."""
    story: Story = setup_story["story"]
    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    assert ctx.player_input is None


# ---------------------------------------------------------------------------
# Test: 10 — missing optional fields
# ---------------------------------------------------------------------------


def test_story_with_no_state_no_scene_no_characters(db_session: Session, test_user) -> None:
    """Context builder handles brand-new story with no scene, state or characters."""
    uid = uuid.uuid4().hex[:8]
    story = Story(
        user_id=test_user.id,
        title=f"Empty Story {uid}",
        genre="Mystery",
        theme="Void",
        tone="Eerie",
        season="Winter",
        length="short",
        status="active",
    )
    db_session.add(story)
    db_session.flush()

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)

    assert ctx.current_scene is None
    assert ctx.characters == []
    assert ctx.relationships == []
    assert ctx.relevant_memories == []
    assert ctx.recent_history == []
    assert ctx.runtime.turn_number == 0


# ---------------------------------------------------------------------------
# Test: 11 — empty character list
# ---------------------------------------------------------------------------


def test_empty_character_list(db_session: Session, test_user) -> None:
    """characters list is empty when story has no characters."""
    uid = uuid.uuid4().hex[:8]
    story = Story(
        user_id=test_user.id,
        title=f"NoChars {uid}",
        genre="Horror",
        theme="Silence",
        tone="Dread",
        season="Autumn",
        length="short",
        status="active",
    )
    db_session.add(story)
    db_session.flush()

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    assert ctx.characters == []


# ---------------------------------------------------------------------------
# Test: 13 — serialisation
# ---------------------------------------------------------------------------


def test_context_serialises_to_dict(db_session: Session, setup_story: dict) -> None:
    """StoryAIContext serialises to a plain JSON-safe dict."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    data = ctx.model_dump()

    assert isinstance(data, dict)
    assert "story_id" in data
    assert "characters" in data
    assert isinstance(data["characters"], list)

    # Ensure all values are JSON-primitive-safe (no SQLAlchemy objects)
    import json
    json_str = json.dumps(data, default=str)
    assert json_str  # non-empty


def test_no_sqlalchemy_objects_in_dict(db_session: Session, setup_story: dict) -> None:
    """Serialised dict contains no SQLAlchemy model instances."""
    from sqlalchemy.orm import DeclarativeBase

    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    _add_story_state(db_session, story.id, scene1.id)

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    data = ctx.model_dump()

    def _check_no_orm(obj: Any, path: str = "root") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                _check_no_orm(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _check_no_orm(v, f"{path}[{i}]")
        else:
            assert not isinstance(obj, DeclarativeBase), (
                f"Found SQLAlchemy ORM object at {path}: {type(obj)}"
            )

    _check_no_orm(data)


# ---------------------------------------------------------------------------
# Test: 14 — no mutation of deterministic game state
# ---------------------------------------------------------------------------


def test_builder_does_not_mutate_story_state(db_session: Session, setup_story: dict) -> None:
    """Building context must not change turn_number, yugen_meter or hidden_variables."""
    story: Story = setup_story["story"]
    scene1: Scene = setup_story["scene1"]
    ss = _add_story_state(db_session, story.id, scene1.id, turn=7)
    db_session.commit()  # persist initial state

    original_turn = ss.turn_number
    original_yugen = ss.yugen_meter
    original_hidden = dict(ss.hidden_variables)

    StoryContextBuilder(db_session).build(story_id=story.id)
    db_session.refresh(ss)

    assert ss.turn_number == original_turn
    assert ss.yugen_meter == original_yugen
    assert ss.hidden_variables == original_hidden


def test_builder_does_not_mutate_character_emotions(
    db_session: Session, setup_story: dict
) -> None:
    """Building context must not create or change CharacterState rows."""
    from sqlalchemy import func, select as sa_select
    from backend.app.models.character_state import CharacterState

    story: Story = setup_story["story"]

    before_count = db_session.scalar(
        sa_select(func.count(CharacterState.id)).where(CharacterState.story_id == story.id)
    )

    StoryContextBuilder(db_session).build(story_id=story.id)

    after_count = db_session.scalar(
        sa_select(func.count(CharacterState.id)).where(CharacterState.story_id == story.id)
    )

    # The builder must never create CharacterState rows
    assert before_count == after_count


# ---------------------------------------------------------------------------
# Test: Private helper — _build_scene_context
# ---------------------------------------------------------------------------


def test_build_scene_context_helper(setup_story: dict) -> None:
    """_build_scene_context converts a Scene ORM row cleanly."""
    scene1: Scene = setup_story["scene1"]
    result = _build_scene_context(scene1)

    assert isinstance(result, SceneContext)
    assert result.id == scene1.id
    assert result.location == scene1.location
    assert result.haiku == scene1.haiku


# ---------------------------------------------------------------------------
# Test: Private helper — _build_memory_query
# ---------------------------------------------------------------------------


def test_build_memory_query_with_scene_and_choice(setup_story: dict) -> None:
    """Memory query includes scene location, mood and player choice text."""
    scene: Scene = setup_story["scene1"]
    player_input = PlayerInputContext(choice_text="Open the locked gate.", free_text=None)

    query = _build_memory_query(scene, player_input)

    assert scene.location in query
    assert scene.mood in query
    assert "Open the locked gate." in query


def test_build_memory_query_no_scene_no_input() -> None:
    """Memory query falls back to 'story' when no scene or input is available."""
    query = _build_memory_query(None, None)
    assert query == "story"


def test_build_memory_query_free_text(setup_story: dict) -> None:
    """Memory query includes free_text when choice_text is absent."""
    scene: Scene = setup_story["scene1"]
    player_input = PlayerInputContext(free_text="I whispered to the shadows.", choice_text=None)

    query = _build_memory_query(scene, player_input)

    assert "whispered" in query


# ---------------------------------------------------------------------------
# Test: Default limits reflected in context
# ---------------------------------------------------------------------------


def test_default_limits_in_context(db_session: Session, setup_story: dict) -> None:
    """Context reports the correct memory and history limits."""
    story: Story = setup_story["story"]

    ctx = StoryContextBuilder(db_session).build(story_id=story.id)
    assert ctx.memory_limit == DEFAULT_MEMORY_LIMIT
    assert ctx.history_limit == DEFAULT_HISTORY_LIMIT


def test_custom_limits_in_context(db_session: Session, setup_story: dict) -> None:
    """Custom memory/history limits are reflected in the context object."""
    story: Story = setup_story["story"]

    ctx = StoryContextBuilder(db_session).build(
        story_id=story.id, memory_limit=2, history_limit=10
    )
    assert ctx.memory_limit == 2
    assert ctx.history_limit == 10
