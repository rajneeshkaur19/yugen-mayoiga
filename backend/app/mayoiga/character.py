
from dataclasses import dataclass, field


@dataclass
class Character:
    """Represents a character and their evolving traits and emotions."""

    id: str
    name: str
    traits: dict[str, float] = field(default_factory=dict)
    emotions: dict[str, float] = field(default_factory=dict)

    def update_emotion(self, emotion: str, delta: float) -> None:
        """Update an emotion, keeping its value between 0 and 100."""
        current = self.emotions.get(emotion, 50.0)
        self.emotions[emotion] = max(0.0, min(100.0, current + delta))

    def update_trait(self, trait: str, delta: float) -> None:
        """Update a trait, keeping its value between 0 and 100."""
        current = self.traits.get(trait, 50.0)
        self.traits[trait] = max(0.0, min(100.0, current + delta))
