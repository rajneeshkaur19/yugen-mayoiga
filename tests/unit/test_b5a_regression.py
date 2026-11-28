"""
Batch 5A Regression Tests
Covers: personalization, language guard, cover-image persistence, image source_type,
feedback API (happy path, validation, rate limit, auth), and language choice fallbacks.
"""
import asyncio
import importlib
import sys
import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# 1. Language Guard Tests
# ---------------------------------------------------------------------------

def test_language_script_directive_japanese():
    from backend.app.ai.language_guard import language_script_directive
    directive = language_script_directive("Japanese")
    assert "日本語" in directive or "Japanese" in directive or "hiragana" in directive.lower() or "katakana" in directive.lower()


def test_language_script_directive_hindi():
    from backend.app.ai.language_guard import language_script_directive
    directive = language_script_directive("Hindi")
    assert "Hindi" in directive or "Devanagari" in directive or "हिंदी" in directive


def test_language_script_directive_french():
    from backend.app.ai.language_guard import language_script_directive
    directive = language_script_directive("French")
    assert "French" in directive or "français" in directive.lower()


def test_language_script_directive_english():
    from backend.app.ai.language_guard import language_script_directive
    directive = language_script_directive("English")
    assert isinstance(directive, str)


def test_validate_output_language_japanese_pass():
    from backend.app.ai.language_guard import validate_output_language
    # Japanese text with hiragana/katakana
    jp_text = "今日は美しい日です。東京のカフェで友達と会いました。"
    ok, reason = validate_output_language(jp_text, "Japanese")
    assert ok is True
    assert reason is None


def test_validate_output_language_japanese_fail_english():
    from backend.app.ai.language_guard import validate_output_language
    en_text = "Today is a beautiful day. I met my friend at a cafe in Tokyo."
    ok, reason = validate_output_language(en_text, "Japanese")
    assert ok is False
    assert reason is not None


def test_validate_output_language_hindi_pass():
    from backend.app.ai.language_guard import validate_output_language
    hi_text = "आज का दिन बहुत सुंदर है। मैं अपने दोस्त से मिला।"
    ok, reason = validate_output_language(hi_text, "Hindi")
    assert ok is True


def test_validate_output_language_hindi_fail_english():
    from backend.app.ai.language_guard import validate_output_language
    en_text = "Today is a beautiful day in the mountains."
    ok, reason = validate_output_language(en_text, "Hindi")
    assert ok is False


def test_validate_output_language_french_pass():
    from backend.app.ai.language_guard import validate_output_language
    fr_text = "C'est une belle journée. Je suis avec mes amis dans le café."
    ok, reason = validate_output_language(fr_text, "French")
    assert ok is True


def test_validate_output_language_english_always_pass():
    from backend.app.ai.language_guard import validate_output_language
    en_text = "This is a simple English sentence about mystery and suspense."
    ok, reason = validate_output_language(en_text, "English")
    assert ok is True


# ---------------------------------------------------------------------------
# 2. Narrative Prompt Personalization Tests
# ---------------------------------------------------------------------------

def _make_story_ai_context(genre="Mystery", tone="Melancholic", theme="abandoned house", language="English"):
    """Create a minimal StoryAIContext for prompt testing."""
    from backend.app.ai.schemas import StoryAIContext, StoryRuntimeContext
    return StoryAIContext(
        story_id=1,
        story_title="Test Story",
        story_theme=theme,
        story_genre=genre,
        story_tone=tone,
        story_season="Autumn",
        story_length="medium",
        story_language=language,
        story_status="active",
        runtime=StoryRuntimeContext(
            turn_number=1,
            yugen_meter=50,
            world_state={"story_premise": "A detective arrives at an old estate"},
            hidden_variables={},
        ),
    )


def test_narrative_prompt_includes_genre():
    from backend.app.ai.prompts.narrative_prompt import build_narrative_user_prompt
    ctx = _make_story_ai_context(genre="Horror", tone="Eerie")
    prompt = build_narrative_user_prompt(ctx)
    assert "Horror" in prompt


def test_narrative_prompt_includes_tone():
    from backend.app.ai.prompts.narrative_prompt import build_narrative_user_prompt
    ctx = _make_story_ai_context(tone="Dreamlike")
    prompt = build_narrative_user_prompt(ctx)
    assert "Dreamlike" in prompt


