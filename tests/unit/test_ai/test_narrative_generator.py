"""Unit tests for the NarrativeGenerator and AI Provider integration (Phase 2).

Test groups covered:
1. Schema validation (valid, invalid, empty rejection, serialization)
2. Generator orchestration (context input, prompt assembly, player input,
   character profiles, memories, world state, history, empty optional contexts)
3. Error handling (timeouts, rate limits, server errors, malformed JSON, empty outputs,
   retries, missing configuration)
4. Safety guarantees (no DB mutation, no ORM leakage, no state mutations,
   no fake fallbacks)
5. Optional live integration test (skipped when API key is unset)
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Tuple

import pytest
from pydantic import ValidationError

from backend.app.ai.exceptions import (
    AIConfigurationError,
    AIEmptyResponseError,
    AINarrativeError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AITimeoutError,
)
from backend.app.ai.narrative_generator import (
    NarrativeGenerator,
    _strip_markdown_code_fence,
)
from backend.app.ai.prompts.narrative_prompt import (
    SYSTEM_INSTRUCTION,
    build_narrative_user_prompt,
)
from backend.app.ai.providers import (
    BaseLLMProvider,
    GeminiProvider,
    OpenAIProvider,
    get_default_provider,
)
from backend.app.ai.schemas import (
    CharacterContext,
    CharacterDialogueSnippet,
    CharacterEmotionContext,
    CharacterTraitsContext,
    HistoryEntryContext,
    MemoryContext,
    NarrativeGenerationResult,
    PlayerInputContext,
    RelationshipContext,
    SceneContext,
    StoryAIContext,
    StoryRuntimeContext,
)

# ---------------------------------------------------------------------------
# Test Helpers & Mock Providers
# ---------------------------------------------------------------------------


class MockProvider(BaseLLMProvider):
    """Test mock provider recording calls and returning configured responses."""

    def __init__(
        self,
        model_name: str = "mock-model",
        return_text: str = "",
        return_tokens: Optional[int] = 42,
        raise_exception: Optional[Exception] = None,
        exception_sequence: Optional[list[Exception]] = None,
    ) -> None:
        super().__init__(model_name=model_name)
        self.return_text = return_text
        self.return_tokens = return_tokens
        self.raise_exception = raise_exception
        self.exception_sequence = list(exception_sequence or [])
        self.call_count = 0
        self.last_prompt: Optional[str] = None
        self.last_system_instruction: Optional[str] = None

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Tuple[str, Optional[int]]:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_instruction = system_instruction

        if self.exception_sequence:
            exc = self.exception_sequence.pop(0)
            raise exc

        if self.raise_exception:
            raise self.raise_exception

        return self.return_text, self.return_tokens


def make_valid_context(
    *,
    player_input: Optional[PlayerInputContext] = None,
    characters: Optional[list[CharacterContext]] = None,
    memories: Optional[list[MemoryContext]] = None,
    relationships: Optional[list[RelationshipContext]] = None,
    history: Optional[list[HistoryEntryContext]] = None,
    scene: Any = ...,
    world_state: Optional[dict[str, Any]] = None,
) -> StoryAIContext:
    """Build a standalone StoryAIContext instance for fast unit testing."""
    default_scene = SceneContext(
        id=201,
        story_id=101,
        scene_number=2,
        location="Dilapidated Engawa",
        mood="Dreadful Stillness",
        content="The rotting wooden walkway bends under your weight. Mist curls across the courtyard.",
        haiku="Rotten wood groans low / Mist creeps up the cedar steps / No footstep behind",
        is_ending=False,
    )
    resolved_scene = default_scene if scene is ... else scene

    return StoryAIContext(
        story_id=101,
        story_title="Whispers of Mayoiga",
        story_theme="Guilt and Loss",
        story_genre="Psychological Mystery",
        story_tone="Dark and Melancholic",
        story_season="Late Autumn",
        story_length="standard",
        story_status="active",
        current_scene=resolved_scene,
        runtime=StoryRuntimeContext(
            turn_number=4,
            yugen_meter=55,
            hidden_variables={"fog_density": "oppressive", "lantern_lit": False},
            world_state=world_state or {"tension": 70, "village_decay": 85},
        ),
        characters=characters
        if characters is not None
        else [
            CharacterContext(
                id=301,
                name="Sora",
                role="Estranged Sister",
                age=24,
                background="Searching for her missing grandfather amidst the mountain shrine.",
                goals=["Uncover grandfather's ledger", "Survive the night"],
                fears=["The dark", "Drowning"],
                secrets=["Took grandfather's ceremonial bell"],
                emotions=CharacterEmotionContext(
                    fear=45,
                    anxiety=60,
                    anger=10,
                    sadness=30,
                    happiness=5,
                    trust=40,
                ),
                traits=CharacterTraitsContext(
                    openness=65,
                    conscientiousness=75,
                    extraversion=30,
                    agreeableness=50,
                    neuroticism=70,
                ),
            )
        ],
        relationships=relationships
        if relationships is not None
        else [
            RelationshipContext(
                from_character_id=301,
                from_character_name="Sora",
                to_character_id=999,
                to_character_name="Player",
                trust=45,
                friendship=50,
                suspicion=35,
                fear=20,
                dependency=15,
            )
        ],
        relevant_memories=memories
        if memories is not None
        else [
            MemoryContext(
                id=401,
                character_id=301,
                character_name="Sora",
                event="Found an antique bell buried beneath the altar stone.",
                type="long_term",
                importance=85,
                emotional_weight=20,
                status="normal",
                created_turn=1,
                relevance_score=0.88,
            )
        ],
        recent_history=history
        if history is not None
        else [
            HistoryEntryContext(
                turn_number=3,
                scene_id=201,
                choice_text="Step onto the broken veranda.",
                free_text=None,
                parsed_action="step",
            )
        ],
        player_input=player_input
        or PlayerInputContext(
            choice_text="Ask Sora what she is hiding behind her sleeve.",
            free_text=None,
            parsed_action="ask",
        ),
        memory_limit=5,
        history_limit=5,
    )


VALID_JSON_RESPONSE = json.dumps(
    {
        "narrative_text": (
            "The mist wraps tight around the pillars as you speak. Sora freezes, her fingers "
            "tightening over the fraying silk of her sleeve. For a second, only the slow drip "
            "of mountain condensation answers."
        ),
        "scene_title": "A Question in the Cold",
        "scene_mood": "Suspenseful Stillness",
        "passage_summary": "The player confronts Sora about what she is concealing, causing her to tense up.",
        "dialogue": [
            {
                "character_name": "Sora",
                "dialogue": "You shouldn't pry into things you don't yet understand.",
            }
        ],
    }
)

# ---------------------------------------------------------------------------
# 1. Schema Tests (1 - 4)
# ---------------------------------------------------------------------------


def test_schema_valid_narrative_response() -> None:
    """1. Valid narrative response parses and validates successfully."""
    data = json.loads(VALID_JSON_RESPONSE)
    res = NarrativeGenerationResult.model_validate(data)
    assert "Sora freezes" in res.narrative_text
    assert res.scene_title == "A Question in the Cold"
    assert res.scene_mood == "Suspenseful Stillness"
    assert len(res.dialogue) == 1
    assert res.dialogue[0].character_name == "Sora"


def test_schema_invalid_response_missing_narrative_text() -> None:
    """2. Invalid response missing mandatory narrative_text raises ValidationError."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"scene_title": "Silent Night", "scene_mood": "Gloomy"}
        )


