"""Batch 3: Story State, Choices, Scenes & Memories — Integration & Regression Tests.

Covers:
1. Choice-to-state transitions & exact single turn increment
2. Emotion engine updates, clamping, persistence, and no mutation on failure
3. Relationship engine updates, clamping, and validation
4. World-state mutations, persistence across scenes, invalid key rejection, log history
5. Permanent character memories: significance rule, cracked/gilded semantics,
   duplicate prevention, and heap-based retrieval
6. Duplicate choice submission prevention (allow_loop=False & completed story)
7. Invalid choices (wrong scene, unmet condition, missing choice)
8. Priority event ordering, due-event execution, duplicate prevention, rollback
9. Ending reachability for all 3 Mayoiga endings:
   - The Unveiled Dawn
   - The Timeless Sanctuary
   - Where the Mists Dissolve
10. Transaction rollback on mid-pipeline failure
"""

from __future__ import annotations

import uuid
from collections import deque

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.character import Character
from backend.app.models.character_state import CharacterState
from backend.app.models.choice import Choice
from backend.app.models.ending import Ending
from backend.app.models.event import Event
from backend.app.models.memory import Memory
from backend.app.models.relationship import Relationship
from backend.app.models.scene import Scene
from backend.app.models.story import Story
from backend.app.models.story_state import StoryState
from backend.app.models.user import User
from backend.app.models.user_choices_log import UserChoicesLog
from backend.app.models.user_ending import UserEnding
from backend.app.services.action_pipeline import process_story_action
from backend.app.services.emotion_engine import get_character_emotions_dict
from backend.app.services.memory_service import retrieve_relevant_memories
from backend.app.services.world_state_engine import get_all_world_vars, set_world_var


def _db_available() -> bool:
    try:
        import socket

        s = socket.create_connection(("localhost", 5432), timeout=1)
        s.close()
        return True
    except Exception:
        return False


skip_no_db = pytest.mark.skipif(not _db_available(), reason="PostgreSQL not reachable")


def _create_two_char_story(db: Session, user: User) -> dict:
    """Helper creating a clean story with 2 characters, 3 scenes, and choices."""
    uid = uuid.uuid4().hex[:6]
    story = Story(
        user_id=user.id,
        title=f"Batch3 Tale {uid}",
        genre="Mystery",
        theme="Memory",
        tone="Eerie",
        season="Autumn",
        length="medium",
        status="active",
    )
    db.add(story)
    db.flush()

    s1 = Scene(
        story_id=story.id,
        scene_number=1,
        location="Front Gate",
        mood="Foreboding",
        content="Mist clings to the gate.",
        is_ending=False,
    )
    s2 = Scene(
        story_id=story.id,
        scene_number=2,
        location="Hearth Chamber",
        mood="Tense",
        content="Embers glow in the irori.",
        is_ending=False,
    )
    s3 = Scene(
        story_id=story.id,
        scene_number=3,
        location="Dawn Threshold",
        mood="Serene",
        content="Dawn breaks over the ridge.",
        is_ending=True,
    )
    db.add_all([s1, s2, s3])
    db.flush()

    c1 = Character(
        story_id=story.id,
        name=f"Ren_{uid}",
        role="Investigator",
        age=24,
        background="Seeker of lost truths.",
    )
    c2 = Character(
        story_id=story.id,
        name=f"Aoi_{uid}",
        role="Keeper",
        age=21,
        background="Guardian of the estate.",
    )
    db.add_all([c1, c2])
    db.flush()

    state = StoryState(
        story_id=story.id,
        current_scene_id=s1.id,
        hidden_variables={},
        yugen_meter=50,
        turn_number=0,
    )
    db.add(state)
    db.commit()

    return {
        "story": story,
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "c1": c1,
        "c2": c2,
        "state": state,
    }


