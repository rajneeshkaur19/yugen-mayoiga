"""Narrative Generator for Yūgen Mayoiga (AI Phase 2).

This service receives a verified :class:`StoryAIContext`, constructs atmospheric
prompts adhering to the game's aesthetic, invokes the active LLM provider,
and parses/validates the response into a structured :class:`NarrativeGenerationResult`.

Guarantees:
- Strictly decoupled from database persistence (read/write DB operations belong elsewhere).
- Never returns hardcoded fake prose when the LLM fails; raises structured exceptions.
- Validates model output through Pydantic schemas.
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
from backend.app.ai.language_guard import language_script_directive, validate_output_language
from backend.app.ai.prompts.narrative_prompt import (
    SYSTEM_INSTRUCTION,
    build_narrative_user_prompt,
)
from backend.app.ai.providers import BaseLLMProvider, OllamaProvider, get_default_provider
from backend.app.ai.schemas import (
    NarrativeGenerationResult,
    StoryAIContext,
)


def _strip_markdown_code_fence(text: str) -> str:
    """Strip markdown codeblock wrappers (e.g. ```json ... ```) if present."""
    clean = text.strip()
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
    match = re.match(pattern, clean, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return clean


def _parse_narrative_json_robust(text: str) -> dict:
    """Parse JSON with fallback substring extraction for small local LLMs."""
    clean = _strip_markdown_code_fence(text)
    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    first_brace = clean.find("{")
    last_brace = clean.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        data = json.loads(clean[first_brace : last_brace + 1])
        if isinstance(data, dict):
            return data

    raise json.JSONDecodeError("Could not locate valid JSON object in output", clean, 0)


class NarrativeGenerator:
    """AI Narrative Generator orchestrating prompt construction and LLM generation."""

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        max_retries: int = 2,
    ) -> None:
        """Initialize the narrative generator with an optional provider override."""
        self._provider = provider
        self.max_retries = max_retries

    @property
    def provider(self) -> BaseLLMProvider:
        """Lazily resolve the provider if not injected at initialization."""
        if self._provider is None:
            self._provider = get_default_provider()
        return self._provider

    def generate_narrative(
        self,
        context: StoryAIContext,
        system_instruction_override: Optional[str] = None,
    ) -> NarrativeGenerationResult:
        """Generate an atmospheric narrative continuation based on story context.

        Parameters
        ----------
        context:
            Structured, validated StoryAIContext produced by StoryContextBuilder.
        system_instruction_override:
            Optional override for system prompt instructions.

        Returns
        -------
        NarrativeGenerationResult
            Parsed, validated narrative passage with metadata.

        Raises
        ------
        AIConfigurationError
            If no provider or API key is available.
        AITimeoutError
            If provider call times out.
        AIRateLimitError
            If provider rate limit (429) is encountered.
        AIProviderError
            If provider encounters an HTTP or network error.
        AIEmptyResponseError
            If provider returns a blank or empty narrative.
        AIResponseValidationError
            If provider response is not valid JSON or fails schema validation.
        """
        if not isinstance(context, StoryAIContext):
            raise TypeError(
                f"Expected context to be an instance of StoryAIContext, got {type(context).__name__}"
            )

        # 1. Assemble prompt
        system_inst = system_instruction_override or SYSTEM_INSTRUCTION
        user_prompt = build_narrative_user_prompt(context)

        # 2. Invoke provider with bounded token limit and latency telemetry
        provider = self.provider
        is_local = isinstance(provider, OllamaProvider)
        narrative_max_tokens = 256 if is_local else 320
        with pipeline_timer("Narrative Generation") as timer_info:
            try:
                raw_text, tokens = provider.generate(
                    prompt=user_prompt,
                    system_instruction=system_inst,
                    max_tokens=narrative_max_tokens,
                )
            except TypeError:
                raw_text, tokens = provider.generate(
                    prompt=user_prompt,
                    system_instruction=system_inst,
                )
            timer_info["model"] = provider.model_name
            timer_info["tokens"] = tokens

        # 3. Clean and parse JSON
        if not raw_text or not raw_text.strip():
            raise AIEmptyResponseError("Provider returned an empty narrative response.")

        try:
            data = _parse_narrative_json_robust(raw_text)
        except json.JSONDecodeError as exc:
            raise AIResponseValidationError(
                f"Failed to parse LLM response as JSON: {exc}. Response snippet: {raw_text[:200]!r}",
                details={"raw_response": raw_text},
            ) from exc

        if not isinstance(data, dict):
            raise AIResponseValidationError(
                f"Expected LLM response to be a JSON object, got {type(data).__name__}",
                details={"raw_response": raw_text},
            )

        # 4. Normalize fields for model compatibility (e.g. Phi-3 output variations)
        # Explicit alias: Phi-3 sometimes uses "title" instead of "scene_title"
        if "title" in data and not data.get("scene_title"):
            data["scene_title"] = data.pop("title")
        elif "title" in data:
            # title was present but scene_title already set → drop the alias only
            data.pop("title")

        # Sanitize dialogue array
        raw_dialogue = data.get("dialogue", [])
        clean_dialogue = []
        if isinstance(raw_dialogue, list):
            for d in raw_dialogue:
                if isinstance(d, dict) and "character_name" in d and "dialogue" in d:
                    clean_dialogue.append({
                        "character_name": str(d["character_name"]).strip(),
                        "dialogue": str(d["dialogue"]).strip(),
                    })
                elif isinstance(d, str) and ":" in d:
                    cname, ctext = d.split(":", 1)
                    clean_dialogue.append({
                        "character_name": cname.strip(),
                        "dialogue": ctext.strip(),
                    })
        data["dialogue"] = clean_dialogue

        # Inject telemetry if not present
        if not data.get("model_name"):
            data["model_name"] = provider.model_name
        if data.get("tokens_used") is None and tokens is not None:
            data["tokens_used"] = tokens

        # Security: reject any fields not in the declared schema.
        # This enforces the same guarantee as extra='forbid' — LLM-hallucinated
        # game-state mutations (turn_number, ending_triggered, inventory_add, etc.)
        # cannot silently flow through.
        valid_keys = set(NarrativeGenerationResult.model_fields.keys())
        unknown_keys = set(data.keys()) - valid_keys
        if unknown_keys:
            raise AIResponseValidationError(
                f"LLM response contained unexpected fields that could indicate "
                f"game-state injection: {sorted(unknown_keys)!r}. "
                f"Response snippet: {raw_text[:200]!r}",
                details={"unknown_keys": sorted(unknown_keys), "raw_response": raw_text},
            )

        # 5. Validate schema & language fidelity
        try:
            result = NarrativeGenerationResult.model_validate(data)
        except ValidationError as exc:
            raise AIResponseValidationError(
                f"Generated narrative failed schema validation: {exc}",
                details={"errors": exc.errors(), "raw_response": raw_text},
            ) from exc

        is_lang_valid, lang_err = validate_output_language(
            result.narrative_text,
            context.story_language,
        )
        if not is_lang_valid:
            # Retry once with an explicit corrective instruction before failing explicitly
            retry_prompt = (
                f"{user_prompt}\n\nCORRECTION: Your previous response failed language validation: "
                f"{lang_err} {language_script_directive(context.story_language)}"
            )
            try:
                retry_raw, retry_tokens = provider.generate(
                    prompt=retry_prompt,
                    system_instruction=system_inst,
                    max_tokens=narrative_max_tokens,
                )
            except TypeError:
                retry_raw, retry_tokens = provider.generate(
                    prompt=retry_prompt,
                    system_instruction=system_inst,
                )
            if retry_raw and retry_raw.strip():
                try:
                    retry_data = _parse_narrative_json_robust(retry_raw)
                    if "title" in retry_data and not retry_data.get("scene_title"):
                        retry_data["scene_title"] = retry_data.pop("title")
                    elif "title" in retry_data:
                        retry_data.pop("title")
                    retry_data["dialogue"] = [
                        {
                            "character_name": str(d.get("character_name", "")).strip(),
                            "dialogue": str(d.get("dialogue", "")).strip(),
                        }
                        for d in (retry_data.get("dialogue") or [])
                        if isinstance(d, dict) and "character_name" in d and "dialogue" in d
                    ]
                    if not retry_data.get("model_name"):
                        retry_data["model_name"] = provider.model_name
                    if retry_data.get("tokens_used") is None and retry_tokens is not None:
                        retry_data["tokens_used"] = retry_tokens
                    if not (set(retry_data.keys()) - valid_keys):
                        retry_result = NarrativeGenerationResult.model_validate(retry_data)
                        retry_valid, _ = validate_output_language(
                            retry_result.narrative_text,
                            context.story_language,
                        )
                        if retry_valid:
                            return retry_result
                except Exception:
                    pass

            raise AIResponseValidationError(
                f"Generated narrative did not match requested language '{context.story_language}': {lang_err}",
                details={"requested_language": context.story_language, "raw_response": raw_text},
            )

        return result