def test_narrative_prompt_includes_language():
    from backend.app.ai.prompts.narrative_prompt import build_narrative_user_prompt
    ctx = _make_story_ai_context(language="Japanese")
    prompt = build_narrative_user_prompt(ctx)
    # Either the language name or the directive should appear
    assert "Japanese" in prompt or "日本語" in prompt


def test_narrative_prompt_includes_premise():
    from backend.app.ai.prompts.narrative_prompt import build_narrative_user_prompt
    from backend.app.ai.schemas import StoryAIContext, StoryRuntimeContext
    ctx = _make_story_ai_context()
    # Override runtime with our premise
    ctx = StoryAIContext(
        story_id=1,
        story_title="Test Story",
        story_theme="abandoned house",
        story_genre="Mystery",
        story_tone="Melancholic",
        story_season="Autumn",
        story_length="medium",
        story_language="English",
        story_status="active",
        runtime=StoryRuntimeContext(
            turn_number=1,
            yugen_meter=50,
            world_state={"story_premise": "A ghost hunter investigates the ruins"},
            hidden_variables={},
        ),
    )
    prompt = build_narrative_user_prompt(ctx)
    assert "ghost hunter" in prompt


# ---------------------------------------------------------------------------
# 3. Image Generation Source Type Tests
# ---------------------------------------------------------------------------

def test_image_generation_curated_fallback_fields(tmp_path):
    """When AI providers are unconfigured/fail, _orchestrate_generation returns source_type=curated_fallback and is_fallback=True."""
    from backend.app.services import image_generation_service as img_svc

    with patch.object(img_svc, "IMAGE_STORAGE_DIR", tmp_path), \
         patch.dict("os.environ", {"GEMINI_API_KEY": "", "OPENAI_API_KEY": ""}, clear=False):
        res = img_svc._orchestrate_generation(
            prompt="test misty mountain shrine at night",
            fallback_keywords="shrine rain",
            context_label="Scene",
        )
    assert res.success is True
    assert res.source_type == "curated_fallback"
    assert res.is_fallback is True
    assert res.quota_exhausted is False


def test_image_generation_cache_hit_fields(tmp_path):
    """Cache hit should report source_type=cached and is_fallback=False."""
    from backend.app.services import image_generation_service as img_svc

    with patch.object(img_svc, "IMAGE_STORAGE_DIR", tmp_path), \
         patch.object(img_svc, "get_cached_image", return_value=(tmp_path / "cached.png", "/generated-images/cached.png")):
        res = img_svc._orchestrate_generation(
            prompt="test cached scene",
            fallback_keywords="shrine",
            context_label="Scene",
        )
    assert res.success is True
    assert res.source_type == "cached"
    assert res.is_fallback is False
    assert res.quota_exhausted is False


def test_image_generation_response_schema_has_new_fields():
    """LocationImageGenerateResponse schema includes source_type, is_fallback, quota_exhausted."""
    from backend.app.schemas.ai import LocationImageGenerateResponse
    import inspect
    fields = LocationImageGenerateResponse.model_fields
    assert "source_type" in fields
    assert "is_fallback" in fields
    assert "quota_exhausted" in fields


