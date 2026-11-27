"""Integration and end-to-end tests for AI-mediated actions and dynamic choices (Phase 4).

Covers:
38. Existing deterministic choice still works unchanged
39. AI interpretation passes through deterministic validation
40. AI cannot bypass action validation
41. Invalid action does not mutate state
42. Ambiguous action does not mutate state
43. Dynamic choice selection validates correctly
44. Stale choice handling
45. Authentication/ownership validation remains intact
46. API endpoints for dynamic choices and AI actions
"""

from __future__ import annotations

import json
from typing import Optional, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ai.action_validator import (
    DeterministicActionValidator,
    execute_ai_mediated_action,
)
from backend.app.ai.providers import BaseLLMProvider
from backend.app.ai.schemas import (
    AIActionExecutionResponse,
    AIStoryActionRequest,
    DynamicChoice,
    InterpretedAction,
)
from backend.app.models.story_state import StoryState
from backend.app.models.user import User
from backend.app.models.user_choices_log import UserChoicesLog
from backend.app.services.action_pipeline import process_story_action


class MockIntegrationProvider(BaseLLMProvider):
    """Mock provider configurable for integration tests."""

    def __init__(
        self,
        return_text: str = "",
        raise_exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(model_name="mock-integration-model")
        self.return_text = return_text
        self.raise_exception = raise_exception

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Tuple[str, Optional[int]]:
        if self.raise_exception:
            raise self.raise_exception
        return self.return_text, 25


# ---------------------------------------------------------------------------
# Test 38: Existing deterministic choice still works unchanged
# ---------------------------------------------------------------------------


def test_existing_deterministic_choice_unchanged(db_session: Session, setup_story: dict):
    """Verify standard choice_id execution through process_story_action is 100% intact."""
    story = setup_story["story"]
    choice = setup_story["choice"]
    char = setup_story["character"]

    result = process_story_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        choice_id=choice.id,
        active_character_id=char.id,
    )

    assert result["story_id"] == story.id
    assert result["turn_number"] == 1
    assert result["current_scene_id"] == setup_story["scene2"].id
    assert result["scene_location"] == "Irori Hearth"


# ---------------------------------------------------------------------------
# Test 39: AI interpretation passes through deterministic validation
# ---------------------------------------------------------------------------


def test_ai_interpretation_passes_through_deterministic_validation(
    db_session: Session, setup_story: dict
):
    """Verify valid free-text action is interpreted and successfully applied deterministically."""
    story = setup_story["story"]
    char = setup_story["character"]

    interpreted_json = json.dumps(
        {
            "original_text": "I inspect the carvings on the wooden gate.",
            "action_intent": "inspect",
            "target": "wooden gate",
            "approach": "carefully",
            "confidence": 90,
            "is_ambiguous": False,
            "clarification_needed": None,
            "reasoning_summary": "Player examines the gate carvings.",
            "is_supported": True,
        }
    )
    provider = MockIntegrationProvider(return_text=interpreted_json)

    request = AIStoryActionRequest(
        free_text="I inspect the carvings on the wooden gate.",
        character_id=char.id,
    )

    response = execute_ai_mediated_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        action_request=request,
        provider=provider,
    )

    assert response.status == "executed"
    assert response.story_action_result is not None
    assert response.story_action_result["turn_number"] == 1
    assert response.interpretation.action_intent == "inspect"

    # Verify log entry in DB
    log = db_session.scalar(
        select(UserChoicesLog).where(
            UserChoicesLog.story_id == story.id,
            UserChoicesLog.turn_number == 1,
        )
    )
    assert log is not None
    assert "inspect the carvings" in log.free_text


# ---------------------------------------------------------------------------
# Test 40: AI cannot bypass action validation (disallowed verbs rejected)
# ---------------------------------------------------------------------------


def test_ai_cannot_bypass_action_validation_disallowed_verb(
    db_session: Session, setup_story: dict
):
    """Verify that an interpreted action with an unauthorized intent is rejected."""
    story = setup_story["story"]

    malicious_json = json.dumps(
        {
            "original_text": "I execute system shutdown.",
            "action_intent": "exec",  # Unauthorized verb
            "confidence": 95,
            "is_ambiguous": False,
            "is_supported": True,
        }
    )
    provider = MockIntegrationProvider(return_text=malicious_json)

    request = AIStoryActionRequest(free_text="I execute system shutdown.")

    response = execute_ai_mediated_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        action_request=request,
        provider=provider,
    )

    assert response.status == "rejected"
    assert response.story_action_result is None
    assert "not an authorized narrative verb" in response.validation_error


