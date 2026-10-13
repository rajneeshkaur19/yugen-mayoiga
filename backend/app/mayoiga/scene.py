from dataclasses import dataclass, field

from .choice import Choice


@dataclass
class Scene:
    """Represents a scene in the Yūgen Mayoiga narrative."""

    id: str
    title: str
    text: str
    choices: list[Choice] = field(default_factory=list)
    is_ending: bool = False

    def add_choice(self, choice: Choice) -> None:
        """Add a choice to this scene."""
        if any(existing.id == choice.id for existing in self.choices):
            raise ValueError(f"Duplicate choice ID: {choice.id}")

        self.choices.append(choice)

    def get_choice(self, choice_id: str) -> Choice:
        """Return a choice by its ID."""
        for choice in self.choices:
            if choice.id == choice_id:
                return choice

        raise ValueError(f"Choice '{choice_id}' not found in scene '{self.id}'.")