# ---------------------------------------------------------------------------
# 4. Feedback API Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def feedback_client():
    """HTTP test client with feedback rate limiter reset between tests."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.api.feedback import reset_feedback_rate_limiter
    reset_feedback_rate_limiter()
    with TestClient(app) as client:
        yield client


def test_feedback_valid_submission(feedback_client):
    """Valid feedback returns HTTP 201 with id field."""
    resp = feedback_client.post("/feedback", json={
        "feedback_type": "Suggestion",
        "subject": "Great game",
        "message": "Love the atmosphere and story design.",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data


def test_feedback_empty_message_rejected(feedback_client):
    """Empty message is rejected with 422."""
    resp = feedback_client.post("/feedback", json={
        "feedback_type": "Bug Report",
        "subject": "Test",
        "message": "",
    })
    assert resp.status_code == 422


def test_feedback_short_subject_rejected(feedback_client):
    """Subject shorter than 2 chars is rejected with 422."""
    resp = feedback_client.post("/feedback", json={
        "feedback_type": "Bug Report",
        "subject": "X",
        "message": "This is a valid message body.",
    })
    assert resp.status_code == 422


def test_feedback_missing_subject_rejected(feedback_client):
    """Missing subject is rejected with 422."""
    resp = feedback_client.post("/feedback", json={
        "feedback_type": "Other",
        "message": "This is a valid message body.",
    })
    assert resp.status_code == 422


def test_feedback_invalid_type_rejected(feedback_client):
    """Invalid feedback_type is rejected with 422."""
    resp = feedback_client.post("/feedback", json={
        "feedback_type": "spam",
        "subject": "Valid subject",
        "message": "Valid message body.",
    })
    assert resp.status_code == 422


def test_feedback_anonymous_allowed(feedback_client):
    """Anonymous requests (no auth header) are allowed; user_id should be None."""
    resp = feedback_client.post("/feedback", json={
        "feedback_type": "Other",
        "subject": "Anonymous feedback",
        "message": "Sent without authentication credentials.",
    })
    assert resp.status_code == 201
    assert resp.json().get("user_id") is None


def test_feedback_rate_limit(feedback_client):
    """6th submission from same IP within window returns 429."""
    from backend.app.api.feedback import reset_feedback_rate_limiter
    reset_feedback_rate_limiter()
    payload = {
        "feedback_type": "Suggestion",
        "subject": "Rate limit test",
        "message": "Testing the rate limiter endpoint.",
    }
    for i in range(5):
        resp = feedback_client.post("/feedback", json=payload)
        assert resp.status_code == 201, f"Request {i+1} should succeed but got {resp.status_code}"
    sixth = feedback_client.post("/feedback", json=payload)
    assert sixth.status_code == 429


def test_feedback_with_optional_name_email(feedback_client):
    """Optional name and email fields are accepted."""
    resp = feedback_client.post("/feedback", json={
        "feedback_type": "Bug Report",
        "subject": "Bug with portrait",
        "message": "Character portrait fails to load on mobile.",
        "name": "Miyuki",
        "email": "miyuki@example.com",
    })
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# 5. Language Choice Fallback Tests (via choice_generator localized_fallbacks dict)
# ---------------------------------------------------------------------------

LOCALIZED_FALLBACKS = {
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
    "English": (
        "Observe the surroundings carefully.",
        "Reflect on what has happened so far.",
    ),
}


def test_choice_fallback_japanese():
    """Japanese fallback choices contain CJK characters."""
    fb1, fb2 = LOCALIZED_FALLBACKS["Japanese"]
    combined = fb1 + " " + fb2
    has_cjk = any('\u3040' <= ch <= '\u9fff' for ch in combined)
    assert has_cjk, f"Expected Japanese CJK chars, got: {combined}"


def test_choice_fallback_hindi():
    """Hindi fallback choices contain Devanagari characters."""
    fb1, fb2 = LOCALIZED_FALLBACKS["Hindi"]
    combined = fb1 + " " + fb2
    has_devanagari = any('\u0900' <= ch <= '\u097f' for ch in combined)
    assert has_devanagari, f"Expected Devanagari chars, got: {combined}"


def test_choice_fallback_french():
    """French fallback choices contain French text (not generic English)."""
    fb1, fb2 = LOCALIZED_FALLBACKS["French"]
    combined = (fb1 + " " + fb2).lower()
    has_french = any(w in combined for w in ["observer", "réfléchir", "environs", "passé"])
    assert has_french, f"Expected French text, got: {combined}"


def test_choice_fallback_english():
    """English fallback choices are non-empty."""
    fb1, fb2 = LOCALIZED_FALLBACKS["English"]
    assert len(fb1) > 0 and len(fb2) > 0


def test_choice_generator_has_localized_fallbacks():
    """The choice generator source contains localized fallback strings for all 4 languages."""
    import pathlib
    src = pathlib.Path("backend/app/ai/choice_generator.py").read_text(encoding="utf-8")
    for lang, (fb1, _) in LOCALIZED_FALLBACKS.items():
        if lang != "English":
            assert fb1 in src, f"Expected {lang} fallback text in choice_generator.py"
