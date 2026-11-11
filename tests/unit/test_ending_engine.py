import pytest
from backend.app.models.ending import Ending
from backend.app.services.ending_engine import (
    evaluate_condition_clause,
    evaluate_ending,
)


def test_evaluate_condition_operators():
    state = {
        "trust": 75,
        "fear": 90,
        "truth_discovered": True,
        "secret_discovered": False,
        "location": "shrine",
    }

    # Greater than
    assert evaluate_condition_clause("trust", {">": 70}, state) is True
    assert evaluate_condition_clause("trust", {">": 80}, state) is False

    # Less than
    assert evaluate_condition_clause("trust", {"<": 30}, state) is False

    # Equality and Booleans
    assert evaluate_condition_clause("truth_discovered", True, state) is True
    assert evaluate_condition_clause("secret_discovered", False, state) is True
    assert evaluate_condition_clause("location", "shrine", state) is True


def test_ending_a_condition():
    """Ending A: trust > 70 AND truth_discovered = true."""
    ending_a = Ending(
        id=1,
        story_id=1,
        name="Dawn over Mayoiga",
        conditions={"trust": {">": 70}, "truth_discovered": True},
        seal_text="MAYOIGA_TRUTH",
    )

    # Satisfied
    assert evaluate_ending(ending_a, {"trust": 75, "truth_discovered": True}) is True

    # Unsatisfied (trust <= 70)
    assert evaluate_ending(ending_a, {"trust": 70, "truth_discovered": True}) is False

    # Unsatisfied (truth_discovered is False)
    assert evaluate_ending(ending_a, {"trust": 85, "truth_discovered": False}) is False


def test_ending_b_condition():
    """Ending B: trust < 30 AND betrayal_detected = true."""
    ending_b = Ending(
        id=2,
        story_id=1,
        name="The Shattered Teacup",
        conditions={"trust": {"<": 30}, "betrayal_detected": True},
        seal_text="SHATTERED_TRUST",
    )

    # Satisfied
    assert evaluate_ending(ending_b, {"trust": 25, "betrayal_detected": True}) is True

    # Unsatisfied
    assert evaluate_ending(ending_b, {"trust": 40, "betrayal_detected": True}) is False


def test_ending_c_condition():
    """Ending C: fear > 85 AND escape_chosen = true."""
    ending_c = Ending(
        id=3,
        story_id=1,
        name="Flight into the Mists",
        conditions={"fear": {">": 85}, "escape_chosen": True},
        seal_text="MIST_FLIGHT",
    )

    assert evaluate_ending(ending_c, {"fear": 92, "escape_chosen": True}) is True
    assert evaluate_ending(ending_c, {"fear": 80, "escape_chosen": True}) is False


def test_ending_d_condition():
    """Ending D: secret_discovered = false."""
    ending_d = Ending(
        id=4,
        story_id=1,
        name="Eternal Obscurity",
        conditions={"secret_discovered": False},
        seal_text="ETERNAL_FOG",
    )

    assert evaluate_ending(ending_d, {"secret_discovered": False}) is True
    assert evaluate_ending(ending_d, {"secret_discovered": True}) is False
