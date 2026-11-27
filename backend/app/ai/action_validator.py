"""Deterministic Action Validation and Execution Service for Yūgen Mayoiga.

Enforces strict server-side validation over AI-generated choices and interpreted
player actions. Ensures that AI suggestions never bypass game rules, state consistency,
or security boundaries before routing to the existing deterministic action pipeline.
"""

from __future__ import annotations

import re
from typing import Any, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ai.action_interpreter import ActionInterpreter
from backend.app.ai.context_builder import StoryContextBuilder
from backend.app.core.timing import pipeline_timer
from backend.app.ai.providers import BaseLLMProvider
from backend.app.ai.schemas import (
    AIActionExecutionResponse,
    AIStoryActionRequest,
    DynamicChoice,
    InterpretedAction,
    InterpretationStatus,
    StoryAIContext,
)
from backend.app.models.character import Character
from backend.app.models.story import Story
from backend.app.services.action_pipeline import process_story_action
from backend.app.services.state_service import get_or_create_story_state

PERMITTED_ACTION_VERBS = {
    "inspect",
    "examine",
    "check",
    "observe",
    "read",
    "scrutinize",
    "look",
    "speak",
    "talk",
    "ask",
    "tell",
    "whisper",
    "question",
    "comfort",
    "search",
    "investigate",
    "explore",
    "feel",
    "use",
    "open",
    "unlock",
    "light",
    "ignite",
    "ring",
    "drink",
    "apply",
    "move",
    "walk",
    "step",
    "approach",
    "enter",
    "retreat",
    "flee",
    "take",
    "grab",
    "pick up",
    "pocket",
    "retrieve",
    "wait",
    "listen",
    "pause",
    "hesitate",
    "hide",
    "touch",
    "wipe",
}

FORBIDDEN_KEYWORDS = {
    "exec",
    "eval",
    "sql",
    "drop",
    "delete",
    "insert",
    "update",
    "truncate",
    "admin",
    "system",
    "script",
    "__import__",
    "subprocess",
}


class DeterministicActionValidator:
    """Validates dynamic choices and interpreted free-text actions against game rules."""

    @staticmethod
    def validate_dynamic_choice(
        choice: DynamicChoice,
        current_scene_id: int,
    ) -> Tuple[bool, Optional[str]]:
        """Validate an AI-suggested dynamic choice before execution.

        Ensures choice is not stale, has a permitted intent verb, and does
        not contain forbidden payload patterns.
        """
        if choice.scene_id is not None and choice.scene_id != current_scene_id:
            return (
                False,
                f"Stale dynamic choice: originated from scene {choice.scene_id}, but current scene is {current_scene_id}.",
            )

        intent_lower = (choice.action_intent or "").strip().lower()
        if intent_lower not in PERMITTED_ACTION_VERBS:
            return (
                False,
                f"Action intent '{choice.action_intent}' is not permitted by the deterministic gameplay engine.",
            )

        for kw in FORBIDDEN_KEYWORDS:
            if (
                kw in intent_lower
                or (choice.target and kw in choice.target.lower())
                or (choice.approach and kw in choice.approach.lower())
            ):
                return False, f"Action contains forbidden keyword or command structure: '{kw}'."

        return True, None

    @staticmethod
    def validate_interpreted_action(
        action: InterpretedAction,
        context: StoryAIContext,
    ) -> Tuple[bool, Optional[str]]:
        """Validate an AI-interpreted action before routing to state modification."""
        if action.is_ambiguous:
            return (
                False,
                action.clarification_needed
                or "The action is ambiguous or contains multiple steps. Please clarify.",
            )

        if not action.is_supported:
            return (
                False,
                action.clarification_needed
                or "The requested action is not supported within this narrative context.",
            )

        if action.confidence < 30:
            return (
                False,
                action.clarification_needed
                or "Interpretation confidence is too low. Please be more specific.",
            )

        intent_lower = (action.action_intent or "").strip().lower()
        if intent_lower not in PERMITTED_ACTION_VERBS:
            return (
                False,
                f"Action intent '{action.action_intent}' is not an authorized narrative verb.",
            )

        for kw in FORBIDDEN_KEYWORDS:
            if (
                kw in intent_lower
                or (action.target and kw in action.target.lower())
                or (action.approach and kw in action.approach.lower())
            ):
                return False, f"Action rejected: contains disallowed instruction keyword '{kw}'."

        # Character target validation: if a companion is addressed, ensure they exist in context
        if action.character_target:
            target_name = action.character_target.strip().lower()
            present_names = [c.name.strip().lower() for c in context.characters]
            if target_name not in present_names:
                return (
                    False,
                    f"Target character '{action.character_target}' is not present in this scene.",
                )

        return True, None


