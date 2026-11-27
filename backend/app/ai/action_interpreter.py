"""Free-Text Action Interpreter for Yūgen Mayoiga.

Translates player natural language into structured semantic intent, targets,
and approaches using configured LLM providers while defending against prompt injection,
multi-action overloading, and ambiguity.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from pydantic import ValidationError

from backend.app.core.timing import pipeline_timer
from backend.app.ai.exceptions import (
    AIConfigurationError,
    AIEmptyResponseError,
    AINarrativeError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AITimeoutError,
)
from backend.app.ai.prompts.action_prompt import (
    ACTION_INTERPRETER_SYSTEM_INSTRUCTION,
    build_action_user_prompt,
)
from backend.app.ai.providers import BaseLLMProvider, OllamaProvider, get_default_provider
from backend.app.ai.schemas import (
    ActionInterpretationResult,
    InterpretedAction,
    InterpretationStatus,
    StoryAIContext,
)


def _strip_markdown_code_fences(text: str) -> str:
    """Strip leading/trailing markdown code fences (```json ... ```) from provider output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_robust(text: str) -> dict:
    """Robustly parse JSON object with substring fallback."""
    cleaned = _strip_markdown_code_fences(text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        data = json.loads(cleaned[first_brace : last_brace + 1])
        if isinstance(data, dict):
            return data

    raise json.JSONDecodeError("Could not locate valid JSON object in output", cleaned, 0)


# Simple pattern matching for overt prompt injection / override phrases
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?(prompt|secrets?|keys?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an?\s+)?admin", re.IGNORECASE),
    re.compile(r"drop\s+table", re.IGNORECASE),
    re.compile(r"set\s+(yugen_meter|turn_number|trust)\s*=", re.IGNORECASE),
]


