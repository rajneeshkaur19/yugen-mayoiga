"""Unit tests for the AI Consistency Checker and Phase 2 schema hardening (Phase 3).

Test groups:
1.  Schema — ConsistencyIssue and ConsistencyReport (1-6)
2.  Deterministic checks (7-14)
3.  AI semantic evaluation (15-20)
4.  Fail-safe behavior (21-26)
5.  Safety guarantees (27-32)
6.  Phase 2 schema hardening audit
7.  Optional live integration test
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Tuple

import pytest
from pydantic import ValidationError

from backend.app.ai.consistency_checker import (
    ConsistencyChecker,
    _parse_ai_issues,
    run_deterministic_checks,
)
from backend.app.ai.exceptions import (
    AIConfigurationError,
    AIEmptyResponseError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AITimeoutError,
)
from backend.app.ai.narrative_generator import NarrativeGenerator
from backend.app.ai.providers import BaseLLMProvider, get_default_provider
from backend.app.ai.schemas import (
    CharacterContext,
    CharacterDialogueSnippet,
    CharacterEmotionContext,
    CharacterTraitsContext,
    CheckStatus,
    ConsistencyIssue,
    ConsistencyReport,
    HistoryEntryContext,
    IssueCategory,
    IssueSeverity,
    MemoryContext,
    NarrativeGenerationResult,
    PlayerInputContext,
    RelationshipContext,
    SceneContext,
    StoryAIContext,
    StoryRuntimeContext,
)

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


class MockProvider(BaseLLMProvider):
    """Recordable mock LLM provider for unit tests."""

    def __init__(
        self,
        model_name: str = "mock-model",
        return_text: str = "",
        return_tokens: Optional[int] = None,
        raise_exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(model_name=model_name)
        self.return_text = return_text
        self.return_tokens = return_tokens
        self.raise_exception = raise_exception
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
        if self.raise_exception:
            raise self.raise_exception
        return self.return_text, self.return_tokens


def _make_narrative(text: str = "The mist thickens around the engawa.", **kwargs: Any) -> NarrativeGenerationResult:
    return NarrativeGenerationResult(narrative_text=text, **kwargs)


def _make_context(
    *,
    world_state: Optional[dict] = None,
    hidden_variables: Optional[dict] = None,
    characters: Optional[list] = None,
    scene_location: str = "Dilapidated Engawa",
    scene_mood: str = "Foreboding",
    is_ending: bool = False,
    turn_number: int = 3,
    yugen_meter: int = 50,
    memories: Optional[list] = None,
    history: Optional[list] = None,
    player_input: Optional[PlayerInputContext] = None,
) -> StoryAIContext:
    return StoryAIContext(
        story_id=1,
        story_title="Test Story",
        story_theme="Isolation",
        story_genre="Mystery",
        story_tone="Dark",
        story_season="Autumn",
        story_length="short",
        story_status="active",
        current_scene=SceneContext(
            id=10,
            story_id=1,
            scene_number=1,
            location=scene_location,
            mood=scene_mood,
            content="The corridor stretches into darkness.",
            is_ending=is_ending,
        ),
        runtime=StoryRuntimeContext(
            turn_number=turn_number,
            yugen_meter=yugen_meter,
            hidden_variables=hidden_variables or {},
            world_state=world_state or {},
        ),
        characters=characters if characters is not None else [
            CharacterContext(
                id=1,
                name="Hana",
                role="Villager",
                age=30,
                background="Old resident of the village.",
                goals=["Escape"],
                fears=["Darkness", "Drowning"],
                secrets=["Knows who caused the fire"],
                emotions=CharacterEmotionContext(
                    fear=60, anxiety=50, anger=10,
                    sadness=30, happiness=10, trust=20,
                ),
                traits=CharacterTraitsContext(
                    openness=40, conscientiousness=60,
                    extraversion=20, agreeableness=35, neuroticism=75,
                ),
            )
        ],
        relevant_memories=memories or [],
        recent_history=history or [],
        player_input=player_input,
    )


VALID_AI_RESPONSE = json.dumps({
    "issues": [
        {
            "issue_type": "world_state_contradiction",
            "severity": "medium",
            "description": "Fog described as clear.",
            "evidence": "World variable fog_level='heavy'; narrative says 'clear sky'.",
            "affected_character_id": None,
            "affected_location": None,
            "confidence": 75,
        }
    ],
    "overall_confidence": 80,
    "summary": "One medium severity world-state contradiction detected.",
})

CLEAN_AI_RESPONSE = json.dumps({
    "issues": [],
    "overall_confidence": 92,
    "summary": "No consistency issues detected.",
})


# ---------------------------------------------------------------------------
# 1. Schema Tests (1-6)
# ---------------------------------------------------------------------------


def test_schema_valid_consistency_report() -> None:
    """1. Valid ConsistencyReport validates successfully."""
    report = ConsistencyReport(
        is_consistent=True,
        issues=[],
        overall_confidence=90,
        check_status=CheckStatus.PASSED,
        checked_categories=[IssueCategory.WORLD_STATE_CONTRADICTION],
        unavailable_categories=[],
        summary="All clear.",
    )
    assert report.is_consistent is True
    assert report.check_status == CheckStatus.PASSED


def test_schema_valid_consistency_issue() -> None:
    """2. Valid ConsistencyIssue validates successfully."""
    issue = ConsistencyIssue(
        issue_type=IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION,
        severity=IssueSeverity.HIGH,
        description="Character broke from established fear.",
        evidence="Character fear=85/100; narrative shows no fear.",
        affected_character_id=5,
        confidence=85,
    )
    assert issue.severity == IssueSeverity.HIGH
    assert issue.affected_character_id == 5


def test_schema_invalid_severity_rejected() -> None:
    """3. Invalid severity value raises ValidationError."""
    with pytest.raises(ValidationError):
        ConsistencyIssue(
            issue_type=IssueCategory.OTHER,
            severity="catastrophic",  # type: ignore[arg-type]
            description="Something bad.",
            evidence="Some evidence.",
            confidence=50,
        )


def test_schema_invalid_confidence_out_of_range() -> None:
    """4. Confidence outside 0-100 raises ValidationError."""
    with pytest.raises(ValidationError):
        ConsistencyIssue(
            issue_type=IssueCategory.OTHER,
            severity=IssueSeverity.LOW,
            description="Something.",
            evidence="Evidence.",
            confidence=150,  # Out of range
        )


def test_schema_serialization_roundtrip() -> None:
    """5. ConsistencyReport serializes and deserializes cleanly."""
    report = ConsistencyReport(
        is_consistent=False,
        issues=[
            ConsistencyIssue(
                issue_type=IssueCategory.UNAUTHORIZED_ACTION,
                severity=IssueSeverity.CRITICAL,
                description="Narrative forces player death.",
                evidence="'You die immediately' in narration.",
                confidence=95,
            )
        ],
        overall_confidence=70,
        check_status=CheckStatus.ISSUES_FOUND,
        checked_categories=[IssueCategory.SCENE_CONTINUITY],
        unavailable_categories=[IssueCategory.MEMORY_CONTRADICTION],
        summary="Critical unauthorized action detected.",
    )
    dumped = report.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["check_status"] == "issues_found"
    assert len(dumped["issues"]) == 1

    json_str = report.model_dump_json()
    reloaded = ConsistencyReport.model_validate_json(json_str)
    assert reloaded == report


def test_schema_extra_fields_forbidden_on_issue() -> None:
    """6. Extra fields in ConsistencyIssue are rejected (extra='forbid')."""
    with pytest.raises(ValidationError):
        ConsistencyIssue(
            issue_type=IssueCategory.OTHER,
            severity=IssueSeverity.LOW,
            description="Something.",
            evidence="Evidence.",
            confidence=50,
            rogue_field="injected",  # type: ignore[call-arg]
        )

def test_schema_extra_fields_forbidden_on_report() -> None:
    """Extra fields in ConsistencyReport are rejected (extra='forbid')."""
    with pytest.raises(ValidationError):
        ConsistencyReport(
            is_consistent=True,
            issues=[],
            overall_confidence=90,
            check_status=CheckStatus.PASSED,
            checked_categories=[],
            unavailable_categories=[],
            summary="Fine.",
            injected_mutation="evil",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# 2. Deterministic Check Tests (7-14)
# ---------------------------------------------------------------------------


def test_deterministic_world_state_fog_contradiction() -> None:
    """7. Heavy fog + 'clear sky' in narrative is flagged."""
    ctx = _make_context(world_state={"fog_level": "heavy"})
    narrative = _make_narrative("The clear sky stretched above the shrine, brilliant and cloudless.")
    issues, checked = run_deterministic_checks(ctx, narrative)
    ws_issues = [i for i in issues if i.issue_type == IssueCategory.WORLD_STATE_CONTRADICTION]
    assert any("fog" in i.description.lower() or "fog" in i.evidence.lower() for i in ws_issues)


def test_deterministic_no_fog_contradiction_when_no_fog_state() -> None:
    """8. No fog contradiction flagged when world state has no fog variable."""
    ctx = _make_context(world_state={"tension": 70})
    narrative = _make_narrative("A clear sky stretched overhead.")
    issues, _ = run_deterministic_checks(ctx, narrative)
    ws_issues = [i for i in issues if i.issue_type == IssueCategory.WORLD_STATE_CONTRADICTION]
    assert len(ws_issues) == 0


def test_deterministic_character_trust_contradiction() -> None:
    """9. Character with extreme distrust (trust≤15) suddenly trusts completely → flagged."""
    char = CharacterContext(
        id=2, name="Kuro", role="Stranger", age=40, background="Unknown wanderer.",
        goals=[], fears=[], secrets=[],
        emotions=CharacterEmotionContext(fear=20, anxiety=30, anger=5, sadness=10, happiness=5, trust=5),
    )
    ctx = _make_context(characters=[char])
    narrative = _make_narrative("Kuro trusts you completely and smiles warmly at your approach.")
    issues, _ = run_deterministic_checks(ctx, narrative)
    char_issues = [i for i in issues if i.issue_type == IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION]
    assert len(char_issues) >= 1
    assert any(i.affected_character_id == 2 for i in char_issues)


def test_deterministic_no_character_contradiction_for_normal_trust() -> None:
    """10. Character with moderate trust (trust>15) → no contradiction flagged for warmth."""
    char = CharacterContext(
        id=3, name="Yuki", role="Guide", age=25, background="Village guide.",
        goals=[], fears=[], secrets=[],
        emotions=CharacterEmotionContext(fear=10, anxiety=10, anger=5, sadness=5, happiness=50, trust=55),
    )
    ctx = _make_context(characters=[char])
    narrative = _make_narrative("Yuki trusts you completely with a soft nod.")
    issues, _ = run_deterministic_checks(ctx, narrative)
    char_issues = [i for i in issues if i.issue_type == IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION]
    assert len(char_issues) == 0


def test_deterministic_unauthorized_ending_declaration() -> None:
    """11. 'The story ends' in narrative on a non-ending scene is flagged as CRITICAL."""
    ctx = _make_context(is_ending=False)
    narrative = _make_narrative("The story ends here, the final moment of silence.")
    issues, _ = run_deterministic_checks(ctx, narrative)
    scene_issues = [i for i in issues if i.issue_type == IssueCategory.SCENE_CONTINUITY]
    assert len(scene_issues) >= 1
    assert any(i.severity == IssueSeverity.CRITICAL for i in scene_issues)


def test_deterministic_no_ending_flag_on_ending_scene() -> None:
    """12. 'The story ends' on a scene marked is_ending=True → NOT flagged."""
    ctx = _make_context(is_ending=True)
    narrative = _make_narrative("The story ends here as the sun finally sets.")
    issues, _ = run_deterministic_checks(ctx, narrative)
    scene_issues = [i for i in issues if i.issue_type == IssueCategory.SCENE_CONTINUITY]
    assert len(scene_issues) == 0


def test_deterministic_no_false_positive_creative_prose() -> None:
    """13. Rich, atmospheric creative prose does not trigger false positives."""
    ctx = _make_context(
        world_state={"tension": 70},
        hidden_variables={"fog_density": "medium"},
    )
    narrative = _make_narrative(
        "The cedar beams creaked as mist curled through the broken shoji. "
        "Hana pressed herself against the wall, her breath shallow and careful."
    )
    issues, _ = run_deterministic_checks(ctx, narrative)
    assert len(issues) == 0


def test_deterministic_ambiguous_world_state_handled_conservatively() -> None:
    """14. Ambiguous/non-standard world state values do not produce false positives."""
    ctx = _make_context(world_state={"atmosphere": "dense", "dread_level": "high"})
    narrative = _make_narrative("A faint light flickered above.")
    issues, _ = run_deterministic_checks(ctx, narrative)
    # Should not crash and should not produce fog-related false positives
    ws_issues = [i for i in issues if i.issue_type == IssueCategory.WORLD_STATE_CONTRADICTION]
    assert len(ws_issues) == 0


# ---------------------------------------------------------------------------
# 3. AI Semantic Evaluation Tests (15-20)
# ---------------------------------------------------------------------------


def test_ai_provider_called_correctly() -> None:
    """15. ConsistencyChecker calls AI provider exactly once with non-empty prompt."""
    provider = MockProvider(return_text=CLEAN_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)

    assert provider.call_count == 1
    assert provider.last_prompt is not None
    assert len(provider.last_prompt) > 50


def test_ai_context_passed_to_prompt() -> None:
    """16. Story title, scene location, and character name appear in the AI prompt."""
    provider = MockProvider(return_text=CLEAN_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context(scene_location="Midnight Pagoda")
    narrative = _make_narrative()

    checker.check(ctx, narrative)

    prompt = provider.last_prompt
    assert "Test Story" in prompt
    assert "Midnight Pagoda" in prompt
    assert "Hana" in prompt


def test_ai_narrative_passed_to_prompt() -> None:
    """17. Generated narrative text appears in the AI evaluator prompt."""
    provider = MockProvider(return_text=CLEAN_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    unique_text = "The ancient bell tolls seventeen times in the cedar grove."
    narrative = _make_narrative(unique_text)

    checker.check(ctx, narrative)

    assert unique_text in provider.last_prompt


def test_ai_structured_response_validated() -> None:
    """18. Valid AI response produces a structured ConsistencyReport with parsed issues."""
    provider = MockProvider(return_text=VALID_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)

    assert isinstance(report, ConsistencyReport)
    assert len(report.issues) >= 1
    assert any(i.issue_type == IssueCategory.WORLD_STATE_CONTRADICTION for i in report.issues)


def test_ai_invalid_provider_output_handled() -> None:
    """19. Non-JSON / malformed AI response is handled; deterministic results preserved."""
    provider = MockProvider(return_text="This is not JSON at all! 🌀")
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    # Must NOT raise; should return a partial report
    report = checker.check(ctx, narrative)
    assert isinstance(report, ConsistencyReport)
    # Deterministic categories should still be present
    assert IssueCategory.WORLD_STATE_CONTRADICTION in report.checked_categories
    # AI categories should be in unavailable
    assert any(c in report.unavailable_categories for c in [
        IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION,
        IssueCategory.UNAUTHORIZED_ACTION,
    ])


def test_ai_empty_response_handled() -> None:
    """20. Empty string from provider is handled gracefully without crashing."""
    provider = MockProvider(return_text="")
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)
    assert isinstance(report, ConsistencyReport)


# ---------------------------------------------------------------------------
# 4. Fail-Safe Behavior Tests (21-26)
# ---------------------------------------------------------------------------


def test_failsafe_provider_timeout() -> None:
    """21. Provider timeout is caught; deterministic results preserved; report returned."""
    provider = MockProvider(raise_exception=AITimeoutError("Request timed out"))
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)
    assert isinstance(report, ConsistencyReport)
    # Deterministic checks should still have run
    assert IssueCategory.WORLD_STATE_CONTRADICTION in report.checked_categories


def test_failsafe_provider_error() -> None:
    """22. Provider HTTP error is caught; partial report returned."""
    provider = MockProvider(raise_exception=AIProviderError("Internal Server Error", status_code=500))
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)
    assert isinstance(report, ConsistencyReport)
    assert IssueCategory.WORLD_STATE_CONTRADICTION in report.checked_categories


def test_failsafe_rate_limit() -> None:
    """23. Rate limit error from provider is caught; report returned with partial status."""
    provider = MockProvider(raise_exception=AIRateLimitError("Rate limit exceeded", status_code=429))
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)
    assert isinstance(report, ConsistencyReport)


def test_failsafe_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """24. Missing API key: AI categories marked unavailable; deterministic results preserved."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("AI_FALLBACK_PROVIDERS", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    checker = ConsistencyChecker(provider=None)  # Will try to resolve lazily
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)
    assert isinstance(report, ConsistencyReport)
    assert IssueCategory.WORLD_STATE_CONTRADICTION in report.checked_categories
    assert IssueCategory.UNAUTHORIZED_ACTION in report.unavailable_categories