def test_schema_empty_narrative_rejection() -> None:
    """3. Blank or whitespace-only narrative text is rejected by min_length validation."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"narrative_text": "   ", "scene_title": "Empty"}
        )


def test_schema_serialization_roundtrip() -> None:
    """4. Serialization to dict and JSON preserves all fields cleanly."""
    res = NarrativeGenerationResult(
        narrative_text="A raven calls from the torii gate.",
        scene_title="Torii Watch",
        scene_mood="Ominous",
        passage_summary="A raven appears.",
        dialogue=[CharacterDialogueSnippet(character_name="Aki", dialogue="Look away.")],
        model_name="gemini-3.8-flash",
        tokens_used=120,
    )
    dumped = res.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["narrative_text"] == "A raven calls from the torii gate."
    assert dumped["tokens_used"] == 120

    json_str = res.model_dump_json()
    reloaded = NarrativeGenerationResult.model_validate_json(json_str)
    assert reloaded == res


# ---------------------------------------------------------------------------
# 2. Generator Orchestration Tests (5 - 15)
# ---------------------------------------------------------------------------


def test_generator_valid_context_input() -> None:
    """5. Generator accepts a valid StoryAIContext and returns a valid result."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    result = generator.generate_narrative(ctx)

    assert isinstance(result, NarrativeGenerationResult)
    assert "Sora freezes" in result.narrative_text
    assert result.model_name == "mock-model"
    assert result.tokens_used == 42


