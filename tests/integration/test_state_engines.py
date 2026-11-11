import pytest
from sqlalchemy.orm import Session

from backend.app.services.emotion_engine import (
    get_character_emotions_dict,
    record_character_emotions,
)
from backend.app.services.ending_engine import (
    check_and_trigger_endings,
    create_ending,
    get_user_endings,
    record_achieved_ending,
)
from backend.app.services.relationship_engine import (
    apply_relationship_deltas,
    create_or_update_relationship,
    get_relationship,
    list_story_relationships,
)
from backend.app.services.state_service import (
    get_or_create_story_state,
    get_unified_story_state,
    update_hidden_variables,
    update_yugen_meter,
)
from backend.app.services.world_state_engine import (
    get_all_world_vars,
    get_world_var,
    set_world_var,
    update_world_state,
)


def test_world_state_persistence_and_isolation(db_session: Session, setup_story: dict):
    story_id = setup_story["story"].id

    # Insert world variables
    set_world_var(db_session, story_id, "weather", "dense fog")
    set_world_var(db_session, story_id, "power", "off")
    db_session.commit()

    # Retrieve
    assert get_world_var(db_session, story_id, "weather") == "dense fog"
    assert get_world_var(db_session, story_id, "power") == "off"

    all_vars = get_all_world_vars(db_session, story_id)
    assert all_vars["weather"] == "dense fog"
    assert all_vars["power"] == "off"

    # Update
    update_world_state(db_session, story_id, {"power": "on", "door": "unlocked"})
    db_session.commit()
    assert get_world_var(db_session, story_id, "power") == "on"
    assert get_world_var(db_session, story_id, "door") == "unlocked"


def test_relationship_persistence_and_directionality(db_session: Session, setup_story: dict):
    story_id = setup_story["story"].id
    char1_id = setup_story["character"].id

    # Create second character for relationship testing
    from backend.app.models.character import Character
    char2 = Character(
        story_id=story_id,
        name="Ren_Partner",
        role="Scholar",
    )
    db_session.add(char2)
    db_session.commit()
    db_session.refresh(char2)

    # char1 -> char2
    create_or_update_relationship(
        db_session,
        story_id,
        from_character=char1_id,
        to_character=char2.id,
        values={"trust": 75, "suspicion": 10},
    )
    db_session.commit()

    rel = get_relationship(db_session, story_id, char1_id, char2.id)
    assert rel is not None
    assert rel.trust == 75
    assert rel.suspicion == 10

    # Apply deltas
    apply_relationship_deltas(
        db_session,
        story_id,
        from_character=char1_id,
        to_character=char2.id,
        deltas={"trust": -20, "suspicion": 25},
    )
    db_session.commit()

    rel_updated = get_relationship(db_session, story_id, char1_id, char2.id)
    assert rel_updated.trust == 55
    assert rel_updated.suspicion == 35


def test_emotion_state_turn_snapshots(db_session: Session, setup_story: dict):
    story_id = setup_story["story"].id
    char_id = setup_story["character"].id
    scene_id = setup_story["scene1"].id

    # Turn 1: acute fear increase
    record_character_emotions(
        db_session,
        story_id=story_id,
        character_id=char_id,
        scene_id=scene_id,
        turn_number=1,
        deltas={"fear": 35, "trust": 10},
        decay=False,
    )
    db_session.commit()

    emotions_t1 = get_character_emotions_dict(db_session, story_id, char_id)
    assert emotions_t1["fear"] == 35

    # Turn 2: decay pulls fear toward 0 by 5 points
    record_character_emotions(
        db_session,
        story_id=story_id,
        character_id=char_id,
        scene_id=scene_id,
        turn_number=2,
        deltas=None,
        decay=True,
        decay_rate=5,
    )
    db_session.commit()

    emotions_t2 = get_character_emotions_dict(db_session, story_id, char_id)
    assert emotions_t2["fear"] == 30


def test_ending_evaluation_and_recording(db_session: Session, setup_story: dict):
    story_id = setup_story["story"].id
    user_id = setup_story["story"].user_id

    # Create ending requiring trust > 70 and truth_discovered = True
    ending = create_ending(
        db_session,
        story_id=story_id,
        name="Truth of Mayoiga",
        conditions={"trust": {">": 70}, "truth_discovered": True},
        seal_text="MAYOIGA_SEAL",
    )

    # 1. Unsatisfied state: trust = 50, truth_discovered = False
    state_unsatisfied = {"trust": 50, "truth_discovered": False}
    achieved = check_and_trigger_endings(db_session, story_id, user_id, state_unsatisfied)
    assert len(achieved) == 0

    # 2. Satisfied state: trust = 80, truth_discovered = True
    state_satisfied = {"trust": 80, "truth_discovered": True}
    achieved = check_and_trigger_endings(db_session, story_id, user_id, state_satisfied)
    assert len(achieved) >= 1
    assert any(e.name == "Truth of Mayoiga" for e in achieved)

    # Verify user endings gallery
    user_ends = get_user_endings(db_session, user_id)
    assert any(ue.ending_id == ending.id for ue in user_ends)

    # Duplicate prevention: recording same ending twice does not error or duplicate
    record_achieved_ending(db_session, user_id, ending.id)
    user_ends_after = get_user_endings(db_session, user_id)
    matching = [ue for ue in user_ends_after if ue.ending_id == ending.id]
    assert len(matching) == 1