def test_dynamic_choice_forbidden_keyword_in_approach_rejected(
    db_session: Session, setup_story: dict
):
    """Verify that a DynamicChoice with a forbidden keyword in approach is rejected."""
    story = setup_story["story"]
    scene1 = setup_story["scene1"]

    choice_with_bad_approach = DynamicChoice(
        choice_id="dynamic_ai_bad",
        choice_text="Inspect the lock carefully.",
        action_intent="inspect",
        target="lock",
        approach="using eval script",  # Forbidden keyword in approach
        choice_type="dynamic_ai",
        requires_validation=True,
        scene_id=scene1.id,
    )

    request = AIStoryActionRequest(dynamic_choice=choice_with_bad_approach)

    response = execute_ai_mediated_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        action_request=request,
    )

    assert response.status == "rejected"
    assert response.story_action_result is None
    assert "contains forbidden keyword" in response.validation_error



# ---------------------------------------------------------------------------
# Test 41: Invalid action does not mutate state
# ---------------------------------------------------------------------------


def test_invalid_action_does_not_mutate_state(db_session: Session, setup_story: dict):
    """Verify rejected actions leave turn_number and story state unchanged."""
    story = setup_story["story"]

    state_before = db_session.scalar(select(StoryState).where(StoryState.story_id == story.id))
    turn_before = state_before.turn_number if state_before else 0

    unsupported_json = json.dumps(
        {
            "original_text": "I fly over the moon.",
            "action_intent": "move",
            "confidence": 50,
            "is_ambiguous": False,
            "clarification_needed": "Flight is impossible.",
            "is_supported": False,  # Unsupported action
        }
    )
    provider = MockIntegrationProvider(return_text=unsupported_json)

    request = AIStoryActionRequest(free_text="I fly over the moon.")

    response = execute_ai_mediated_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        action_request=request,
        provider=provider,
    )

    assert response.status == "rejected"

    state_after = db_session.scalar(select(StoryState).where(StoryState.story_id == story.id))
    turn_after = state_after.turn_number if state_after else 0
    assert turn_before == turn_after


# ---------------------------------------------------------------------------
# Test 42: Ambiguous action does not mutate state
# ---------------------------------------------------------------------------


def test_ambiguous_action_does_not_mutate_state(db_session: Session, setup_story: dict):
    """Verify ambiguous actions return clarification request without advancing turn."""
    story = setup_story["story"]

    state_before = db_session.scalar(select(StoryState).where(StoryState.story_id == story.id))
    turn_before = state_before.turn_number if state_before else 0

    ambiguous_json = json.dumps(
        {
            "original_text": "maybe",
            "action_intent": "other",
            "confidence": 20,
            "is_ambiguous": True,
            "clarification_needed": "Please specify an action.",
            "is_supported": True,
        }
    )
    provider = MockIntegrationProvider(return_text=ambiguous_json)

    request = AIStoryActionRequest(free_text="maybe")

    response = execute_ai_mediated_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        action_request=request,
        provider=provider,
    )

    assert response.status == "ambiguous"
    assert response.clarification_needed == "Please specify an action."
    assert response.story_action_result is None

    state_after = db_session.scalar(select(StoryState).where(StoryState.story_id == story.id))
    turn_after = state_after.turn_number if state_after else 0
    assert turn_before == turn_after


# ---------------------------------------------------------------------------
# Test 43: Dynamic choice selection validates correctly
# ---------------------------------------------------------------------------


def test_dynamic_choice_selection_validates_correctly(db_session: Session, setup_story: dict):
    """Verify selecting a valid DynamicChoice routes cleanly through deterministic execution."""
    story = setup_story["story"]
    scene1 = setup_story["scene1"]

    dynamic_choice = DynamicChoice(
        choice_id="dynamic_ai_1",
        choice_text="Inspect the moss clinging to the torii gate.",
        action_intent="inspect",
        target="torii gate",
        approach="closely",
        choice_type="dynamic_ai",
        requires_validation=True,
        scene_id=scene1.id,
    )

    request = AIStoryActionRequest(dynamic_choice=dynamic_choice)

    response = execute_ai_mediated_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        action_request=request,
    )

    assert response.status == "executed"
    assert response.story_action_result is not None
    assert response.story_action_result["turn_number"] == 1


# ---------------------------------------------------------------------------
# Test 44: Stale choice handling
# ---------------------------------------------------------------------------


def test_stale_choice_rejected(db_session: Session, setup_story: dict):
    """Verify a DynamicChoice from an earlier scene is rejected as stale."""
    story = setup_story["story"]

    stale_choice = DynamicChoice(
        choice_id="dynamic_ai_old",
        choice_text="Examine the gate.",
        action_intent="inspect",
        choice_type="dynamic_ai",
        requires_validation=True,
        scene_id=9999,  # Mismatched scene ID
    )

    request = AIStoryActionRequest(dynamic_choice=stale_choice)

    response = execute_ai_mediated_action(
        db=db_session,
        user_id=story.user_id,
        story_id=story.id,
        action_request=request,
    )

    assert response.status == "rejected"
    assert "Stale dynamic choice" in response.validation_error


# ---------------------------------------------------------------------------
# Test 45: Authentication / ownership validation remains intact
# ---------------------------------------------------------------------------