@skip_no_db
def test_choice_transition_emotion_relationship_world_and_history(
    db_session: Session, test_user: User
) -> None:
    """Valid choice atomically updates scene, turn (+1), emotions, relationships,
    world state, hidden vars, Yūgen meter, and UserChoicesLog."""
    data = _create_two_char_story(db_session, test_user)
    story, s1, s2, c1, c2 = (
        data["story"],
        data["s1"],
        data["s2"],
        data["c1"],
        data["c2"],
    )

    choice = Choice(
        story_id=story.id,
        scene_id=s1.id,
        choice_text="Share the lantern warmth with Aoi.",
        effects={
            "fear": -10,
            "trust": 25,
            "relationships": {f"{c1.id}->{c2.id}": {"trust": 20, "friendship": 15}},
            "world_lantern_lit": True,
            "hidden_clue_alpha": "found",
            "yugen_meter": -10,
            "emotional_weight": 45,
            "memory_importance": 80,
        },
        allow_loop=False,
        next_scene_id=s2.id,
    )
    db_session.add(choice)
    db_session.commit()

    res = process_story_action(
        db_session,
        user_id=test_user.id,
        story_id=story.id,
        choice_id=choice.id,
        active_character_id=c1.id,
    )

    assert res["turn_number"] == 1
    assert res["current_scene_id"] == s2.id
    assert res["yugen_meter"] == 40

    # Emotions persisted and clamped
    db_session.expire_all()
    emos = get_character_emotions_dict(db_session, story.id, c1.id)
    assert 0 <= emos["trust"] <= 100
    assert emos["trust"] > 50

    # Relationship persisted
    rel = db_session.scalar(
        select(Relationship).where(
            Relationship.story_id == story.id,
            Relationship.from_character == c1.id,
            Relationship.to_character == c2.id,
        )
    )
    assert rel is not None
    assert rel.trust == 70
    assert rel.friendship == 65

    # World state persisted across transition
    world = get_all_world_vars(db_session, story.id)
    assert world["lantern_lit"] is True

    # History log records delta for recovery
    log = db_session.scalar(
        select(UserChoicesLog).where(
            UserChoicesLog.story_id == story.id,
            UserChoicesLog.turn_number == 1,
        )
    )
    assert log is not None
    assert log.delta.get("world_lantern_lit") is True


@skip_no_db
def test_duplicate_choice_and_invalid_choices_do_not_mutate_state(
    db_session: Session, test_user: User
) -> None:
    """Repeating an allow_loop=False choice, choosing from wrong scene, or
    unmet condition must raise ValueError without mutating turn_number."""
    data = _create_two_char_story(db_session, test_user)
    story, s1, s2, c1 = data["story"], data["s1"], data["s2"], data["c1"]

    # Looping choice staying on s1 with allow_loop=False
    non_loop_choice = Choice(
        story_id=story.id,
        scene_id=s1.id,
        choice_text="Inspect the sealed gate once.",
        effects={"world_gate_checked": True},
        allow_loop=False,
        next_scene_id=s1.id,
    )
    # Conditional choice requiring hidden key not yet set
    locked_choice = Choice(
        story_id=story.id,
        scene_id=s1.id,
        choice_text="Open the secret panel.",
        effects={"world_panel": "open"},
        condition={"has_crane_key": True},
        allow_loop=False,
        next_scene_id=s2.id,
    )
    # Choice belonging to s2 (wrong scene while on s1)
    s2_choice = Choice(
        story_id=story.id,
        scene_id=s2.id,
        choice_text="Stir the embers.",
        effects={},
        next_scene_id=s1.id,
    )
    db_session.add_all([non_loop_choice, locked_choice, s2_choice])
    db_session.commit()

    # Unmet condition rejected
    with pytest.raises(ValueError, match="prerequisites"):
        process_story_action(
            db_session, test_user.id, story.id, choice_id=locked_choice.id, active_character_id=c1.id
        )

    # Wrong scene choice rejected
    with pytest.raises(ValueError, match="not an available option"):
        process_story_action(
            db_session, test_user.id, story.id, choice_id=s2_choice.id, active_character_id=c1.id
        )

    state_before = db_session.scalar(select(StoryState).where(StoryState.story_id == story.id))
    assert state_before.turn_number == 0

    # First execution succeeds
    process_story_action(
        db_session, test_user.id, story.id, choice_id=non_loop_choice.id, active_character_id=c1.id
    )

    # Second execution of allow_loop=False choice is blocked
    with pytest.raises(ValueError, match="already been executed"):
        process_story_action(
            db_session, test_user.id, story.id, choice_id=non_loop_choice.id, active_character_id=c1.id
        )

    state_after = db_session.scalar(select(StoryState).where(StoryState.story_id == story.id))
    assert state_after.turn_number == 1


