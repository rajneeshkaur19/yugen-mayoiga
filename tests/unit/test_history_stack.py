
from dataclasses import dataclass

import pytest

from algorithms.history_stack import HistoryStack, StateDelta


@dataclass
class DummyState:
    scene: str = "start"
    courage: int = 5
    fear: int = 2


def test_undo_restores_previous_attribute_value():
    state = DummyState()
    stack = HistoryStack()

    state.scene = "forest"
    stack.push([StateDelta(state, "scene", "start", "forest")])

    stack.undo()

    assert state.scene == "start"


def test_undo_restores_multiple_attributes():
    state = DummyState()
    stack = HistoryStack()

    state.courage = 8
    state.fear = 1
    stack.push([
        StateDelta(state, "courage", 5, 8),
        StateDelta(state, "fear", 2, 1),
    ])

    stack.undo()

    assert state.courage == 5
    assert state.fear == 2


def test_multiple_undo_operations_follow_lifo_order():
    state = DummyState()
    stack = HistoryStack()

    state.courage = 6
    stack.push([StateDelta(state, "courage", 5, 6)])

    state.courage = 9
    stack.push([StateDelta(state, "courage", 6, 9)])

    stack.undo()
    assert state.courage == 6

    stack.undo()
    assert state.courage == 5


def test_undo_on_empty_stack_raises_error():
    stack = HistoryStack()

    with pytest.raises(IndexError, match="Nothing to undo"):
        stack.undo()


def test_empty_delta_record_is_rejected():
    stack = HistoryStack()

    with pytest.raises(ValueError, match="empty delta"):
        stack.push([])


def test_peek_does_not_remove_record():
    state = DummyState()
    stack = HistoryStack()
    delta = StateDelta(state, "scene", "start", "forest")
    stack.push([delta])

    assert stack.peek() == [delta]
    assert len(stack) == 1


def test_clear_removes_all_records():
    state = DummyState()
    stack = HistoryStack()
    stack.push([StateDelta(state, "scene", "start", "forest")])

    stack.clear()

    assert stack.is_empty()
    assert len(stack) == 0
    assert stack.peek() is None

def test_undo_removes_dictionary_key_that_was_added():
    from algorithms.history_stack import HistoryStack, StateDelta

    class Character:
        traits = {}

    character = Character()

    delta = StateDelta.for_dict_entry(
        target=character,
        attribute="traits",
        key="curiosity",
        old_value=None,
        new_value=75,
        existed_before=False,
    )

    character.traits["curiosity"] = 75

    stack = HistoryStack()
    stack.push([delta])
    stack.undo()

    assert "curiosity" not in character.traits