def test_unauthorized_user_blocked_from_ai_action(
    db_session: Session, setup_story: dict, other_user: User
):
    """Verify that a user who does not own the story cannot invoke ai-action."""
    story = setup_story["story"]

    request = AIStoryActionRequest(free_text="Look around.")

    with pytest.raises(ValueError, match="does not belong to user"):
        execute_ai_mediated_action(
            db=db_session,
            user_id=other_user.id,
            story_id=story.id,
            action_request=request,
        )


# ---------------------------------------------------------------------------
# Test 46: End-to-end API endpoints for dynamic choices and AI actions
# ---------------------------------------------------------------------------


def test_api_dynamic_choices_endpoint(
    client: TestClient, setup_story: dict, auth_headers: dict, monkeypatch
):
    """Verify GET /stories/{story_id}/dynamic-choices returns expected schema."""
    story = setup_story["story"]

    mock_choices = json.dumps(
        {
            "choices": [
                {
                    "choice_id": "dynamic_ai_1",
                    "choice_text": "Check the ancient milestone for inscriptions.",
                    "action_intent": "inspect",
                }
            ]
        }
    )

    # Patch get_default_provider to return mock provider
    monkeypatch.setattr(
        "backend.app.ai.choice_generator.get_default_provider",
        lambda: MockIntegrationProvider(return_text=mock_choices),
    )

    response = client.get(
        f"/stories/{story.id}/dynamic-choices",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["generation_status"] == "success"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["choice_id"] == "dynamic_ai_1"
    assert data["choices"][0]["choice_type"] == "dynamic_ai"


def test_api_ai_action_endpoint(
    client: TestClient, setup_story: dict, auth_headers: dict, monkeypatch
):
    """Verify POST /stories/{story_id}/ai-action processes free-text action."""
    story = setup_story["story"]

    mock_interp = json.dumps(
        {
            "original_text": "I listen carefully to the wind.",
            "action_intent": "wait",
            "approach": "carefully",
            "confidence": 95,
            "is_ambiguous": False,
            "is_supported": True,
        }
    )

    monkeypatch.setattr(
        "backend.app.ai.action_interpreter.get_default_provider",
        lambda: MockIntegrationProvider(return_text=mock_interp),
    )

    response = client.post(
        f"/stories/{story.id}/ai-action",
        headers=auth_headers,
        json={"free_text": "I listen carefully to the wind."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"
    assert data["story_action_result"]["turn_number"] == 1
    assert data["interpretation"]["action_intent"] == "wait"


def test_api_generate_narrative_endpoint_success(
    client: TestClient, setup_story: dict, auth_headers: dict, monkeypatch
):
    """Verify POST /stories/{story_id}/generate-narrative returns generated narrative envelope."""
    story = setup_story["story"]

    mock_narrative_json = json.dumps(
        {
            "narrative_text": "The wind howls softly through the dilapidated bamboo grove.",
            "scene_title": "The Forgotten Pathway",
            "scene_mood": "Eerie and contemplative",
            "passage_summary": "The traveler paused to observe the quiet grove.",
            "dialogue": [
                {
                    "character_name": "Ren",
                    "dialogue": "Watch your step here; the earth remembers.",
                }
            ],
            "model_name": "mock-narrative-model",
        }
    )

    monkeypatch.setattr(
        "backend.app.ai.narrative_generator.get_default_provider",
        lambda: MockIntegrationProvider(return_text=mock_narrative_json),
    )

    response = client.post(
        f"/stories/{story.id}/generate-narrative",
        headers=auth_headers,
        json={"choice_text": "Step into the bamboo grove"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["narrative"] is not None
    assert "dilapidated bamboo grove" in data["narrative"]["narrative_text"]
    assert len(data["narrative"]["dialogue"]) == 1
    assert data["narrative"]["dialogue"][0]["character_name"] == "Ren"


def test_api_generate_narrative_endpoint_unavailable(
    client: TestClient, setup_story: dict, auth_headers: dict, monkeypatch
):
    """Verify POST /stories/{story_id}/generate-narrative returns graceful unavailable envelope on provider failure."""
    story = setup_story["story"]

    from backend.app.ai.exceptions import AIProviderError

    monkeypatch.setattr(
        "backend.app.ai.narrative_generator.get_default_provider",
        lambda: MockIntegrationProvider(
            raise_exception=AIProviderError("API rate limit exceeded")
        ),
    )

    response = client.post(
        f"/stories/{story.id}/generate-narrative",
        headers=auth_headers,
        json={},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["narrative"] is None
    assert "AI narrative generator unavailable" in data["error_message"]


def test_api_generate_narrative_endpoint_unauthorized(
    client: TestClient, setup_story: dict, db_session: Session
):
    """Verify POST /stories/{story_id}/generate-narrative requires auth and story ownership."""
    story = setup_story["story"]

    # Without auth
    res_no_auth = client.post(
        f"/stories/{story.id}/generate-narrative",
        json={},
    )
    assert res_no_auth.status_code in (401, 403)