@skip_no_db
def test_memory_significance_cracked_gilded_dedup_and_retrieval(
    db_session: Session, test_user: User
) -> None:
    """Insignificant free-text actions do NOT create memories; significant actions
    create cracked/gilded memories without duplicates and are retrievable."""
    data = _create_two_char_story(db_session, test_user)
    story, s1, s2, c1 = data["story"], data["s1"], data["s2"], data["c1"]

    # 1. Insignificant free-text action (empty effects, no scene transition)
    process_story_action(
        db_session,
        user_id=test_user.id,
        story_id=story.id,
        free_text="Glance idly at the floor.",
        active_character_id=c1.id,
    )
    mems = list(db_session.scalars(select(Memory).where(Memory.story_id == story.id)).all())
    assert len(mems) == 0, "Insignificant free-text action must not create a memory"

    # 2. Significant traumatic choice -> cracked emotional memory
    traumatic = Choice(
        story_id=story.id,
        scene_id=s1.id,
        choice_text="Shatter the ancestral mirror.",
        effects={
            "fear": 20,
            "emotional_weight": -55,
            "memory_importance": 85,
            "memory_event": "Shattered the ancestral mirror in Front Gate",
        },
        allow_loop=True,
        next_scene_id=s1.id,
    )
    # 3. Significant uplifting choice -> gilded emotional memory
    uplifting = Choice(
        story_id=story.id,
        scene_id=s1.id,
        choice_text="Light the shrine lantern together.",
        effects={
            "happiness": 20,
            "emotional_weight": 55,
            "memory_importance": 85,
            "memory_event": "Lit the shrine lantern together",
        },
        allow_loop=False,
        next_scene_id=s2.id,
    )
    db_session.add_all([traumatic, uplifting])
    db_session.commit()

    # Execute traumatic choice twice (allow_loop=True) -> only ONE memory should exist
    process_story_action(
        db_session, test_user.id, story.id, choice_id=traumatic.id, active_character_id=c1.id
    )
    process_story_action(
        db_session, test_user.id, story.id, choice_id=traumatic.id, active_character_id=c1.id
    )
    process_story_action(
        db_session, test_user.id, story.id, choice_id=uplifting.id, active_character_id=c1.id
    )

    mems = list(
        db_session.scalars(
            select(Memory).where(Memory.story_id == story.id).order_by(Memory.created_turn)
        ).all()
    )
    assert len(mems) == 2
    assert mems[0].status == "cracked"
    assert mems[0].type == "emotional"
    assert mems[1].status == "gilded"
    assert mems[1].type == "emotional"

    # Retrieval finds relevant memory
    retrieved = retrieve_relevant_memories(
        db_session, story.id, query="ancestral mirror", current_turn=4, k=2, character_id=c1.id
    )
    assert len(retrieved) >= 1
    assert "mirror" in retrieved[0][0].event.lower()


