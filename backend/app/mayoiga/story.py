
from dataclasses import dataclass, field

from .scene import Scene


@dataclass
class Story:
    """Manages the scenes and starting point of a story."""

    id: str
    title: str
    scenes: dict[str, Scene] = field(default_factory=dict)
    start_scene_id: str = ""

    def add_scene(self, scene: Scene) -> None:
        """Add a scene while preventing duplicate IDs."""
        if scene.id in self.scenes:
            raise ValueError(f"Duplicate scene ID: {scene.id}")

        self.scenes[scene.id] = scene

    def get_scene(self, scene_id: str) -> Scene:
        """Retrieve a scene by its ID."""
        if scene_id not in self.scenes:
            raise ValueError(f"Scene '{scene_id}' does not exist.")

        return self.scenes[scene_id]

    def validate(self) -> None:
        """Validate the starting scene and choice destinations."""
        if not self.scenes:
            raise ValueError("A story must contain at least one scene.")

        if self.start_scene_id not in self.scenes:
            raise ValueError("The starting scene must exist in the story.")

        for scene in self.scenes.values():
            for choice in scene.choices:
                if choice.next_scene_id not in self.scenes:
                    raise ValueError(
                        f"Choice '{choice.id}' points to missing scene "
                        f"'{choice.next_scene_id}'."
                    )