def test_failsafe_ai_unavailable_report_structure() -> None:
    """25. Report explicitly notes unavailable AI categories instead of claiming full verification."""
    checker = ConsistencyChecker(skip_ai_check=True)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)

    # Deterministic checked categories
    assert IssueCategory.WORLD_STATE_CONTRADICTION in report.checked_categories
    # AI categories explicitly unavailable
    assert IssueCategory.UNAUTHORIZED_ACTION in report.unavailable_categories
    assert IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION in report.unavailable_categories or \
           IssueCategory.CHARACTER_BEHAVIOR_CONTRADICTION in report.checked_categories
    # Status must be PARTIAL (no issues + some unavailable) not PASSED
    assert report.check_status in (CheckStatus.PARTIAL, CheckStatus.ISSUES_FOUND)
    # Overall confidence lowered due to unavailability
    assert report.overall_confidence < 90


def test_failsafe_deterministic_findings_preserved_after_provider_failure() -> None:
    """26. Deterministic issues are preserved in report even when AI provider fails."""
    # Set up context that WILL trigger a deterministic issue (heavy fog + "clear sky")
    ctx = _make_context(world_state={"fog_level": "heavy"})
    narrative = _make_narrative("The clear sky blazed above the shrine.")

    provider = MockProvider(raise_exception=AIProviderError("Connection refused", status_code=503))
    checker = ConsistencyChecker(provider=provider)

    report = checker.check(ctx, narrative)

    # Deterministic fog contradiction should still be in issues
    ws_issues = [i for i in report.issues if i.issue_type == IssueCategory.WORLD_STATE_CONTRADICTION]
    assert len(ws_issues) >= 1