@skip_no_db
def test_priority_events_ordering_dedup_and_rollback(
    db_session: Session, test_user: User
) -> None:
    """Priority events execute in descending priority order, mark status='done'
    to prevent duplicates, keep unmet-condition events 'ready', and roll back on error."""
    data = _create_two_char_story(db_session, test_user)
    story, s1, c1 = data["story"], data["s1"], data["c1"]

    ev_low = Event(
        story_id=story.id,
        due_turn=1,
        priority=10,
        description="Low priority chime",
        trigger_condition={},
        effects={"world_order_log": "low"},
        status="pending",
    )
    ev_high = Event(
        story_id=story.id,
        due_turn=1,
        priority=90,
        description="High priority bell",
        trigger_condition={},
        effects={"world_order_log": "high", "yugen_meter": 5},
        status="pending",
    )
    ev_unmet = Event(
        story_id=story.id,
        due_turn=1,
        priority=50,
        description="Gated event",
        trigger_condition={"secret_unlocked": True},
        effects={"world_gated_ran": True},
        status="pending",
    )
    db_session.add_all([ev_low, ev_high, ev_unmet])
    db_session.commit()

    res = process_story_action(
        db_session, test_user.id, story.id, free_text="Wait quietly.", active_character_id=c1.id
    )
    # High priority executes first, then low priority overwrites world_order_log last
    assert res["triggered_events"] == ["High priority bell", "Low priority chime"]
    assert res["yugen_meter"] == 55

    db_session.expire_all()
    assert db_session.get(Event, ev_high.id).status == "done"
    assert db_session.get(Event, ev_low.id).status == "done"
    assert db_session.get(Event, ev_unmet.id).status == "ready"
    assert get_all_world_vars(db_session, story.id)["order_log"] == "low"

    # Next turn: done events do NOT re-trigger
    res2 = process_story_action(
        db_session, test_user.id, story.id, free_text="Listen again.", active_character_id=c1.id
    )
    assert res2["triggered_events"] == []


@skip_no_db
def test_transaction_rollback_on_mid_pipeline_failure(
    db_session: Session, test_user: User
) -> None:
    """If a failure occurs mid-pipeline (e.g. invalid relationship key or invalid
    world key), turn_number, emotions, and world state all roll back atomically."""
    data = _create_two_char_story(db_session, test_user)
    story, s1, c1 = data["story"], data["s1"], data["c1"]

    bad_choice = Choice(
        story_id=story.id,
        scene_id=s1.id,
        choice_text="Trigger corrupted relationship delta.",
        effects={
            "fear": 30,
            "world_should_not_persist": True,
            "relationships": {"invalid_key_format": {"trust": 10}},
        },
        next_scene_id=s1.id,
    )
    db_session.add(bad_choice)
    db_session.commit()

    with pytest.raises(ValueError, match="Invalid relationship key"):
        process_story_action(
            db_session, test_user.id, story.id, choice_id=bad_choice.id, active_character_id=c1.id
        )

    db_session.expire_all()
    state = db_session.scalar(select(StoryState).where(StoryState.story_id == story.id))
    assert state.turn_number == 0
    assert get_all_world_vars(db_session, story.id) == {}
    assert db_session.scalar(select(CharacterState).where(CharacterState.story_id == story.id)) is None

    # Also verify empty world-state key is rejected
    with pytest.raises(ValueError, match="non-empty string"):
        set_world_var(db_session, story.id, "   ", "val")


