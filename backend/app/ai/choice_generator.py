"""Dynamic AI Choice Generator for Yūgen Mayoiga.

Generates contextual, atmospheric, and actionable player choices using configured
LLM providers. Ensures choices are distinct, deduplicated, and marked as AI-generated
options that require deterministic validation.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

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
from backend.app.ai.language_guard import validate_output_language
from backend.app.ai.prompts.choice_prompt import (
    CHOICE_SYSTEM_INSTRUCTION,
    build_choice_user_prompt,
)
from backend.app.ai.providers import BaseLLMProvider, get_default_provider
from backend.app.ai.schemas import (
    ChoiceGenerationStatus,
    ChoiceRiskLevel,
    DynamicChoice,
    DynamicChoiceSet,
    StoryAIContext,
)


def _strip_markdown_code_fences(text: str) -> str:
    """Strip leading/trailing markdown code fences (```json ... ```) from provider output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_robust(text: str) -> Any:
    """Parse JSON with fallback extraction for local models like Phi-3."""
    cleaned = _strip_markdown_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(cleaned[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    first_bracket = cleaned.find("[")
    last_bracket = cleaned.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        try:
            return json.loads(cleaned[first_bracket : last_bracket + 1])
        except json.JSONDecodeError:
            pass

    return json.loads(cleaned)


class DynamicChoiceGenerator:
    """Dedicated service for generating context-aware narrative choices via LLM."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None) -> None:
        self._provider = provider

    def _resolve_provider(self) -> Optional[BaseLLMProvider]:
        if self._provider is not None:
            return self._provider
        try:
            return get_default_provider()
        except AIConfigurationError:
            return None

    def generate_choices(
        self,
        context: StoryAIContext,
        existing_choices: Optional[list[str]] = None,
        max_choices: int = 3,
    ) -> DynamicChoiceSet:
        """Generate a set of contextual, deduplicated dynamic AI choices.

        Parameters
        ----------
        context : StoryAIContext
            The read-only structured snapshot of the current story state.
        existing_choices : list[str], optional
            Texts of existing deterministic choices for this scene to prevent duplication.
        max_choices : int, default 3
            Maximum number of dynamic choices to return (bounded between 1 and 5).

        Returns
        -------
        DynamicChoiceSet
            Structured choice set with status, telemetry, and validated choices.
        """
        if not isinstance(context, StoryAIContext):
            raise TypeError(
                f"Expected context to be an instance of StoryAIContext, got {type(context).__name__}"
            )

        max_choices = max(1, min(5, max_choices))
        existing_choice_texts = [ec.strip().lower() for ec in (existing_choices or []) if ec]

        provider = self._resolve_provider()
        if provider is None:
            return DynamicChoiceSet(
                choices=[],
                generation_status=ChoiceGenerationStatus.UNAVAILABLE,
                generation_metadata={"error": "No AI provider configured (missing API keys)."},
            )

        prompt = build_choice_user_prompt(
            context=context,
            existing_choices=existing_choices,
            max_choices=max_choices,
        )

        try:
            with pipeline_timer("Dynamic Choice Generation", {"max_choices": max_choices}) as timer_info:
                try:
                    raw_output, tokens_used = provider.generate(
                        prompt=prompt,
                        system_instruction=CHOICE_SYSTEM_INSTRUCTION,
                        max_tokens=384,
                    )
                except TypeError:
                    raw_output, tokens_used = provider.generate(
                        prompt=prompt,
                        system_instruction=CHOICE_SYSTEM_INSTRUCTION,
                    )
                timer_info["model"] = provider.model_name
                timer_info["tokens"] = tokens_used

            if not raw_output or not raw_output.strip():
                return DynamicChoiceSet(
                    choices=[],
                    generation_status=ChoiceGenerationStatus.FAILED,
                    generation_metadata={"error": "Provider returned empty response."},
                )

            try:
                parsed_json = _parse_json_robust(raw_output)
            except json.JSONDecodeError as exc:
                return DynamicChoiceSet(
                    choices=[],
                    generation_status=ChoiceGenerationStatus.FAILED,
                    generation_metadata={"error": f"Invalid JSON from provider: {exc}"},
                )

            # Extract list of choice dicts
            raw_choices: list[dict] = []
            if isinstance(parsed_json, dict) and "choices" in parsed_json:
                raw_choices = parsed_json["choices"]
            elif isinstance(parsed_json, list):
                raw_choices = parsed_json
            else:
                return DynamicChoiceSet(
                    choices=[],
                    generation_status=ChoiceGenerationStatus.FAILED,
                    generation_metadata={"error": "Unexpected JSON structure; expected 'choices' list."},
                )

            validated_choices: list[DynamicChoice] = []
            seen_texts: set[str] = set()

            for idx, item in enumerate(raw_choices, start=1):
                if not isinstance(item, dict):
                    continue

                # Ensure transient ID and scene binding
                cid = str(item.get("choice_id") or f"dynamic_ai_{idx}")
                text = str(item.get("choice_text") or "").strip()
                intent = str(item.get("action_intent") or "inspect").strip().lower()
                target = item.get("target")
                approach = item.get("approach")
                risk = item.get("risk_level")

                if not text:
                    continue

                # Ensure compatibility with strict schema bounds (Phi-3 descriptive outputs)
                if len(text) > 200:
                    text = text[:197].rsplit(" ", 1)[0] + "..."
                if len(intent) > 50:
                    intent = intent[:50]
                if isinstance(target, str) and len(target) > 100:
                    target = target[:100]
                if isinstance(approach, str) and len(approach) > 100:
                    approach = approach[:100]

                norm_text = text.lower()

                # Deduplication against existing choices and other generated choices
                if norm_text in seen_texts or norm_text in existing_choice_texts:
                    continue

                # Parse risk level safely
                risk_enum = ChoiceRiskLevel.LOW
                if isinstance(risk, str):
                    risk_lower = risk.strip().lower()
                    if risk_lower in ("low", "medium", "high"):
                        risk_enum = ChoiceRiskLevel(risk_lower)

                try:
                    choice_obj = DynamicChoice(
                        choice_id=cid,
                        choice_text=text,
                        action_intent=intent,
                        target=target if isinstance(target, str) else None,
                        approach=approach if isinstance(approach, str) else None,
                        risk_level=risk_enum,
                        choice_type="dynamic_ai",
                        requires_validation=True,
                        scene_id=context.current_scene.id if context.current_scene else None,
                    )
                    validated_choices.append(choice_obj)
                    seen_texts.add(norm_text)
                except ValidationError:
                    continue

                if len(validated_choices) >= max_choices:
                    break

            if not validated_choices:
                localized_fallbacks = {
                    "Japanese": (
                        "周囲の様子を注意深く観察する。",
                        "これまでの出来事を静かに振り返る。",
                    ),
                    "Hindi": (
                        "आसपास के वातावरण का ध्यानपूर्वक निरीक्षण करें।",
                        "अब तक जो हुआ है उस पर विचार करें।",
                    ),
                    "French": (
                        "Observer attentivement les environs.",
                        "Réfléchir à ce qui s'est passé jusqu'ici.",
                    ),
                }
                fb1, fb2 = localized_fallbacks.get(
                    context.story_language,
                    (
                        "Observe the surroundings carefully.",
                        "Reflect on what has happened so far.",
                    ),
                )
                fallback_choices = [
                    DynamicChoice(
                        choice_id="fallback_1",
                        choice_text=fb1,
                        action_intent="inspect",
                        target="surroundings",
                        approach="cautiously",
                        risk_level=ChoiceRiskLevel.LOW,
                        choice_type="emergent_fallback",
                        requires_validation=True,
                        scene_id=context.current_scene.id if context.current_scene else None,
                    ),
                    DynamicChoice(
                        choice_id="fallback_2",
                        choice_text=fb2,
                        action_intent="wait",
                        target=None,
                        approach="thoughtfully",
                        risk_level=ChoiceRiskLevel.LOW,
                        choice_type="emergent_fallback",
                        requires_validation=True,
                        scene_id=context.current_scene.id if context.current_scene else None,
                    ),
                ]
                return DynamicChoiceSet(
                    choices=fallback_choices,
                    generation_status=ChoiceGenerationStatus.SUCCESS,
                    generation_metadata={
                        "model_name": getattr(provider, "model_name", "unknown"),
                        "tokens_used": tokens_used,
                        "generated_count": 0,
                        "fallback": True,
                    },
                )

            combined_choice_text = " ".join(c.choice_text for c in validated_choices)
            is_lang_valid, lang_err = validate_output_language(
                combined_choice_text,
                context.story_language,
            )
            if not is_lang_valid:
                return DynamicChoiceSet(
                    choices=[],
                    generation_status=ChoiceGenerationStatus.FAILED,
                    generation_metadata={
                        "error": f"Generated choices did not match requested language '{context.story_language}': {lang_err}",
                        "requested_language": context.story_language,
                    },
                )

            status = (
                ChoiceGenerationStatus.SUCCESS
                if validated_choices
                else ChoiceGenerationStatus.FAILED
            )

            metadata = {
                "model_name": getattr(provider, "model_name", "unknown"),
                "tokens_used": tokens_used,
                "generated_count": len(validated_choices),
            }

            return DynamicChoiceSet(
                choices=validated_choices,
                generation_status=status,
                generation_metadata=metadata,
            )

        except (
            AITimeoutError,
            AIRateLimitError,
            AIEmptyResponseError,
            AIResponseValidationError,
            AIProviderError,
            AINarrativeError,
        ) as exc:
            return DynamicChoiceSet(
                choices=[],
                generation_status=ChoiceGenerationStatus.FAILED,
                generation_metadata={"error": str(exc)},
            )
        except Exception as exc:
            return DynamicChoiceSet(
                choices=[],
                generation_status=ChoiceGenerationStatus.FAILED,
                generation_metadata={"error": f"Unexpected error during choice generation: {exc}"},
            )