def execute_ai_mediated_action(
    db: Session,
    user_id: int,
    story_id: int,
    action_request: AIStoryActionRequest,
    provider: Optional[BaseLLMProvider] = None,
) -> AIActionExecutionResponse:
    """Safely coordinate AI interpretation, deterministic validation, and state execution.

    Flow:
    1. Authenticate story ownership and build fresh StoryAIContext
    2. If DynamicChoice: validate scene binding and permitted intent
    3. If Free-Text: interpret intent with ActionInterpreter, then validate deterministically
    4. If valid: call deterministic process_story_action atomically
    5. If ambiguous or invalid: return structured diagnostic without mutating state
    """
    # 1. Verify story ownership
    story = db.scalar(
        select(Story).where(
            Story.id == story_id,
            Story.user_id == user_id,
        )
    )
    if story is None:
        raise ValueError(f"Story {story_id} not found or does not belong to user {user_id}.")

    # 2. Ensure runtime state exists
    story_state = get_or_create_story_state(db, story_id, commit=True)
    current_scene_id = story_state.current_scene_id or 0
    validator = DeterministicActionValidator()

    # 3. Handle DynamicChoice submission (fast path: skip unnecessary AI context build)
    if action_request.dynamic_choice is not None:
        choice = action_request.dynamic_choice
        with pipeline_timer("Deterministic Dynamic Choice Validation", {"choice_id": choice.choice_id, "scene_id": current_scene_id}) as val_timer:
            is_valid, error_msg = validator.validate_dynamic_choice(
                choice=choice,
                current_scene_id=current_scene_id,
            )
            val_timer["valid"] = is_valid

        if not is_valid:
            return AIActionExecutionResponse(
                status="rejected",
                interpretation=None,
                story_action_result=None,
                clarification_needed=None,
                validation_error=error_msg,
            )

        # Route to deterministic engine with validated choice text
        with pipeline_timer("State Mutation / Database Operations", {"action": "dynamic_choice", "story_id": story_id}):
            action_result = process_story_action(
                db=db,
                user_id=user_id,
                story_id=story_id,
                free_text=choice.choice_text,
                active_character_id=action_request.character_id,
            )

        return AIActionExecutionResponse(
            status="executed",
            interpretation=None,
            story_action_result=action_result,
            clarification_needed=None,
            validation_error=None,
        )

    # 4. Handle Free-Text submission (requires AI interpretation + deterministic validation)
    if action_request.free_text is not None and action_request.free_text.strip():
        # Build context with compact limits for local model performance
        context_builder = StoryContextBuilder(db)
        context = context_builder.build(story_id=story_id, memory_limit=2, history_limit=2)

        interpreter = ActionInterpreter(provider=provider)
        interp_result = interpreter.interpret(
            context=context,
            player_text=action_request.free_text.strip(),
        )

        if interp_result.status == InterpretationStatus.UNAVAILABLE:
            return AIActionExecutionResponse(
                status="unavailable",
                interpretation=None,
                story_action_result=None,
                clarification_needed=None,
                validation_error=interp_result.error_message or "AI service unavailable.",
            )

        if interp_result.status == InterpretationStatus.AMBIGUOUS:
            action = interp_result.interpreted_action
            return AIActionExecutionResponse(
                status="ambiguous",
                interpretation=action,
                story_action_result=None,
                clarification_needed=(
                    action.clarification_needed if action else "Action is ambiguous. Please clarify."
                ),
                validation_error=None,
            )

        if interp_result.status == InterpretationStatus.UNSUPPORTED:
            action = interp_result.interpreted_action
            clarification = action.clarification_needed if action and action.clarification_needed else None
            return AIActionExecutionResponse(
                status="rejected",
                interpretation=action,
                story_action_result=None,
                clarification_needed=clarification,
                validation_error=clarification or "The requested action is not supported within this narrative context.",
            )

        if interp_result.status == InterpretationStatus.FAILED or interp_result.interpreted_action is None:
            return AIActionExecutionResponse(
                status="rejected",
                interpretation=None,
                story_action_result=None,
                clarification_needed=None,
                validation_error=interp_result.error_message or "Failed to interpret action.",
            )

        interpreted_action = interp_result.interpreted_action

        # Deterministic validation over interpreted action
        with pipeline_timer("Deterministic Interpreted Action Validation") as val_timer:
            is_valid, error_msg = validator.validate_interpreted_action(
                action=interpreted_action,
                context=context,
            )
            val_timer["valid"] = is_valid

        if not is_valid:
            return AIActionExecutionResponse(
                status="rejected",
                interpretation=interpreted_action,
                story_action_result=None,
                clarification_needed=interpreted_action.clarification_needed,
                validation_error=error_msg,
            )

        # Route approved action through deterministic engine
        with pipeline_timer("State Mutation / Database Operations", {"action": "free_text", "story_id": story_id}):
            action_result = process_story_action(
                db=db,
                user_id=user_id,
                story_id=story_id,
                free_text=interpreted_action.original_text,
                active_character_id=action_request.character_id,
            )

        return AIActionExecutionResponse(
            status="executed",
            interpretation=interpreted_action,
            story_action_result=action_result,
            clarification_needed=None,
            validation_error=None,
        )

    raise ValueError("Either 'free_text' or 'dynamic_choice' must be provided in action request.")
