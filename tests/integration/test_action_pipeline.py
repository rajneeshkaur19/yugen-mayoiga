import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.event import Event
from backend.app.models.memory import Memory
from backend.app.models.story_state import StoryState
from backend.app.models.user_choices_log import UserChoicesLog
from backend.app.services.action_pipeline import process_story_action
from backend.app.services.world_state_engine import get_world_var


def test_atomic_action_pipeline_success(db_session: Session, setup_story: dict):
    story = setup_story["story"]
    user_id = story.user_id
    story_id = story.id
    choice = setup_story["choice"]
    char = setup_story["character"]

    result = process_story_action(
        db=db_session,
        user_id=user_id,
        story_id=story_id,
        choice_id=choice.id,
        active_character_id=char.id,
    )

    # Validate returned structure
    assert result["story_id"] == story_id
    assert result["turn_number"] == 1
    assert result["current_scene_id"] == setup_story["scene2"].id
    assert result["scene_location"] == "Irori Hearth"
    assert result["yugen_meter"] == 40  # 50 - 10
    assert result["applied_effects"]["world_door"] == "unlocked"

    # Verify world state persisted
    assert get_world_var(db_session, story_id, "door") == "unlocked"

    # Verify memory was created
    mems = list(
        db_session.scalars(
            select(Memory).where(
                Memory.story_id == story_id,
                Memory.type == "player_choice",
            )
        ).all()
    )
    assert len(mems) >= 1
    assert "Step across the threshold" in mems[0].event

    # Verify user choices log entry created
    logs = list(
        db_session.scalars(
            select(UserChoicesLog).where(
                UserChoicesLog.story_id == story_id,
                UserChoicesLog.turn_number == 1,
            )
        ).all()
    )
    assert len(logs) == 1
    assert logs[0].choice_id == choice.id

    # Verify ending triggered
    assert len(result["achieved_endings"]) >= 1
    assert result["achieved_endings"][0]["seal_text"] == "TRUTH_SEAL"


def test_action_pipeline_wrong_user_blocked(db_session: Session, setup_story: dict, other_user):
    story_id = setup_story["story"].id
    choice_id = setup_story["choice"].id

    with pytest.raises(ValueError, match="does not belong to user"):
        process_story_action(
            db=db_session,
            user_id=other_user.id,
            story_id=story_id,
            choice_id=choice_id,
        )


def test_action_pipeline_invalid_choice_rejected(db_session: Session, setup_story: dict):
    story = setup_story["story"]
    with pytest.raises(ValueError, match="not an available option"):
        process_story_action(
            db=db_session,
            user_id=story.user_id,
            story_id=story.id,
            choice_id=999999,
        )


def test_action_pipeline_rollback_on_failure(db_session: Session, setup_story: dict):
    story = setup_story["story"]
    user_id = story.user_id
    story_id = story.id

    # Turn before failed action
    state_before = db_session.scalar(select(StoryState).where(StoryState.story_id == story_id))
    turn_before = state_before.turn_number if state_before else 0

    try:
        # Pass completely invalid parameters
        process_story_action(
            db=db_session,
            user_id=user_id,
            story_id=story_id,
            choice_id=999999,
        )
    except ValueError:
        pass

    state_after = db_session.scalar(select(StoryState).where(StoryState.story_id == story_id))
    turn_after = state_after.turn_number if state_after else 0
    assert turn_before == turn_after



def test_scheduled_event_applies_condition_and_effects(
    db_session: Session, setup_story: dict
):
    story = setup_story["story"]
    choice = setup_story["choice"]
    char = setup_story["character"]

    event = Event(
        story_id=story.id,
        description="The hidden door opens.",
        priority=5,
        due_turn=1,
        status="pending",
        trigger_condition={"truth_discovered": True},
        effects={
            "world": {"event_door": "opened"},
            "yugen_meter": 5,
        },
    )
    db_session.add(event)
    db_session.flush()

    result = process_story_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        choice_id=choice.id,
        active_character_id=char.id,
    )

    db_session.refresh(event)
    assert event.status == "done"
    assert "The hidden door opens." in result["triggered_events"]
    assert get_world_var(db_session, story.id, "event_door") == "opened"
    assert result["yugen_meter"] == 45


def test_scheduled_event_waits_when_condition_is_false(
    db_session: Session, setup_story: dict
):
    story = setup_story["story"]
    choice = setup_story["choice"]
    char = setup_story["character"]

    event = Event(
        story_id=story.id,
        description="A locked memory awakens.",
        priority=5,
        due_turn=1,
        status="pending",
        trigger_condition={"truth_discovered": False},
        effects={"world": {"should_not_apply": True}},
    )
    db_session.add(event)
    db_session.flush()

    result = process_story_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        choice_id=choice.id,
        active_character_id=char.id,
    )

    db_session.refresh(event)
    assert event.status == "ready"
    assert "A locked memory awakens." not in result["triggered_events"]
    assert get_world_var(db_session, story.id, "should_not_apply") is None


def test_scheduled_events_execute_in_priority_order(
    db_session: Session, setup_story: dict
):
    story = setup_story["story"]
    choice = setup_story["choice"]
    char = setup_story["character"]

    low_priority = Event(
        story_id=story.id,
        description="Low-priority event",
        priority=1,
        due_turn=1,
        status="pending",
        trigger_condition={},
        effects={},
    )
    high_priority = Event(
        story_id=story.id,
        description="High-priority event",
        priority=10,
        due_turn=1,
        status="pending",
        trigger_condition={},
        effects={},
    )
    db_session.add_all([low_priority, high_priority])
    db_session.flush()

    result = process_story_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        choice_id=choice.id,
        active_character_id=char.id,
    )

    assert result["triggered_events"][:2] == [
        "High-priority event",
        "Low-priority event",
    ]
