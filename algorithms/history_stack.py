"""Delta-based undo stack for Yugen Mayoiga."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StateDelta:
    """Represent one reversible attribute or dictionary-entry change."""

    target: Any
    attribute: str
    old_value: Any
    new_value: Any
    key: str | None = None
    existed_before: bool = True

    @classmethod
    def for_attribute(
        cls,
        target: Any,
        attribute: str,
        old_value: Any,
        new_value: Any,
    ) -> "StateDelta":
        return cls(target, attribute, old_value, new_value)

    @classmethod
    def for_dict_entry(
        cls,
        target: Any,
        attribute: str,
        key: str,
        old_value: Any,
        new_value: Any,
        *,
        existed_before: bool = True,
    ) -> "StateDelta":
        return cls(
            target=target,
            attribute=attribute,
            old_value=old_value,
            new_value=new_value,
            key=key,
            existed_before=existed_before,
        )

    def reverse(self) -> None:
        """Restore the value that existed before this change."""
        if self.key is None:
            setattr(self.target, self.attribute, self.old_value)
            return

        mapping = getattr(self.target, self.attribute)

        if not self.existed_before:
            mapping.pop(self.key, None)
        else:
            mapping[self.key] = self.old_value


@dataclass
class HistoryStack:
    """Store completed actions and undo them in LIFO order."""

    _stack: list[list[StateDelta]] = field(
        default_factory=list,
        repr=False,
    )

    def push(self, deltas: list[StateDelta]) -> None:
        """Record the deltas for one completed action."""
        if not deltas:
            raise ValueError("Cannot push an empty delta record.")

        self._stack.append(list(deltas))

    def undo(self) -> list[StateDelta]:
        """Reverse the latest action and return its deltas."""
        if self.is_empty():
            raise IndexError("Nothing to undo.")

        deltas = self._stack[-1]

        for delta in reversed(deltas):
            delta.reverse()

        self._stack.pop()
        return deltas

    def peek(self) -> list[StateDelta] | None:
        """Return a copy of the latest record without removing it."""
        if self.is_empty():
            return None

        return self._stack[-1].copy()

    def clear(self) -> None:
        """Remove all stored action records."""
        self._stack.clear()

    def is_empty(self) -> bool:
        """Return whether the stack contains no actions."""
        return not self._stack

    def __len__(self) -> int:
        """Return the number of stored actions."""
        return len(self._stack)