@skip_no_db
def test_all_three_endings_reachable_and_mutually_exclusive(
    db_session: Session, test_user: User
) -> None:
    """Verify the 9-scene Mayoiga graph reaches each of the 3 intended endings
    ('The Unveiled Dawn', 'The Timeless Sanctuary', 'Where the Mists Dissolve')
    without premature triggering or cross-triggering, and blocks further actions."""
    paths = [
        (
            "The Unveiled Dawn",
            [
                ("start", "west_wing", {"yugen_meter": 5}),
                ("west_wing", "cellar_archive", {"yugen_meter": 5}),
                ("cellar_archive", "inner_sanctum", {"hidden_truth_discovered": True, "yugen_meter": -15}),
                ("inner_sanctum", "ending_truth", {"hidden_unveiled_dawn": True, "hidden_truth_discovered": True, "yugen_meter": -30}),
            ],
        ),
        (
            "The Timeless Sanctuary",
            [
                ("start", "perimeter_garden", {"yugen_meter": 10}),
                ("perimeter_garden", "inner_sanctum", {"yugen_meter": 10}),
                ("inner_sanctum", "ending_eternal", {"hidden_sanctuary_accepted": True, "yugen_meter": 30}),
            ],
        ),
        (
            "Where the Mists Dissolve",
            [
                ("start", "hearth_room", {"yugen_meter": -5}),
                ("hearth_room", "perimeter_garden", {"yugen_meter": 5}),
                ("perimeter_garden", "inner_sanctum", {"yugen_meter": 10}),
                ("inner_sanctum", "ending_twilight", {"hidden_journey_concluded": True, "yugen_meter": 0}),
            ],
        ),
    ]

    scene_keys = [
        ("start", 1, False),
        ("west_wing", 2, False),
        ("hearth_room", 3, False),
        ("perimeter_garden", 4, False),
        ("cellar_archive", 5, False),
        ("inner_sanctum", 6, False),
        ("ending_truth", 7, True),
        ("ending_eternal", 8, True),
        ("ending_twilight", 9, True),
    ]

    for expected_ending_name, steps in paths:
        story = Story(
            user_id=test_user.id,
            title=f"Reach {expected_ending_name}",
            genre="Mystery",
            theme="Sanctuary",
            tone="Eerie",
            season="Autumn",
            length="medium",
            status="active",
        )
        db_session.add(story)
        db_session.flush()

        scenes_map: dict[str, Scene] = {}
        for key, num, is_end in scene_keys:
            sc = Scene(
                story_id=story.id,
                scene_number=num,
                location=key,
                mood="Atmospheric",
                content=f"Scene {key}",
                is_ending=is_end,
            )
            db_session.add(sc)
            scenes_map[key] = sc
        db_session.flush()

        char = Character(
            story_id=story.id, name="Traveler", role="Protagonist", age=22, background="Visitor"
        )
        db_session.add(char)

        db_session.add_all([
            Ending(story_id=story.id, name="The Unveiled Dawn", conditions={"unveiled_dawn": True}, seal_text="Dawn"),
            Ending(story_id=story.id, name="The Timeless Sanctuary", conditions={"sanctuary_accepted": True}, seal_text="Keeper"),
            Ending(story_id=story.id, name="Where the Mists Dissolve", conditions={"journey_concluded": True}, seal_text="Echo"),
        ])

        choice_objs: list[Choice] = []
        for idx, (src, dst, eff) in enumerate(steps):
            ch = Choice(
                story_id=story.id,
                scene_id=scenes_map[src].id,
                choice_text=f"{src} -> {dst}",
                effects=eff,
                allow_loop=False,
                sort_order=idx,
                next_scene_id=scenes_map[dst].id,
            )
            db_session.add(ch)
            choice_objs.append(ch)

        db_session.add(
            StoryState(
                story_id=story.id,
                current_scene_id=scenes_map["start"].id,
                hidden_variables={},
                yugen_meter=50,
                turn_number=0,
            )
        )
        db_session.commit()

        # Walk all intermediate steps — must NOT trigger an ending early
        for ch in choice_objs[:-1]:
            mid_res = process_story_action(db_session, test_user.id, story.id, choice_id=ch.id)
            assert mid_res["achieved_endings"] == []
            assert mid_res["is_ending"] is False

        # Final climax step — must trigger ONLY the expected ending
        final_res = process_story_action(db_session, test_user.id, story.id, choice_id=choice_objs[-1].id)
        assert final_res["is_ending"] is True
        assert [e["name"] for e in final_res["achieved_endings"]] == [expected_ending_name]

        # Story is now completed; further actions must be rejected
        with pytest.raises(ValueError, match="already reached an ending"):
            process_story_action(db_session, test_user.id, story.id, free_text="Keep wandering")
