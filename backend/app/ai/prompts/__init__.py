"""AI Prompt templates package."""

from backend.app.ai.prompts.action_prompt import (
    ACTION_INTERPRETER_SYSTEM_INSTRUCTION,
    build_action_user_prompt,
)
from backend.app.ai.prompts.choice_prompt import (
    CHOICE_SYSTEM_INSTRUCTION,
    build_choice_user_prompt,
)
from backend.app.ai.prompts.consistency_prompt import (
    CONSISTENCY_SYSTEM_INSTRUCTION,
    build_consistency_user_prompt,
)
from backend.app.ai.prompts.narrative_prompt import (
    SYSTEM_INSTRUCTION,
    build_narrative_user_prompt,
)

__all__ = [
    "SYSTEM_INSTRUCTION",
    "build_narrative_user_prompt",
    "CONSISTENCY_SYSTEM_INSTRUCTION",
    "build_consistency_user_prompt",
    "CHOICE_SYSTEM_INSTRUCTION",
    "build_choice_user_prompt",
    "ACTION_INTERPRETER_SYSTEM_INSTRUCTION",
    "build_action_user_prompt",
]
