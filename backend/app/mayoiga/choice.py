
from dataclasses import dataclass, field


@dataclass
class Choice:
    """Represents a user's choice and its effects on the story."""

    id: str
    text: str
    next_scene_id: str
    emotion_deltas: dict[str, float] = field(default_factory=dict)
    trait_deltas: dict[str, float] = field(default_factory=dict)

    def apply_to(self, character) -> None:
        """Apply this choice's emotion and trait changes to a character."""
        for emotion, delta in self.emotion_deltas.items():
            character.update_emotion(emotion, delta)

        for trait, delta in self.trait_deltas.items():
            character.update_trait(trait, delta)
