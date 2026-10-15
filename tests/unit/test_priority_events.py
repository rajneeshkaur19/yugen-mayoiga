
from algorithms.priority_events import StoryEvent, PriorityEventManager


def test_pending_events_follow_fifo_order():
    manager = PriorityEventManager()
    first = StoryEvent("e1", 5, 1)
    second = StoryEvent("e2", 3, 2)

    manager.add_event(first)
    manager.add_event(second)

    assert manager.pending.popleft() == first
    assert manager.pending.popleft() == second


def test_schedule_pending_orders_events_by_due_time():
    manager = PriorityEventManager()
    later = StoryEvent("later", 10, 1)
    earlier = StoryEvent("earlier", 3, 1)

    manager.add_event(later)
    manager.add_event(earlier)

    assert manager.schedule_pending() == 2
    assert manager.peek_next_scheduled() == earlier


def test_only_due_events_are_promoted():
    manager = PriorityEventManager()
    due = StoryEvent("due", 2, 1)
    future = StoryEvent("future", 8, 5)

    manager.add_event(due)
    manager.add_event(future)
    manager.schedule_pending()

    assert manager.promote_due_events(3) == 1
    assert manager.pop_ready_event() == due
    assert manager.peek_next_scheduled() == future


def test_ready_events_follow_highest_priority_first():
    manager = PriorityEventManager()
    low = StoryEvent("low", 1, 1)
    high = StoryEvent("high", 1, 10)
    medium = StoryEvent("medium", 1, 5)

    for event in (low, high, medium):
        manager.add_event(event)

    manager.schedule_pending()
    assert manager.promote_due_events(1) == 3

    assert manager.pop_ready_event() == high
    assert manager.pop_ready_event() == medium
    assert manager.pop_ready_event() == low


def test_equal_priorities_preserve_insertion_order():
    manager = PriorityEventManager()
    first = StoryEvent("first", 1, 5)
    second = StoryEvent("second", 1, 5)

    manager.add_event(first)
    manager.add_event(second)
    manager.schedule_pending()
    manager.promote_due_events(1)

    assert manager.pop_ready_event() == first
    assert manager.pop_ready_event() == second


def test_empty_manager_returns_none():
    manager = PriorityEventManager()

    assert manager.pop_ready_event() is None
    assert manager.peek_next_scheduled() is None
    assert len(manager) == 0


def test_event_count_tracks_all_stages():
    manager = PriorityEventManager()
    event = StoryEvent("e1", 5, 1)

    manager.add_event(event)
    assert len(manager) == 1

    manager.schedule_pending()
    assert len(manager) == 1

    manager.promote_due_events(5)
    assert len(manager) == 1

    manager.pop_ready_event()
    assert len(manager) == 0
