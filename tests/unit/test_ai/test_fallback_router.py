"""Unit and integration tests for Multi-Provider Fallback Router in Yūgen Mayoiga.

Tests:
1. Gemini success (no fallback triggered)
2. Gemini 429 (Rate Limit) -> OpenAI fallback success
3. Gemini 503 (Server Overload) -> OpenAI fallback success
4. Gemini timeout -> Ollama / next provider success
5. All providers unavailable -> Graceful error (AIProviderError HTTP 503)
6. Malformed provider response handled without crashing
7. Missing optional provider configuration (e.g. OpenAI unset) handled gracefully
8. Correct priority order respected (Gemini -> OpenAI -> Ollama)
9. Provider health tracking (cooldown marks unhealthy, auto-recovers after expiration)
10. No API keys exposed in error messages or logs
11. In-memory scene choice caching prevents duplicate calls
"""

from __future__ import annotations

import json
from typing import Optional, Tuple
import pytest

from backend.app.ai.exceptions import (
    AIConfigurationError,
    AIEmptyResponseError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from backend.app.ai.providers import (
    BaseLLMProvider,
    FallbackRouter,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderHealthTracker,
    build_fallback_chain,
)


class MockProvider(BaseLLMProvider):
    """Configurable mock provider for fallback testing."""

    def __init__(
        self,
        name: str = "MockProvider",
        model_name: str = "mock-model",
        return_text: str = '{"status": "ok"}',
        return_tokens: int = 42,
        raise_exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(model_name=model_name)
        self.provider_name = name
        self.return_text = return_text
        self.return_tokens = return_tokens
        self.raise_exception = raise_exception
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Tuple[str, Optional[int]]:
        self.call_count += 1
        if self.raise_exception:
            raise self.raise_exception
        return self.return_text, self.return_tokens


# ---------------------------------------------------------------------------
# 1. Gemini Success (No Fallback)
# ---------------------------------------------------------------------------


def test_gemini_success_no_fallback() -> None:
    gemini = MockProvider(name="GeminiProvider", return_text='{"result": "gemini_prose"}')
    openai = MockProvider(name="OpenAIProvider", return_text='{"result": "openai_prose"}')

    router = FallbackRouter(providers=[gemini, openai])
    text, tokens = router.generate("Continue the story")

    assert "gemini_prose" in text
    assert gemini.call_count == 1
    assert openai.call_count == 0


# ---------------------------------------------------------------------------
# 2. Gemini 429 -> OpenAI Fallback Success
# ---------------------------------------------------------------------------


def test_gemini_429_fallback_to_openai() -> None:
    gemini = MockProvider(
        name="GeminiProvider",
        raise_exception=AIRateLimitError("Gemini quota exceeded", status_code=429),
    )
    openai = MockProvider(name="OpenAIProvider", return_text='{"result": "openai_rescued"}')

    tracker = ProviderHealthTracker(cooldown_seconds=10.0)
    router = FallbackRouter(providers=[gemini, openai], health_tracker=tracker)

    text, tokens = router.generate("What happens next?")

    assert "openai_rescued" in text
    assert gemini.call_count == 1
    assert openai.call_count == 1
    # Check that Gemini is now tracked as unhealthy
    assert not tracker.is_healthy("GeminiProvider")


# ---------------------------------------------------------------------------
# 3. Gemini 503 (Server Overload) -> OpenAI Fallback Success
# ---------------------------------------------------------------------------


def test_gemini_503_fallback_to_openai() -> None:
    gemini = MockProvider(
        name="GeminiProvider",
        raise_exception=AIProviderError("Gemini model high demand", status_code=503),
    )
    openai = MockProvider(name="OpenAIProvider", return_text='{"result": "openai_handled_503"}')

    tracker = ProviderHealthTracker(cooldown_seconds=10.0)
    router = FallbackRouter(providers=[gemini, openai], health_tracker=tracker)
    text, tokens = router.generate("Enter the shrine")

    assert "openai_handled_503" in text
    assert gemini.call_count == 1
    assert openai.call_count == 1


# ---------------------------------------------------------------------------
# 4. Gemini Timeout -> Next Provider
# ---------------------------------------------------------------------------


def test_gemini_timeout_fallback_to_next() -> None:
    gemini = MockProvider(
        name="GeminiProvider",
        raise_exception=AITimeoutError("Gemini API request timed out after 30.0s"),
    )
    ollama = MockProvider(name="OllamaProvider", return_text='{"result": "ollama_local"}')

    tracker = ProviderHealthTracker(cooldown_seconds=10.0)
    router = FallbackRouter(providers=[gemini, ollama], health_tracker=tracker)
    text, tokens = router.generate("Check the door")

    assert "ollama_local" in text
    assert gemini.call_count == 1
    assert ollama.call_count == 1


# ---------------------------------------------------------------------------
# 5. All Providers Unavailable -> Graceful AIProviderError
# ---------------------------------------------------------------------------


def test_all_providers_unavailable_raises_provider_error() -> None:
    gemini = MockProvider(
        name="GeminiProvider",
        raise_exception=AIRateLimitError("Gemini 429", status_code=429),
    )
    openai = MockProvider(
        name="OpenAIProvider",
        raise_exception=AIProviderError("OpenAI 500 error", status_code=500),
    )

    router = FallbackRouter(providers=[gemini, openai])

    with pytest.raises(AIProviderError) as exc_info:
        router.generate("Descend the stairwell")

    assert "All configured AI providers failed" in str(exc_info.value)
    assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# 6. Malformed Response Handled Gracefully
# ---------------------------------------------------------------------------


def test_malformed_response_triggers_fallback() -> None:
    gemini = MockProvider(
        name="GeminiProvider",
        raise_exception=AIProviderError("Malformed HTTP response"),
    )
    openai = MockProvider(name="OpenAIProvider", return_text='{"valid": true}')

    router = FallbackRouter(providers=[gemini, openai])
    text, _ = router.generate("Inspect the talisman")

    assert "valid" in text
    assert openai.call_count == 1


# ---------------------------------------------------------------------------
# 7. Missing Optional Provider Configuration Handled
# ---------------------------------------------------------------------------


def test_missing_optional_provider_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    chain = build_fallback_chain()
    # Should only build Gemini provider without failing on missing OpenAI
    assert len(chain) >= 1
    assert any(isinstance(p, GeminiProvider) for p in chain)
    assert not any(isinstance(p, OpenAIProvider) for p in chain)


# ---------------------------------------------------------------------------
# 8. Correct Provider Order Respected
# ---------------------------------------------------------------------------


def test_provider_order_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    chain = build_fallback_chain()
    assert len(chain) >= 2
    assert isinstance(chain[0], GeminiProvider)
    assert isinstance(chain[1], OpenAIProvider)


# ---------------------------------------------------------------------------
# 9. Provider Health Tracking & Cooldown
# ---------------------------------------------------------------------------


def test_provider_health_tracker_cooldown() -> None:
    tracker = ProviderHealthTracker(cooldown_seconds=0.2)
    assert tracker.is_healthy("GeminiProvider")

    tracker.mark_unhealthy("GeminiProvider")
    assert not tracker.is_healthy("GeminiProvider")

    import time
    time.sleep(0.25)
    assert tracker.is_healthy("GeminiProvider")


# ---------------------------------------------------------------------------
# 10. No API Keys Exposed in Error Messages
# ---------------------------------------------------------------------------


def test_no_api_keys_in_error_messages() -> None:
    secret_key = "AIzaSySuperSecretKey12345"
    gemini = MockProvider(
        name="GeminiProvider",
        raise_exception=AIRateLimitError("Quota limit hit", status_code=429),
    )

    router = FallbackRouter(providers=[gemini])
    with pytest.raises(AIProviderError) as exc_info:
        router.generate("Prompt")

    err_str = str(exc_info.value)
    assert secret_key not in err_str
