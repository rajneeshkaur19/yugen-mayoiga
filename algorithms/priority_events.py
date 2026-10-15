
"""Queue and heap-based event scheduling for Yugen Mayoiga."""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from itertools import count
from typing import Any
from collections import deque


@dataclass(frozen=True)
class StoryEvent:
    """An event scheduled to occur during a story session."""

    event_id: str
    due_time: int
    priority: int
    payload: Any = None


@dataclass
class PriorityEventManager:
    """Manage pending, scheduled, and ready story events.

    Pending events enter in FIFO order.
    Scheduled events are promoted when their due time is reached.
    Ready events are processed by highest priority first.
    """

    pending: deque[StoryEvent] = field(default_factory=deque)
    _scheduled: list[tuple[int, int, StoryEvent]] = field(
        default_factory=list, repr=False
    )
    _ready: list[tuple[int, int, StoryEvent]] = field(
        default_factory=list, repr=False
    )
    _counter: Any = field(default_factory=count, repr=False)

    def add_event(self, event: StoryEvent) -> None:
        """Add an event to the pending FIFO queue."""
        self.pending.append(event)

    def schedule_pending(self) -> int:
        """Move all pending events into the scheduled min-heap.

        Returns the number of events scheduled.
        """
        scheduled_count = 0

        while self.pending:
            event = self.pending.popleft()
            heappush(
                self._scheduled,
                (event.due_time, next(self._counter), event),
            )
            scheduled_count += 1

        return scheduled_count

    def promote_due_events(self, current_time: int) -> int:
        """Move events due by current_time into the ready max-priority heap.

        Returns the number of events promoted.
        """
        promoted_count = 0

        while self._scheduled and self._scheduled[0][0] <= current_time:
            _, sequence, event = heappop(self._scheduled)
            heappush(self._ready, (-event.priority, sequence, event))
            promoted_count += 1

        return promoted_count

    def pop_ready_event(self) -> StoryEvent | None:
        """Remove and return the highest-priority ready event."""
        if not self._ready:
            return None

        _, _, event = heappop(self._ready)
        return event

    def peek_next_scheduled(self) -> StoryEvent | None:
        """Return the next scheduled event without removing it."""
        if not self._scheduled:
            return None

        return self._scheduled[0][2]

    def __len__(self) -> int:
        """Return the total number of events across all stages."""
        return len(self.pending) + len(self._scheduled) + len(self._ready)
