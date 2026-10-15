from dataclasses import dataclass, field
from typing import Any

from algorithms.history_stack import HistoryStack, StateDelta

from .character import Character
from .story import Story


@dataclass
class StoryState:
    story: Story
    character: Character
    current_scene_id: str = ""
    history: list[str] = field(default_factory=list)

    _undo_stack: HistoryStack = field(
        default_factory=HistoryStack,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.story.scenes:
            raise ValueError("Cannot start a story without scenes.")

        if not self.story.start_scene_id:
            raise ValueError("Story must define a starting scene.")

        self.story.validate()

        if not self.current_scene_id:
            self.current_scene_id = self.story.start_scene_id

        if self.current_scene_id not in self.story.scenes:
            raise ValueError(
                f"Scene '{self.current_scene_id}' does not exist."
            )

        if not self.history:
            self.history.append(self.current_scene_id)

    @property
    def current_scene(self):
        return self.story.get_scene(self.current_scene_id)

    @staticmethod
    def _dict_deltas(
        target: Any,
        attribute: str,
        before: dict,
        after: dict,
    ) -> list[StateDelta]:
        """Create deltas only for dictionary entries that actually changed."""
        deltas: list[StateDelta] = []

        for key in before.keys() | after.keys():
            existed_before = key in before
            exists_after = key in after

            old_value = before.get(key)
            new_value = after.get(key)

            if existed_before == exists_after and old_value == new_value:
                continue

            # A removed key is restored by reversing this delta.
            # A newly added key is deleted when this delta is reversed.
            deltas.append(
                StateDelta.for_dict_entry(
                    target=target,
                    attribute=attribute,
                    key=key,
                    old_value=old_value,
                    new_value=new_value,
                    existed_before=existed_before,
                )
            )

        return deltas

    def make_choice(self, choice_id: str):
        """Apply a choice and record only the state changes it produces."""
        if self.current_scene.is_ending:
            raise ValueError("The story has already ended.")

        choice = self.current_scene.get_choice(choice_id)

        # Keep temporary copies so a failed choice can be rolled back safely.
        old_scene_id = self.current_scene_id
        old_history = self.history.copy()
        old_traits = self.character.traits.copy()
        old_emotions = self.character.emotions.copy()

        try:
            choice.apply_to(self.character)

            self.current_scene_id = choice.next_scene_id
            self.history.append(self.current_scene_id)

            deltas: list[StateDelta] = [
                StateDelta.for_attribute(
                    self,
                    "current_scene_id",
                    old_scene_id,
                    self.current_scene_id,
                ),
                StateDelta.for_attribute(
                    self,
                    "history",
                    old_history,
                    self.history.copy(),
                ),
            ]

            deltas.extend(
                self._dict_deltas(
                    self.character,
                    "traits",
                    old_traits,
                    self.character.traits,
                )
            )

            deltas.extend(
                self._dict_deltas(
                    self.character,
                    "emotions",
                    old_emotions,
                    self.character.emotions,
                )
            )

            self._undo_stack.push(deltas)

        except Exception:
            # Restore state even if applying the choice fails partway through.
            self.character.traits = old_traits
            self.character.emotions = old_emotions
            self.current_scene_id = old_scene_id
            self.history = old_history
            raise

        return self.current_scene

    def undo(self):
        """Undo the latest choice and return to the previous scene."""
        if self._undo_stack.is_empty():
            raise ValueError("Nothing to undo.")

        self._undo_stack.undo()
        return self.current_scene