class ActionInterpreter:
    """Dedicated service for interpreting player natural-language actions into structured intent."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None) -> None:
        self._provider = provider

    def _resolve_provider(self) -> Optional[BaseLLMProvider]:
        if self._provider is not None:
            return self._provider
        try:
            return get_default_provider()
        except AIConfigurationError:
            return None

    def interpret(
        self,
        context: StoryAIContext,
        player_text: str,
    ) -> ActionInterpretationResult:
        """Parse natural language player action into structured semantic intent.

        Parameters
        ----------
        context : StoryAIContext
            The read-only story context snapshot.
        player_text : str
            Raw untrusted natural language text submitted by the player.

        Returns
        -------
        ActionInterpretationResult
            Result envelope containing the validated InterpretedAction and status.
        """
        if not isinstance(context, StoryAIContext):
            raise TypeError(
                f"Expected context to be an instance of StoryAIContext, got {type(context).__name__}"
            )

        if not isinstance(player_text, str) or not player_text.strip():
            return ActionInterpretationResult(
                interpreted_action=None,
                status=InterpretationStatus.FAILED,
                error_message="Player text cannot be empty or blank.",
            )

        clean_text = player_text.strip()

        # Guard against overt prompt injection patterns early
        for pat in INJECTION_PATTERNS:
            if pat.search(clean_text):
                action = InterpretedAction(
                    original_text=clean_text,
                    action_intent="other",
                    target=None,
                    approach=None,
                    character_target=None,
                    parameters={},
                    confidence=0,
                    is_ambiguous=False,
                    clarification_needed="Actions cannot directly alter internal game state or system rules.",
                    reasoning_summary="Prompt injection or state override attempt intercepted.",
                    is_supported=False,
                )
                return ActionInterpretationResult(
                    interpreted_action=action,
                    status=InterpretationStatus.UNSUPPORTED,
                    error_message=None,
                )

        provider = self._resolve_provider()
        if provider is None:
            return ActionInterpretationResult(
                interpreted_action=None,
                status=InterpretationStatus.UNAVAILABLE,
                error_message="No AI provider configured (missing API keys).",
            )

        prompt = build_action_user_prompt(context=context, player_text=clean_text)

        try:
            is_local = isinstance(provider, OllamaProvider)
            interp_max_tokens = 256 if is_local else 96
            with pipeline_timer("AI Action Interpretation", {"player_text": clean_text[:40]}) as timer_info:
                try:
                    raw_output, tokens = provider.generate(
                        prompt=prompt,
                        system_instruction=ACTION_INTERPRETER_SYSTEM_INSTRUCTION,
                        max_tokens=interp_max_tokens,
                    )
                except TypeError:
                    raw_output, tokens = provider.generate(
                        prompt=prompt,
                        system_instruction=ACTION_INTERPRETER_SYSTEM_INSTRUCTION,
                    )
                timer_info["model"] = provider.model_name
                timer_info["tokens"] = tokens

            if not raw_output or not raw_output.strip():
                return ActionInterpretationResult(
                    interpreted_action=None,
                    status=InterpretationStatus.FAILED,
                    error_message="Provider returned empty response.",
                )

            try:
                parsed_json = _parse_json_robust(raw_output)
            except json.JSONDecodeError as exc:
                return ActionInterpretationResult(
                    interpreted_action=None,
                    status=InterpretationStatus.FAILED,
                    error_message=f"Invalid JSON from provider: {exc}",
                )

            if not isinstance(parsed_json, dict):
                return ActionInterpretationResult(
                    interpreted_action=None,
                    status=InterpretationStatus.FAILED,
                    error_message="Unexpected JSON structure; expected an object.",
                )

            # Strict preservation of original text
            parsed_json["original_text"] = clean_text

            # Enforce confidence bounds
            conf = parsed_json.get("confidence", 50)
            if not isinstance(conf, int) or conf < 0 or conf > 100:
                parsed_json["confidence"] = max(0, min(100, int(conf) if isinstance(conf, (int, float)) else 50))

            # Normalize string lengths to prevent validation errors on descriptive local LLMs
            if isinstance(parsed_json.get("action_intent"), str):
                parsed_json["action_intent"] = parsed_json["action_intent"][:50].strip()
            if isinstance(parsed_json.get("target"), str):
                parsed_json["target"] = parsed_json["target"][:100].strip()
            if isinstance(parsed_json.get("approach"), str):
                parsed_json["approach"] = parsed_json["approach"][:100].strip()
            if isinstance(parsed_json.get("character_target"), str):
                parsed_json["character_target"] = parsed_json["character_target"][:100].strip()
            if isinstance(parsed_json.get("clarification_needed"), str):
                parsed_json["clarification_needed"] = parsed_json["clarification_needed"][:300].strip()
            if isinstance(parsed_json.get("reasoning_summary"), str):
                parsed_json["reasoning_summary"] = parsed_json["reasoning_summary"][:300].strip()

            # Filter to defined schema fields
            valid_keys = set(InterpretedAction.model_fields.keys())
            filtered_json = {k: v for k, v in parsed_json.items() if k in valid_keys}

            try:
                action = InterpretedAction.model_validate(filtered_json)
            except ValidationError as val_err:
                return ActionInterpretationResult(
                    interpreted_action=None,
                    status=InterpretationStatus.FAILED,
                    error_message=f"Response schema validation failed: {val_err}",
                )

            # Determine high-level interpretation status
            if action.is_ambiguous:
                status = InterpretationStatus.AMBIGUOUS
            elif not action.is_supported:
                status = InterpretationStatus.UNSUPPORTED
            else:
                status = InterpretationStatus.SUCCESS

            return ActionInterpretationResult(
                interpreted_action=action,
                status=status,
                error_message=None,
            )

        except (
            AITimeoutError,
            AIRateLimitError,
            AIEmptyResponseError,
            AIResponseValidationError,
            AIProviderError,
            AINarrativeError,
        ) as exc:
            return ActionInterpretationResult(
                interpreted_action=None,
                status=InterpretationStatus.FAILED,
                error_message=str(exc),
            )
        except Exception as exc:
            return ActionInterpretationResult(
                interpreted_action=None,
                status=InterpretationStatus.FAILED,
                error_message=f"Unexpected error during action interpretation: {exc}",
            )
