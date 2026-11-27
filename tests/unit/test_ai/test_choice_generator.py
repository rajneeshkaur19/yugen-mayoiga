"""Unit tests for the DynamicChoiceGenerator and choice schemas (Phase 4).

Test coverage includes:
1. Schema validation (valid, extra fields forbidden, constraints)
2. Generator orchestration (context input, scene, characters, world state, memories, history)
3. Deterministic choice coexistence (deduplication, non-interference)
4. Choice limits and deduplication
5. Error handling (malformed JSON, empty response, timeouts, provider failures, missing config)
6. Safety guarantees (no DB access, read-only, no state mutations)
"""

from __future__ import annotations

import json
from typing import Any, Optional, Tuple

import pytest
from pydantic import ValidationError

from backend.app.ai.choice_generator import DynamicChoiceGenerator
from backend.app.ai.exceptions import (
    AIConfigurationError,
    AIEmptyResponseError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from backend.app.ai.providers import BaseLLMProvider
from backend.app.ai.schemas import (
    CharacterContext,
    CharacterEmotionContext,
    CharacterTraitsContext,
    ChoiceGenerationStatus,
    ChoiceRiskLevel,
    DynamicChoice,
    DynamicChoiceSet,
    HistoryEntryContext,
    MemoryContext,
    PlayerInputContext,
    RelationshipContext,
    SceneContext,
    StoryAIContext,
    StoryRuntimeContext,
)


# ---------------------------------------------------------------------------
# Test Helpers & Mock Provider
# ---------------------------------------------------------------------------


class MockChoiceProvider(BaseLLMProvider):
    """Test mock provider recording calls and returning configured responses."""

    def __init__(
        self,
        model_name: str = "mock-choice-model",
        return_text: str = "",
        return_tokens: Optional[int] = 50,
        raise_exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(model_name=model_name)
        self.return_text = return_text
        self.return_tokens = return_tokens
        self.raise_exception = raise_exception
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Tuple[str, Optional[int]]:
        self.calls.append({"prompt": prompt, "system_instruction": system_instruction})
        if self.raise_exception:
            raise self.raise_exception
        return self.return_text, self.return_tokens


def _build_sample_context(
    characters: Optional[list[CharacterContext]] = None,
    memories: Optional[list[MemoryContext]] = None,
    world_state: Optional[dict[str, Any]] = None,
) -> StoryAIContext:
    """Build a standalone StoryAIContext instance for isolated unit tests."""
    scene = SceneContext(
        id=101,
        story_id=1,
        scene_number=1,
        location="Silent Station Platform",
        mood="Eerie Solitude",
        content="Rust flakes from the iron overhang. The station timetable displays no arrivals.",
        haiku="No train arrives here / Weeds push through the rusted track / Cold fog takes the light",
        is_ending=False,
    )

    return StoryAIContext(
        story_id=1,
        story_title="The Forgotten Rail",
        story_theme="Abandonment",
        story_genre="Mystery",
        story_tone="Subdued and Eerie",
        story_season="Autumn",
        story_length="short",
        story_status="in_progress",
        current_scene=scene,
        runtime=StoryRuntimeContext(
            turn_number=2,
            yugen_meter=40,
            hidden_variables={"station_bell": "cracked"},
            world_state=world_state or {"fog_level": "heavy", "station_door": "locked"},
        ),
        characters=characters
        if characters is not None
        else [
            CharacterContext(
                id=1,
                name="Aki",
                role="Traveling Companion",
                age=20,
                background="Carries an antique silver compass.",
                goals=["Reach the mountain village"],
                fears=["Echoes in the fog"],
                secrets=["Lost her ticket"],
                emotions=CharacterEmotionContext(
                    fear=35, anxiety=50, anger=5, sadness=20, happiness=10, trust=65
                ),
                traits=CharacterTraitsContext(
                    openness=60, conscientiousness=70, extraversion=40, agreeableness=65, neuroticism=55
                ),
            )
        ],
        relationships=[
            RelationshipContext(
                from_character_id=1,
                from_character_name="Aki",
                to_character_id=999,
                to_character_name="Player",
                trust=65,
                friendship=55,
                suspicion=20,
                fear=10,
                dependency=30,
            )
        ],
        relevant_memories=memories
        if memories is not None
        else [
            MemoryContext(
                id=10,
                character_id=1,
                character_name="Aki",
                event="Found an old brass key stamped with the number 4.",
                type="player_choice",
                importance=80,
                emotional_weight=20,
                status="normal",
                created_turn=1,
                relevance_score=0.9,
            )
        ],
        recent_history=[
            HistoryEntryContext(
                turn_number=1,
                scene_id=101,
                choice_text="Step onto the rain-slick platform",
                parsed_action="step",
            )
        ],
        player_input=PlayerInputContext(choice_text="Step onto the platform"),
    )


SAMPLE_VALID_CHOICES_JSON = json.dumps(
    {
        "choices": [
            {
                "choice_id": "dynamic_ai_1",
                "choice_text": "Inspect the station master's frosted window for movement.",
                "action_intent": "inspect",
                "target": "frosted window",
                "approach": "stealthily",
                "risk_level": "low",
            },
            {
                "choice_id": "dynamic_ai_2",
                "choice_text": "Ask Aki if she recognizes the symbol carved on the bench.",
                "action_intent": "speak",
                "target": "carved bench",
                "approach": "quietly",
                "risk_level": "low",
            },
        ]
    }
)


# ---------------------------------------------------------------------------
# 1. Schema Tests
# ---------------------------------------------------------------------------


def test_schema_valid_dynamic_choice():
    """Verify that a valid DynamicChoice instantiates correctly."""
    choice = DynamicChoice(
        choice_id="dynamic_ai_1",
        choice_text="Examine the rusted timetable board.",
        action_intent="inspect",
        target="timetable board",
        approach="carefully",
        risk_level=ChoiceRiskLevel.LOW,
        choice_type="dynamic_ai",
        requires_validation=True,
        scene_id=101,
    )
    assert choice.choice_id == "dynamic_ai_1"
    assert choice.choice_type == "dynamic_ai"
    assert choice.requires_validation is True
    assert choice.scene_id == 101


def test_schema_dynamic_choice_extra_fields_forbidden():
    """Verify extra injected fields on DynamicChoice are rejected."""
    with pytest.raises(ValidationError):
        DynamicChoice(
            choice_id="dynamic_ai_1",
            choice_text="Inspect the lock.",
            action_intent="inspect",
            state_mutations={"yugen_meter": 0},  # Forbidden extra field
        )


def test_schema_dynamic_choice_set_extra_fields_forbidden():
    """Verify extra fields on DynamicChoiceSet are rejected."""
    with pytest.raises(ValidationError):
        DynamicChoiceSet(
            choices=[],
            generation_status=ChoiceGenerationStatus.SUCCESS,
            unauthorized_field="malicious",
        )


# ---------------------------------------------------------------------------
# 2. Generator Orchestration & Prompt Building Tests
# ---------------------------------------------------------------------------


def test_valid_choice_generation():
    """Verify valid dynamic choice generation returns success and valid choices."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(context=context, max_choices=3)

    assert result.generation_status == ChoiceGenerationStatus.SUCCESS
    assert len(result.choices) == 2
    assert result.choices[0].choice_id == "dynamic_ai_1"
    assert result.choices[0].choice_type == "dynamic_ai"
    assert result.choices[0].requires_validation is True
    assert result.choices[0].scene_id == 101
    assert "frosted window" in result.choices[0].choice_text


def test_context_passed_to_provider():
    """Verify provider receives prompt and system instructions."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    generator.generate_choices(context=context)

    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["system_instruction"] is not None
    assert "Yūgen Mayoiga" in call["system_instruction"]


def test_current_scene_included():
    """Verify current scene location and mood are in the prompt."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    generator.generate_choices(context=context)

    prompt = provider.calls[0]["prompt"]
    assert "Silent Station Platform" in prompt
    assert "Eerie Solitude" in prompt
    assert "Rust flakes from the iron overhang" in prompt


def test_character_context_included():
    """Verify character name, role, and emotion metrics are included in the prompt."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    generator.generate_choices(context=context)

    prompt = provider.calls[0]["prompt"]
    assert "Aki" in prompt
    assert "Traveling Companion" in prompt
    assert "Fear=35" in prompt
    assert "Trust=65" in prompt


def test_world_state_included():
    """Verify world state variables are included in the prompt."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context(world_state={"fog_level": "heavy", "station_door": "locked"})

    generator.generate_choices(context=context)

    prompt = provider.calls[0]["prompt"]
    assert "fog_level: heavy" in prompt
    assert "station_door: locked" in prompt


def test_relevant_memories_included():
    """Verify relevant memories are formatted into the prompt."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    generator.generate_choices(context=context)

    prompt = provider.calls[0]["prompt"]
    assert "Found an old brass key" in prompt


def test_existing_deterministic_choices_handled():
    """Verify existing deterministic choices are included in prompt as non-duplication constraints."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    generator.generate_choices(
        context=context,
        existing_choices=["Walk toward the waiting room", "Light the rusted lantern"],
    )

    prompt = provider.calls[0]["prompt"]
    assert "Walk toward the waiting room" in prompt
    assert "Light the rusted lantern" in prompt


def test_duplicate_choices_deduplicated():
    """Verify generated choices that duplicate existing choices or each other are filtered out."""
    duplicate_payload = json.dumps(
        {
            "choices": [
                {
                    "choice_id": "c1",
                    "choice_text": "Walk toward the waiting room",  # Clashes with existing choice
                    "action_intent": "move",
                },
                {
                    "choice_id": "c2",
                    "choice_text": "Examine the lantern.",
                    "action_intent": "inspect",
                },
                {
                    "choice_id": "c3",
                    "choice_text": "examine the lantern.",  # Duplicate of c2 (case-insensitive)
                    "action_intent": "inspect",
                },
                {
                    "choice_id": "c4",
                    "choice_text": "Listen to the tracks.",
                    "action_intent": "wait",
                },
            ]
        }
    )
    provider = MockChoiceProvider(return_text=duplicate_payload)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(
        context=context,
        existing_choices=["Walk toward the waiting room"],
    )

    assert result.generation_status == ChoiceGenerationStatus.SUCCESS
    assert len(result.choices) == 2
    assert result.choices[0].choice_text == "Examine the lantern."
    assert result.choices[1].choice_text == "Listen to the tracks."


def test_choice_limits_enforced():
    """Verify max_choices limits the returned choices count."""
    payload = json.dumps(
        {
            "choices": [
                {"choice_id": f"c_{i}", "choice_text": f"Choice number {i}", "action_intent": "inspect"}
                for i in range(1, 6)
            ]
        }
    )
    provider = MockChoiceProvider(return_text=payload)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(context=context, max_choices=2)

    assert len(result.choices) == 2


# ---------------------------------------------------------------------------
# 3. Error Handling Tests
# ---------------------------------------------------------------------------


def test_invalid_json_handled():
    """Verify malformed JSON from provider returns failed status with error metadata."""
    provider = MockChoiceProvider(return_text="This is plain text, not JSON.")
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(context=context)

    assert result.generation_status == ChoiceGenerationStatus.FAILED
    assert result.choices == []
    assert "Invalid JSON" in result.generation_metadata["error"]


def test_empty_response_handled():
    """Verify empty provider response is caught and reported safely."""
    provider = MockChoiceProvider(return_text="   ")
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(context=context)

    assert result.generation_status == ChoiceGenerationStatus.FAILED
    assert result.choices == []
    assert "empty response" in result.generation_metadata["error"]


def test_provider_failure_handled():
    """Verify provider exception returns failed status without unhandled crashes."""
    provider = MockChoiceProvider(raise_exception=AIProviderError("HTTP 500 error"))
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(context=context)

    assert result.generation_status == ChoiceGenerationStatus.FAILED
    assert result.choices == []
    assert "HTTP 500 error" in result.generation_metadata["error"]


def test_provider_timeout_handled():
    """Verify provider timeout is caught gracefully."""
    provider = MockChoiceProvider(raise_exception=AITimeoutError("Request timed out"))
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(context=context)

    assert result.generation_status == ChoiceGenerationStatus.FAILED
    assert "timed out" in result.generation_metadata["error"]


def test_missing_api_configuration_handled(monkeypatch):
    """Verify missing API credentials return unavailable status."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("AI_FALLBACK_PROVIDERS", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    generator = DynamicChoiceGenerator(provider=None)
    context = _build_sample_context()

    result = generator.generate_choices(context=context)

    assert result.generation_status == ChoiceGenerationStatus.UNAVAILABLE
    assert result.choices == []
    assert "No AI provider configured" in result.generation_metadata["error"]


# ---------------------------------------------------------------------------
# 4. Safety & Non-Mutation Guarantees
# ---------------------------------------------------------------------------


def test_no_database_mutation():
    """Verify DynamicChoiceGenerator does not accept or interact with database sessions."""
    generator = DynamicChoiceGenerator(provider=MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON))
    assert not hasattr(generator, "db")
    assert not hasattr(generator, "session")


def test_no_deterministic_state_mutation():
    """Verify that generating choices does not alter the StoryAIContext."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    turn_before = context.runtime.turn_number
    yugen_before = context.runtime.yugen_meter

    generator.generate_choices(context=context)

    assert context.runtime.turn_number == turn_before
    assert context.runtime.yugen_meter == yugen_before


def test_choices_marked_as_dynamic_ai():
    """Verify generated choices always have choice_type='dynamic_ai' and requires_validation=True."""
    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    result = generator.generate_choices(context=context)

    for choice in result.choices:
        assert choice.choice_type == "dynamic_ai"
        assert choice.requires_validation is True


def test_existing_deterministic_choices_preserved():
    """Verify existing deterministic choices list is untouched by generator."""
    existing = ["Choice A", "Choice B"]
    existing_copy = list(existing)

    provider = MockChoiceProvider(return_text=SAMPLE_VALID_CHOICES_JSON)
    generator = DynamicChoiceGenerator(provider=provider)
    context = _build_sample_context()

    generator.generate_choices(context=context, existing_choices=existing)

    assert existing == existing_copy
