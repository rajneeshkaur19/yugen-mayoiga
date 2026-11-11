import pytest
from algorithms.state_store import StateStore


def test_relationship_attributes_and_deltas():
    store = StateStore()
    # 1 -> 2
    store.init_relationship(1, 2, {
        "trust": 50,
        "friendship": 50,
        "suspicion": 10,
        "fear": 0,
        "dependency": 20,
    })

    store.apply_relationship_delta(1, 2, "trust", -20)
    store.apply_relationship_delta(1, 2, "suspicion", 35)

    rel = store.get_relationship(1, 2)
    assert rel["trust"] == 30
    assert rel["suspicion"] == 45


def test_relationship_directionality_independence():
    store = StateStore()
    # Aki lies to Ren
    # Aki (1) -> Ren (2) vs Ren (2) -> Aki (1)
    store.init_relationship(1, 2, {"trust": 60, "suspicion": 10})
    store.init_relationship(2, 1, {"trust": 72, "suspicion": 15})

    # Ren finds out: Ren's feelings toward Aki change
    store.apply_relationship_delta(2, 1, "trust", -30)
    store.apply_relationship_delta(2, 1, "suspicion", 40)

    ren_to_aki = store.get_relationship(2, 1)
    aki_to_ren = store.get_relationship(1, 2)

    assert ren_to_aki["trust"] == 42
    assert ren_to_aki["suspicion"] == 55
    # Aki's feelings toward Ren should remain unaltered
    assert aki_to_ren["trust"] == 60
    assert aki_to_ren["suspicion"] == 10


def test_relationship_clamping():
    store = StateStore()
    store.init_relationship(1, 2, {"trust": 90, "fear": 10})

    store.apply_relationship_delta(1, 2, "trust", 50)
    assert store.get_relationship(1, 2)["trust"] == 100

    store.apply_relationship_delta(1, 2, "fear", -50)
    assert store.get_relationship(1, 2)["fear"] == 0
