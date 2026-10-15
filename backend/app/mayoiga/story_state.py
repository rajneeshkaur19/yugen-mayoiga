
from copy import deepcopy
from dataclasses import dataclass, field

from .character import Character
from .story import Story


@dataclass
class StoryState:
    """Tracks the current progress of a story session."""

    story: Story
    character: Character
    current_scene_id: str = ""
    history: list[str] = field(default_factory=list)
    _undo_stack: list[dict] = field(
        default_factory=list,
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

        self.history.append(self.current_scene_id)

    @property
    def current_scene(self):
        """Return the scene currently being played."""
        return self.story.get_scene(self.current_scene_id)

    def _save_snapshot(self) -> None:
        """Save the current state before applying a choice."""
        self._undo_stack.append(
            {
                "current_scene_id": self.current_scene_id,
                "history": self.history.copy(),
                "traits": deepcopy(self.character.traits),
                "emotions": deepcopy(self.character.emotions),
            }
        )

    def make_choice(self, choice_id: str):
        """Apply a choice and move to its destination scene."""
        if self.current_scene.is_ending:
            raise ValueError("The story has already ended.")

        choice = self.current_scene.get_choice(choice_id)

        self._save_snapshot()
        try:
            choice.apply_to(self.character)
        except Exception:
            self._undo_stack.pop()
            raise

        self.current_scene_id = choice.next_scene_id
        self.history.append(self.current_scene_id)

        return self.current_scene

    def undo(self):
        """Restore the state saved before the most recent choice."""
        if not self._undo_stack:
            raise ValueError("Nothing to undo.")

        snapshot = self._undo_stack.pop()

        self.current_scene_id = snapshot["current_scene_id"]
        self.history = snapshot["history"]
        self.character.traits = snapshot["traits"]
        self.character.emotions = snapshot["emotions"]

        return self.current_scene
