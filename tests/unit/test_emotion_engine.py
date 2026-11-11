import pytest
from backend.app.services.emotion_engine import (
    calculate_decayed_emotions,
)


def test_positive_and_negative_emotion_deltas():
    from algorithms.state_store import StateStore
    store = StateStore()
    store.init_character_emotions(1, {"fear": 30, "trust": 50})

    # Positive delta
    store.apply_emotion_delta(1, "fear", 25)
    assert store.get_emotions(1)["fear"] == 55

    # Negative delta
    store.apply_emotion_delta(1, "trust", -15)
    assert store.get_emotions(1)["trust"] == 35


def test_clamping_at_boundaries():
    from algorithms.state_store import StateStore
    store = StateStore()
    store.init_character_emotions(1, {"anger": 80, "happiness": 20})

    # Exceed 100
    store.apply_emotion_delta(1, "anger", 50)
    assert store.get_emotions(1)["anger"] == 100

    # Fall below 0
    store.apply_emotion_delta(1, "happiness", -60)
    assert store.get_emotions(1)["happiness"] == 0


def test_emotion_decay_towards_baselines():
    # Baselines: fear=0, anxiety=0, anger=0, sadness=0, happiness=50, trust=50
    curr = {
        "fear": 20,
        "anxiety": 15,
        "anger": 10,
        "sadness": 8,
        "happiness": 70,
        "trust": 30,
    }

    decayed = calculate_decayed_emotions(curr, decay_rate=5)
    assert decayed["fear"] == 15      # 20 -> 15 (toward 0)
    assert decayed["anxiety"] == 10   # 15 -> 10 (toward 0)
    assert decayed["anger"] == 5      # 10 -> 5 (toward 0)
    assert decayed["sadness"] == 3    # 8 -> 3 (toward 0)
    assert decayed["happiness"] == 65 # 70 -> 65 (toward 50)
    assert decayed["trust"] == 35     # 30 -> 35 (toward 50)


def test_memory_reinforcement_calculations():
    from algorithms.state_store import StateStore
    store = StateStore()
    store.init_character_emotions(1, {"fear": 40, "happiness": 50})

    # Traumatic memory: high importance (80), negative weight (-50)
    store.reinforce_emotion(1, "fear", importance=80, emotional_weight=50, damping=0.2)
    # delta = round((80/100) * 50 * 0.2) = round(8.0) = 8
    assert store.get_emotions(1)["fear"] == 48