# ---------------------------------------------------------------------------
# 5. Safety Guarantee Tests (27-32)
# ---------------------------------------------------------------------------


def test_safety_no_database_access(db_session, setup_story) -> None:
    """27. ConsistencyChecker performs zero database queries or mutations."""
    from backend.app.ai.context_builder import StoryContextBuilder
    from backend.app.models.story_state import StoryState

    story = setup_story["story"]
    scene = setup_story["scene1"]
    state = StoryState(
        story_id=story.id, current_scene_id=scene.id,
        turn_number=2, yugen_meter=40, hidden_variables={},
    )
    db_session.add(state)
    db_session.commit()

    ctx = StoryContextBuilder(db_session).build(story.id)
    narrative = _make_narrative("The wind shifts through the broken gate.")

    provider = MockProvider(return_text=CLEAN_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    report = checker.check(ctx, narrative)

    # DB state untouched
    db_session.refresh(state)
    assert state.turn_number == 2
    assert state.yugen_meter == 40
    assert isinstance(report, ConsistencyReport)


def test_safety_no_orm_objects_in_provider_prompt() -> None:
    """28. Only plain strings are passed to the AI provider — no ORM objects."""
    provider = MockProvider(return_text=CLEAN_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    checker.check(ctx, narrative)

    assert isinstance(provider.last_prompt, str)
    assert isinstance(provider.last_system_instruction, str)
    assert "<backend.app.models" not in provider.last_prompt
    assert "<sqlalchemy." not in provider.last_prompt


def test_safety_no_deterministic_state_mutation() -> None:
    """29. ConsistencyChecker does not modify context or runtime values."""
    ctx = _make_context(turn_number=5, yugen_meter=65)
    narrative = _make_narrative()

    original_turn = ctx.runtime.turn_number
    original_meter = ctx.runtime.yugen_meter
    original_chars = len(ctx.characters)

    provider = MockProvider(return_text=CLEAN_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    checker.check(ctx, narrative)

    assert ctx.runtime.turn_number == original_turn
    assert ctx.runtime.yugen_meter == original_meter
    assert len(ctx.characters) == original_chars


def test_safety_narrative_remains_unchanged() -> None:
    """30. The narrative passage is never modified by the checker."""
    original_text = "The shoji screen rattles in the mountain wind."
    narrative = _make_narrative(original_text)

    provider = MockProvider(return_text=CLEAN_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    checker.check(ctx, narrative)

    assert narrative.narrative_text == original_text


def test_safety_no_unauthorized_game_state_mutations_from_ai() -> None:
    """31. AI evaluator response cannot inject game-state mutation fields into the report."""
    malicious_response = json.dumps({
        "issues": [],
        "overall_confidence": 90,
        "summary": "All clear.",
        "turn_number": 999,          # Mutation attempt
        "ending_trigger": True,       # Mutation attempt
        "yugen_meter": 100,           # Mutation attempt
        "new_scene_id": 42,           # Mutation attempt
    })
    provider = MockProvider(return_text=malicious_response)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    report = checker.check(ctx, narrative)
    report_dict = report.model_dump()

    assert "turn_number" not in report_dict
    assert "ending_trigger" not in report_dict
    assert "yugen_meter" not in report_dict
    assert "new_scene_id" not in report_dict


def test_safety_no_automatic_narrative_retry() -> None:
    """32. ConsistencyChecker never retries narrative generation."""
    # Provider is called for consistency check, not for generation retry
    provider = MockProvider(return_text=VALID_AI_RESPONSE)
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative()

    checker.check(ctx, narrative)

    # Consistency check calls provider once; must NOT call it additional times for retry
    assert provider.call_count == 1


# ---------------------------------------------------------------------------
# 6. Phase 2 Schema Hardening Audit
# ---------------------------------------------------------------------------


def test_p2_schema_hardening_extra_forbid_active() -> None:
    """NarrativeGenerationResult now rejects extra fields with extra='forbid'."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult(
            narrative_text="The gate creaks open.",
            ending_trigger=True,  # type: ignore[call-arg]
        )


def test_p2_schema_hardening_state_changes_rejected() -> None:
    """state_changes field is rejected by NarrativeGenerationResult."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"narrative_text": "Rain falls.", "state_changes": {"hp": -50}}
        )


def test_p2_schema_hardening_relationship_changes_rejected() -> None:
    """relationship_changes field is rejected by NarrativeGenerationResult."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"narrative_text": "She smiles.", "relationship_changes": {"char_1": {"trust": 20}}}
        )


def test_p2_schema_hardening_emotion_changes_rejected() -> None:
    """emotion_changes field is rejected by NarrativeGenerationResult."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"narrative_text": "Fear grips you.", "emotion_changes": {"fear": 30}}
        )


def test_p2_schema_hardening_world_state_changes_rejected() -> None:
    """world_state_changes field is rejected by NarrativeGenerationResult."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"narrative_text": "The fog thickens.", "world_state_changes": {"fog": "heavy"}}
        )


def test_p2_schema_hardening_scene_transition_rejected() -> None:
    """scene_transition field is rejected by NarrativeGenerationResult."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"narrative_text": "You move forward.", "scene_transition": 42}
        )


def test_p2_schema_hardening_player_action_rejected() -> None:
    """player_action field is rejected by NarrativeGenerationResult."""
    with pytest.raises(ValidationError):
        NarrativeGenerationResult.model_validate(
            {"narrative_text": "You reach for it.", "player_action": "grab_key"}
        )


def test_p2_schema_hardening_legitimate_fields_still_work() -> None:
    """All legitimate NarrativeGenerationResult fields still validate correctly."""
    result = NarrativeGenerationResult.model_validate({
        "narrative_text": "The corridor stretches onward.",
        "scene_title": "Into the Dark",
        "scene_mood": "Tense",
        "passage_summary": "Player moves forward.",
        "dialogue": [{"character_name": "Hana", "dialogue": "Wait."}],
        "model_name": "gemini-3.8-flash",
        "tokens_used": 150,
    })
    assert result.scene_title == "Into the Dark"
    assert result.tokens_used == 150


def test_p2_schema_hardening_generator_injection_raises() -> None:
    """NarrativeGenerator correctly raises AIResponseValidationError for injected state fields."""
    from backend.app.ai.narrative_generator import NarrativeGenerator
    from backend.app.ai.schemas import PlayerInputContext

    injection_json = json.dumps({
        "narrative_text": "You push open the door.",
        "scene_title": "Threshold",
        "turn_number": 9999,
        "ending_triggered": True,
    })

    class LocalMock(BaseLLMProvider):
        def generate(self, prompt, system_instruction=None):
            return injection_json, None

    generator = NarrativeGenerator(provider=LocalMock(model_name="mock"))
    ctx = StoryAIContext(
        story_id=1, story_title="T", story_theme="T", story_genre="M",
        story_tone="D", story_season="A", story_length="short", story_status="active",
        runtime=StoryRuntimeContext(turn_number=1, yugen_meter=50),
    )
    with pytest.raises(AIResponseValidationError):
        generator.generate_narrative(ctx)


# ---------------------------------------------------------------------------
# 7. Optional Live Integration Test
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="Live AI provider credentials not configured in environment.",
)
def test_live_consistency_integration() -> None:
    """Optional live test: real AI provider runs consistency check."""
    from backend.app.ai.providers import get_default_provider

    provider = get_default_provider()
    checker = ConsistencyChecker(provider=provider)
    ctx = _make_context()
    narrative = _make_narrative(
        "The mist curls through the broken shoji as Hana steps back, "
        "her breath barely audible above the distant cedar creak."
    )

    report = checker.check(ctx, narrative)
    assert isinstance(report, ConsistencyReport)
    assert report.check_status in (CheckStatus.PASSED, CheckStatus.ISSUES_FOUND, CheckStatus.PARTIAL)