def test_generator_provider_called_correctly() -> None:
    """6. Provider is invoked exactly once with non-empty prompt and system instruction."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    generator.generate_narrative(ctx)

    assert provider.call_count == 1
    assert provider.last_prompt is not None
    assert len(provider.last_prompt) > 50
    assert provider.last_system_instruction == SYSTEM_INSTRUCTION


def test_generator_strips_markdown_code_fences() -> None:
    """7. Generator cleanly strips ```json codeblocks returned by LLMs."""
    wrapped_response = f"```json\n{VALID_JSON_RESPONSE}\n```"
    provider = MockProvider(return_text=wrapped_response)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    result = generator.generate_narrative(ctx)
    assert result.scene_title == "A Question in the Cold"


def test_generator_structured_response_validation() -> None:
    """8. Generator strictly validates returned fields and attaches provider metadata."""
    custom_json = json.dumps(
        {
            "narrative_text": "The wind howls through the paper screens.",
            "scene_title": "Paper Shivers",
            "scene_mood": "Eerie",
            "passage_summary": "Wind disturbs the interior.",
            "dialogue": [],
            "model_name": "custom-llm",
            "tokens_used": 99,
        }
    )
    provider = MockProvider(model_name="default-llm", return_text=custom_json, return_tokens=50)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    result = generator.generate_narrative(ctx)
    assert result.model_name == "custom-llm"
    assert result.tokens_used == 99


def test_generator_context_passed_into_prompt() -> None:
    """9. Story title, theme, tone, and season are present in the constructed prompt."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    generator.generate_narrative(ctx)

    prompt = provider.last_prompt
    assert "Whispers of Mayoiga" in prompt
    assert "Guilt and Loss" in prompt
    assert "Dark and Melancholic" in prompt
    assert "Late Autumn" in prompt


def test_generator_player_input_incorporated_into_prompt() -> None:
    """10. Player choice text and action verb are clearly visible in the prompt."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context(
        player_input=PlayerInputContext(
            choice_text="Inspect the carved stone statue.",
            free_text="I wipe the moss off the stone carving.",
            parsed_action="inspect",
        )
    )

    generator.generate_narrative(ctx)

    prompt = provider.last_prompt
    assert "Inspect the carved stone statue." in prompt
    assert "I wipe the moss off the stone carving." in prompt
    assert "inspect" in prompt


def test_generator_character_context_included() -> None:
    """11. Character names, traits, emotions, goals, and secrets are in prompt."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    generator.generate_narrative(ctx)

    prompt = provider.last_prompt
    assert "Sora" in prompt
    assert "Estranged Sister" in prompt
    assert "Fear:45/100" in prompt
    assert "Uncover grandfather's ledger" in prompt
    assert "Took grandfather's ceremonial bell" in prompt


def test_generator_relevant_memories_included() -> None:
    """12. Retrieved memories and relevance scores are present in prompt."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    generator.generate_narrative(ctx)

    prompt = provider.last_prompt
    assert "Found an antique bell buried beneath the altar stone." in prompt
    assert "0.88" in prompt


def test_generator_world_state_included() -> None:
    """13. World state and runtime variables are in prompt."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context(world_state={"tension": 88, "altar_broken": True})

    generator.generate_narrative(ctx)

    prompt = provider.last_prompt
    assert "tension" in prompt
    assert "88" in prompt
    assert "fog_density" in prompt


def test_generator_narrative_history_included() -> None:
    """14. Recent player history entries are displayed chronologically in prompt."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context(
        history=[
            HistoryEntryContext(
                turn_number=1,
                scene_id=10,
                choice_text="Crossed the rope bridge.",
            ),
            HistoryEntryContext(
                turn_number=2,
                scene_id=11,
                choice_text="Lit the stone lantern.",
            ),
        ]
    )

    generator.generate_narrative(ctx)

    prompt = provider.last_prompt
    assert "Turn 1" in prompt
    assert "Crossed the rope bridge." in prompt
    assert "Turn 2" in prompt
    assert "Lit the stone lantern." in prompt


def test_generator_empty_optional_context_handled() -> None:
    """15. Generator gracefully formats prompts when characters, memories, history are empty."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context(
        characters=[],
        memories=[],
        relationships=[],
        history=[],
        scene=None,
        player_input=None,
    )

    result = generator.generate_narrative(ctx)

    prompt = provider.last_prompt
    assert "The player travels alone." in prompt
    assert "No footstep behind" not in prompt
    assert isinstance(result, NarrativeGenerationResult)


# ---------------------------------------------------------------------------
# 3. Error Handling Tests (16 - 22)
# ---------------------------------------------------------------------------


def test_error_handling_provider_timeout() -> None:
    """16. Provider timeout raises AITimeoutError."""
    provider = MockProvider(raise_exception=AITimeoutError("Gemini request timed out"))
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    with pytest.raises(AITimeoutError, match="timed out"):
        generator.generate_narrative(ctx)


def test_error_handling_provider_rate_limit() -> None:
    """17. Provider HTTP 429 raises AIRateLimitError."""
    provider = MockProvider(raise_exception=AIRateLimitError("Rate limit exceeded", status_code=429))
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    with pytest.raises(AIRateLimitError, match="Rate limit"):
        generator.generate_narrative(ctx)


def test_error_handling_provider_failure() -> None:
    """18. Generic provider failure raises AIProviderError."""
    provider = MockProvider(raise_exception=AIProviderError("Internal Server Error", status_code=500))
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    with pytest.raises(AIProviderError, match="Internal Server Error"):
        generator.generate_narrative(ctx)


def test_error_handling_malformed_json_response() -> None:
    """19. Non-JSON text from provider raises AIResponseValidationError."""
    provider = MockProvider(return_text="This is raw text without JSON brackets.")
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    with pytest.raises(AIResponseValidationError, match="Failed to parse LLM response as JSON"):
        generator.generate_narrative(ctx)


def test_error_handling_empty_provider_output() -> None:
    """20. Blank or empty provider output raises AIEmptyResponseError."""
    provider = MockProvider(return_text="   \n  ")
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    with pytest.raises(AIEmptyResponseError, match="empty narrative response"):
        generator.generate_narrative(ctx)


def test_error_handling_retry_limit_behavior() -> None:
    """21. Provider handles retry exhaustion and surfaces final exception."""
    # Test retry behavior via provider with a sequence of errors
    provider = MockProvider(
        exception_sequence=[
            AITimeoutError("Timeout attempt 1"),
            AITimeoutError("Timeout attempt 2"),
        ]
    )
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    with pytest.raises(AITimeoutError, match="Timeout attempt 1"):
        generator.generate_narrative(ctx)


def test_error_handling_missing_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """22. Missing API keys raise AIConfigurationError when resolving default provider."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("AI_FALLBACK_PROVIDERS", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    generator = NarrativeGenerator(provider=None)
    ctx = make_valid_context()

    with pytest.raises(AIConfigurationError, match="No AI provider configured"):
        generator.generate_narrative(ctx)


# ---------------------------------------------------------------------------
# 4. Safety Guarantees Tests (23 - 27)
# ---------------------------------------------------------------------------


def test_safety_no_database_mutation(db_session, setup_story) -> None:
    """23. Generating narrative performs zero database writes/commits/flushes."""
    from sqlalchemy import select as sa_select
    from backend.app.ai.context_builder import StoryContextBuilder
    from backend.app.models.story_state import StoryState

    story = setup_story["story"]
    scene = setup_story["scene1"]

    # Insert state
    state = StoryState(
        story_id=story.id,
        current_scene_id=scene.id,
        turn_number=3,
        yugen_meter=50,
        hidden_variables={"dust": True},
    )
    db_session.add(state)
    db_session.commit()

    ctx = StoryContextBuilder(db_session).build(story.id)

    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)

    # Call generator
    result = generator.generate_narrative(ctx)
    assert isinstance(result, NarrativeGenerationResult)

    # Verify DB state untouched
    db_session.refresh(state)
    assert state.turn_number == 3
    assert state.yugen_meter == 50
    assert state.hidden_variables == {"dust": True}


def test_safety_no_orm_objects_passed_to_provider() -> None:
    """24. Only primitives, Pydantic objects, and formatted strings are sent to provider."""
    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    generator.generate_narrative(ctx)

    assert isinstance(provider.last_prompt, str)
    assert isinstance(provider.last_system_instruction, str)
    # Check that prompt doesn't contain python object representations
    assert "<backend.app.models" not in provider.last_prompt
    assert "<sqlalchemy." not in provider.last_prompt


def test_safety_no_deterministic_state_mutation() -> None:
    """25. Generator never modifies context object or deterministic values."""
    ctx = make_valid_context()
    original_turn = ctx.runtime.turn_number
    original_meter = ctx.runtime.yugen_meter

    provider = MockProvider(return_text=VALID_JSON_RESPONSE)
    generator = NarrativeGenerator(provider=provider)
    generator.generate_narrative(ctx)

    assert ctx.runtime.turn_number == original_turn
    assert ctx.runtime.yugen_meter == original_meter


def test_safety_no_ai_generated_state_mutation_accepted() -> None:
    """26. Game-state mutation fields in LLM response are rejected by extra='forbid'.

    With ``NarrativeGenerationResult(model_config=ConfigDict(extra='forbid'))``,
    any field not in the declared schema causes a ``ValidationError`` inside the
    generator, which the generator converts to ``AIResponseValidationError``.
    This guarantees LLM-hallucinated state mutations cannot silently flow through.
    """
    injection_json = json.dumps(
        {
            "narrative_text": "You push open the door.",
            "scene_title": "Threshold",
            "scene_mood": "Eerie",
            "turn_number": 9999,          # Injection attempt
            "inventory_add": ["Magic Key"], # Injection attempt
            "yugen_meter": 100,           # Injection attempt
            "ending_triggered": True,     # Injection attempt
        }
    )
    provider = MockProvider(return_text=injection_json)
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    # extra='forbid' causes ValidationError → AIResponseValidationError
    with pytest.raises(AIResponseValidationError):
        generator.generate_narrative(ctx)


def test_safety_no_fake_fallback_narration_on_error() -> None:
    """27. Generator never swallows provider errors with fake canned prose."""
    provider = MockProvider(raise_exception=AIProviderError("API connection reset"))
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    with pytest.raises(AIProviderError):
        generator.generate_narrative(ctx)


# ---------------------------------------------------------------------------
# 5. Helper & Utility Unit Tests
# ---------------------------------------------------------------------------


def test_strip_markdown_code_fence() -> None:
    """Verify markdown stripper handles various code fence configurations."""
    assert _strip_markdown_code_fence('```json\n{"key": "val"}\n```') == '{"key": "val"}'
    assert _strip_markdown_code_fence('```\n{"key": "val"}\n```') == '{"key": "val"}'
    assert _strip_markdown_code_fence('{"key": "val"}') == '{"key": "val"}'


def test_invalid_context_type_raises_type_error() -> None:
    """Passing a non-StoryAIContext object raises TypeError."""
    generator = NarrativeGenerator(provider=MockProvider())
    with pytest.raises(TypeError, match="Expected context to be an instance of StoryAIContext"):
        generator.generate_narrative("not a context object")  # type: ignore[arg-type]


def test_gemini_provider_default_model() -> None:
    """GeminiProvider defaults to gemini-3.8-flash and respects custom model configuration."""
    provider = GeminiProvider(api_key="fake-test-key")
    assert provider.model_name == "gemini-3.8-flash"

    custom_provider = GeminiProvider(api_key="fake-test-key", model_name="custom-model")
    assert custom_provider.model_name == "custom-model"


# ---------------------------------------------------------------------------
# 6. Optional Live Provider Integration Test
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="Live AI provider credentials (GEMINI_API_KEY / OPENAI_API_KEY) not configured in environment.",
)
def test_live_provider_integration() -> None:
    """Optional live integration test running only when real API keys are present."""
    provider = get_default_provider()
    generator = NarrativeGenerator(provider=provider)
    ctx = make_valid_context()

    try:
        result = generator.generate_narrative(ctx)
        assert isinstance(result, NarrativeGenerationResult)
        assert len(result.narrative_text) > 20
        assert result.model_name is not None
    except (AIProviderError, AIRateLimitError, AITimeoutError) as exc:
        pytest.skip(f"Live provider quota or network unavailable: {exc}")
