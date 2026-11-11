import pytest
from algorithms.state_store import StateStore, clamp


def test_clamp_boundaries():
    assert clamp(-10, 0, 100) == 0
    assert clamp(150, 0, 100) == 100
    assert clamp(42, 0, 100) == 42
    assert clamp(50.6) == 51


def test_emotion_deltas_and_clamping():
    store = StateStore()
    char_id = 1
    store.init_character_emotions(char_id, {"fear": 10, "trust": 50})

    # Positive delta
    store.apply_emotion_delta(char_id, "fear", 25)
    assert store.get_emotions(char_id)["fear"] == 35

    # Clamping at 100
    store.apply_emotion_delta(char_id, "fear", 100)
    assert store.get_emotions(char_id)["fear"] == 100

    # Negative delta and clamping at 0
    store.apply_emotion_delta(char_id, "fear", -150)
    assert store.get_emotions(char_id)["fear"] == 0


def test_emotion_decay():
    store = StateStore()
    char_id = 1
    # Fear baseline is 0; current is 40
    store.init_character_emotions(char_id, {"fear": 40, "trust": 80})

    # Decay by 5 points
    store.decay_emotions(char_id, decay_rate=5)
    emotions = store.get_emotions(char_id)
    assert emotions["fear"] == 35  # Moved 5 points toward baseline 0
    assert emotions["trust"] == 75  # Moved 5 points toward baseline 50

    # Multiple decays reach baseline without overshooting
    for _ in range(10):
        store.decay_emotions(char_id, decay_rate=10)
    emotions = store.get_emotions(char_id)
    assert emotions["fear"] == 0
    assert emotions["trust"] == 50


def test_emotion_reinforcement_from_memory():
    store = StateStore()
    char_id = 1
    store.init_character_emotions(char_id, {"fear": 20})

    # High importance (90), positive emotional weight (+40)
    # delta = round((90/100) * 40 * 0.2) = round(7.2) = 7
    store.reinforce_emotion(char_id, "fear", importance=90, emotional_weight=40, damping=0.2)
    assert store.get_emotions(char_id)["fear"] == 27


def test_relationship_directionality_and_bounds():
    store = StateStore()
    # Aki (1) -> Ren (2)
    store.init_relationship(1, 2, {"trust": 72, "suspicion": 15})
    # Ren (2) -> Aki (1)
    store.init_relationship(2, 1, {"trust": 40, "suspicion": 30})

    # Update Aki -> Ren
    store.apply_relationship_delta(1, 2, "trust", -30)
    store.apply_relationship_delta(1, 2, "suspicion", 40)

    rel_1_to_2 = store.get_relationship(1, 2)
    rel_2_to_1 = store.get_relationship(2, 1)

    assert rel_1_to_2["trust"] == 42
    assert rel_1_to_2["suspicion"] == 55
    # Directionality: Ren -> Aki must be untouched!
    assert rel_2_to_1["trust"] == 40
    assert rel_2_to_1["suspicion"] == 30


def test_relationship_no_self_loop():
    store = StateStore()
    with pytest.raises(ValueError, match="self-referential"):
        store.init_relationship(1, 1)


def test_world_state_key_value():
    store = StateStore()
    store.set_world_var("door", "locked")
    store.set_world_var("power", "on")
    store.set_world_var("time", "23:40")

    assert store.get_world_var("door") == "locked"
    assert store.get_world_var("power") == "on"

    store.update_world_state({"power": "off", "weather": "rain"})
    assert store.get_world_var("power") == "off"
    assert store.get_world_var("weather") == "rain"


def test_hidden_variables_and_yugen_meter():
    store = StateStore()
    store.set_hidden_var("truth_progress", 10)
    store.update_hidden_vars({"truth_progress_delta": 15, "secret_found": True})

    assert store.get_hidden_var("truth_progress") == 25
    assert store.get_hidden_var("secret_found") is True

    # Yūgen meter starts at 50
    store.update_yugen_meter(-15)
    assert store.yugen_meter == 35
    store.update_yugen_meter(100)
    assert store.yugen_meter == 100
    store.update_yugen_meter(-150)
    assert store.yugen_meter == 0


def test_apply_choice_effects_combined():
    store = StateStore()
    store.init_character_emotions(1, {"fear": 10})
    store.init_relationship(1, 2, {"trust": 50})

    effects = {
        "emotions": {1: {"fear": 25}},
        "relationships": {(1, 2): {"trust": -15}},
        "world": {"power": "off"},
        "hidden": {"mystery_clue": "found"},
        "yugen_meter": -10,
    }

    store.apply_choice_effects(effects, active_character_id=1)
    assert store.get_emotions(1)["fear"] == 35
    assert store.get_relationship(1, 2)["trust"] == 35
    assert store.get_world_var("power") == "off"
    assert store.get_hidden_var("mystery_clue") == "found"
    assert store.yugen_meter == 40
