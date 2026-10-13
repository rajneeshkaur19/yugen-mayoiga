
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

    def make_choice(self, choice_id: str):
        """Apply a choice and move to its destination scene."""
        if self.current_scene.is_ending:
            raise ValueError("The story has already ended.")

        choice = self.current_scene.get_choice(choice_id)

        choice.apply_to(self.character)
        self.current_scene_id = choice.next_scene_id
        self.history.append(self.current_scene_id)

        return self.current_scene
