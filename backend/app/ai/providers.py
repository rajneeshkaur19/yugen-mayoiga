"""LLM Provider adapters for Yūgen Mayoiga AI narrative generation.

Supports Google Gemini and OpenAI with environment-driven configuration,
secure credential management, bounded retries on transient errors, and strict
exception mapping.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import httpx

from backend.app.core.timing import logger, pipeline_timer
from backend.app.ai.exceptions import (
    AIConfigurationError,
    AIEmptyResponseError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)

# ---------------------------------------------------------------------------
# Base Provider
# ---------------------------------------------------------------------------


class BaseLLMProvider(ABC):
    """Abstract interface for LLM text-generation providers."""

    def __init__(
        self,
        model_name: str,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Optional[int]]:
        """Send prompt to the LLM and return (raw_text_response, tokens_used).

        Raises
        ------
        AIProviderError
        AIRateLimitError
        AITimeoutError
        AIEmptyResponseError
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Google Gemini Provider
# ---------------------------------------------------------------------------


class GeminiProvider(BaseLLMProvider):
    """Provider adapter communicating with Google Gemini REST API."""

    provider_name: str = "GeminiProvider"
    DEFAULT_MODEL = "gemini-3.8-flash"
    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise AIConfigurationError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in the environment."
            )
        self._api_key = key
        model = model_name or os.getenv("GEMINI_MODEL") or self.DEFAULT_MODEL
        env_timeout = float(os.getenv("GEMINI_TIMEOUT", "12.0"))
        effective_timeout = timeout if timeout is not None else env_timeout
        env_retries = int(os.getenv("GEMINI_MAX_RETRIES", "1"))
        effective_retries = max_retries if max_retries is not None else env_retries
        super().__init__(model_name=model, timeout=effective_timeout, max_retries=effective_retries)
        self.base_url = (base_url or os.getenv("GEMINI_API_BASE") or self.DEFAULT_BASE_URL).rstrip("/")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Optional[int]]:
        """Call Gemini generateContent endpoint with bounded retry on transient errors."""
        endpoint = f"{self.base_url}/models/{self.model_name}:generateContent?key={self._api_key}"

        generation_config: dict = {
            "responseMimeType": "application/json",
            "temperature": 0.7,
        }
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens

        payload: dict = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": generation_config,
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}],
            }

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )

                status = response.status_code

                if status == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise AIEmptyResponseError("Gemini returned no candidates in response.")

                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts or not parts[0].get("text"):
                        raise AIEmptyResponseError("Gemini returned empty content in candidate.")

                    text = parts[0]["text"]
                    tokens = data.get("usageMetadata", {}).get("totalTokenCount")
                    return text, tokens

                # Error responses
                error_body = {}
                try:
                    error_body = response.json()
                except Exception:
                    pass

                err_msg = (
                    error_body.get("error", {}).get("message")
                    or f"Gemini API returned HTTP {status}"
                )

                if status == 429:
                    raise AIRateLimitError(
                        f"Gemini API rate limit exceeded (HTTP 429): {err_msg}",
                        status_code=429,
                    )

                # Retry on 5xx server errors
                if 500 <= status < 600:
                    raise AIProviderError(
                        f"Gemini API server error (HTTP {status}): {err_msg}",
                        status_code=status,
                    )

                # Client errors (400, 401, 403, 404) should not be retried
                raise AIProviderError(
                    f"Gemini API error (HTTP {status}): {err_msg}",
                    status_code=status,
                )

            except (httpx.TimeoutException, AITimeoutError) as exc:
                raise AITimeoutError(
                    f"Gemini API request timed out after {self.timeout}s: {exc}"
                )
            except (AIRateLimitError, AIProviderError) as exc:
                last_exception = exc
                if isinstance(exc, AIRateLimitError):
                    raise
                if isinstance(exc, AIProviderError) and exc.status_code and exc.status_code < 500 and exc.status_code != 429:
                    raise
            except httpx.RequestError as exc:
                last_exception = AIProviderError(f"Network error connecting to Gemini API: {exc}")
            except Exception as exc:
                if isinstance(exc, (AIEmptyResponseError, AIConfigurationError)):
                    raise
                last_exception = AIProviderError(f"Unexpected error calling Gemini API: {exc}")

            # If retries remaining and error is retryable (timeout, 429, 5xx, or network)
            if attempt < self.max_retries:
                backoff = 0.5 * (2**attempt)
                time.sleep(backoff)

        # Retries exhausted
        if last_exception:
            raise last_exception
        raise AIProviderError("Gemini API call failed after retries.")


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------


class OpenAIProvider(BaseLLMProvider):
    """Provider adapter communicating with OpenAI Chat Completions API."""

    provider_name: str = "OpenAIProvider"
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise AIConfigurationError(
                "OpenAI API key is not configured. Please set OPENAI_API_KEY in the environment."
            )
        self._api_key = key
        model = model_name or os.getenv("OPENAI_MODEL") or self.DEFAULT_MODEL
        env_timeout = float(os.getenv("OPENAI_TIMEOUT", "12.0"))
        effective_timeout = timeout if timeout is not None else env_timeout
        env_retries = int(os.getenv("OPENAI_MAX_RETRIES", "1"))
        effective_retries = max_retries if max_retries is not None else env_retries
        super().__init__(model_name=model, timeout=effective_timeout, max_retries=effective_retries)
        self.base_url = (base_url or os.getenv("OPENAI_API_BASE") or self.DEFAULT_BASE_URL).rstrip("/")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Optional[int]]:
        """Call OpenAI chat/completions endpoint with JSON mode and bounded retries."""
        endpoint = f"{self.base_url}/chat/completions"

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: dict = {
            "model": self.model_name,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(endpoint, json=payload, headers=headers)

                status = response.status_code

                if status == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise AIEmptyResponseError("OpenAI returned no choices in response.")

                    msg = choices[0].get("message", {})
                    content = msg.get("content")
                    if not content or not content.strip():
                        raise AIEmptyResponseError("OpenAI returned empty content in message.")

                    tokens = data.get("usage", {}).get("total_tokens")
                    return content, tokens

                error_body = {}
                try:
                    error_body = response.json()
                except Exception:
                    pass

                err_msg = (
                    error_body.get("error", {}).get("message")
                    or f"OpenAI API returned HTTP {status}"
                )

                if status == 429:
                    raise AIRateLimitError(
                        f"OpenAI API rate limit exceeded (HTTP 429): {err_msg}",
                        status_code=429,
                    )

                if 500 <= status < 600:
                    raise AIProviderError(
                        f"OpenAI API server error (HTTP {status}): {err_msg}",
                        status_code=status,
                    )

                raise AIProviderError(
                    f"OpenAI API error (HTTP {status}): {err_msg}",
                    status_code=status,
                )

            except (httpx.TimeoutException, AITimeoutError) as exc:
                last_exception = AITimeoutError(
                    f"OpenAI API request timed out after {self.timeout}s: {exc}"
                )
            except (AIRateLimitError, AIProviderError) as exc:
                last_exception = exc
                if isinstance(exc, AIRateLimitError):
                    raise
                if isinstance(exc, AIProviderError) and exc.status_code and exc.status_code < 500 and exc.status_code != 429:
                    raise
            except httpx.RequestError as exc:
                last_exception = AIProviderError(f"Network error connecting to OpenAI API: {exc}")
            except Exception as exc:
                if isinstance(exc, (AIEmptyResponseError, AIConfigurationError)):
                    raise
                last_exception = AIProviderError(f"Unexpected error calling OpenAI API: {exc}")

            if attempt < self.max_retries:
                backoff = 0.5 * (2**attempt)
                time.sleep(backoff)

        if last_exception:
            raise last_exception
        raise AIProviderError("OpenAI API call failed after retries.")


# ---------------------------------------------------------------------------
# Ollama Local Provider (Optional Tertiary Fallback)
# ---------------------------------------------------------------------------


class OllamaProvider(BaseLLMProvider):
    """Provider adapter communicating with a local Ollama server, optimized for Phi-3."""

    provider_name: str = "OllamaProvider"
    DEFAULT_MODEL = "phi3:latest"
    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    DEFAULT_TIMEOUT = 60.0
    DEFAULT_NUM_PREDICT = 256
    DEFAULT_NUM_CTX = 2048
    DEFAULT_KEEP_ALIVE = "30m"
    DEFAULT_NUM_THREAD = min(8, os.cpu_count() or 4)

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 1,
        num_predict: Optional[int] = None,
        num_ctx: Optional[int] = None,
        keep_alive: Optional[str] = None,
        num_thread: Optional[int] = None,
    ) -> None:
        model = model_name or os.getenv("OLLAMA_MODEL") or self.DEFAULT_MODEL
        env_timeout = float(os.getenv("OLLAMA_TIMEOUT", str(self.DEFAULT_TIMEOUT)))
        effective_timeout = timeout if timeout is not None else env_timeout
        super().__init__(model_name=model, timeout=effective_timeout, max_retries=max_retries)
        self.base_url = (base_url or os.getenv("OLLAMA_API_BASE") or self.DEFAULT_BASE_URL).rstrip("/")

        env_predict = int(os.getenv("OLLAMA_NUM_PREDICT", str(self.DEFAULT_NUM_PREDICT)))
        self.num_predict = num_predict if num_predict is not None else env_predict

        env_ctx = int(os.getenv("OLLAMA_NUM_CTX", str(self.DEFAULT_NUM_CTX)))
        self.num_ctx = num_ctx if num_ctx is not None else env_ctx

        self.keep_alive = keep_alive or os.getenv("OLLAMA_KEEP_ALIVE", self.DEFAULT_KEEP_ALIVE)

        env_thread = int(os.getenv("OLLAMA_NUM_THREAD", str(self.DEFAULT_NUM_THREAD)))
        self.num_thread = num_thread if num_thread is not None else env_thread

    def warmup(self) -> bool:
        """Preload the local model into memory with extended keep_alive to eliminate cold-start latency."""
        endpoint = f"{self.base_url}/api/generate"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    endpoint,
                    json={"model": self.model_name, "keep_alive": self.keep_alive},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Optional[int]]:
        """Call Ollama /api/generate with JSON format, bounded tokens, and retries."""
        endpoint = f"{self.base_url}/api/generate"

        predict_tokens = max_tokens if max_tokens is not None else self.num_predict

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": self.keep_alive,
            "options": {
                "num_predict": predict_tokens,
                "num_ctx": self.num_ctx,
                "num_thread": self.num_thread,
                "temperature": 0.2,
                "top_p": 0.9,
            },
        }
        if system_instruction:
            payload["system"] = system_instruction

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(endpoint, json=payload)

                status = response.status_code
                if status == 200:
                    data = response.json()
                    content = data.get("response", "")
                    if not content or not content.strip():
                        raise AIEmptyResponseError("Ollama returned empty response.")
                    # Clean any trailing or leading markdown code block wrappers
                    clean_content = content.strip()
                    if clean_content.startswith("```"):
                        clean_content = re.sub(r"^```(?:json)?\s*", "", clean_content, flags=re.IGNORECASE)
                        clean_content = re.sub(r"\s*```$", "", clean_content)
                    tokens = data.get("eval_count")
                    return clean_content.strip(), tokens

                raise AIProviderError(
                    f"Ollama server returned HTTP {status}: {response.text[:200]}",
                    status_code=status,
                )
            except (httpx.TimeoutException, AITimeoutError) as exc:
                last_exception = AITimeoutError(f"Ollama request timed out after {self.timeout}s: {exc}")
            except (AIRateLimitError, AIProviderError) as exc:
                last_exception = exc
            except httpx.RequestError as exc:
                last_exception = AIProviderError(f"Could not connect to Ollama at {self.base_url}: {exc}")
            except Exception as exc:
                if isinstance(exc, (AIEmptyResponseError, AIConfigurationError)):
                    raise
                last_exception = AIProviderError(f"Unexpected error calling Ollama: {exc}")

            if attempt < self.max_retries:
                time.sleep(0.5 * (2**attempt))

        if last_exception:
            raise last_exception
        raise AIProviderError("Ollama call failed after retries.")


# ---------------------------------------------------------------------------
# Provider Health Tracking & Multi-Provider Fallback Router
# ---------------------------------------------------------------------------


class ProviderHealthTracker:
    """Tracks temporary provider outages (429, 503, timeouts) without permanent lockouts."""

    def __init__(self, cooldown_seconds: float = 300.0) -> None:
        self.cooldown_seconds = cooldown_seconds
        # provider_name -> timestamp of when cooldown expires
        self._cooldowns: dict[str, float] = {}

    def is_healthy(self, provider_name: str) -> bool:
        """Check if provider is currently in cooldown."""
        expire_time = self._cooldowns.get(provider_name, 0.0)
        return time.time() >= expire_time

    def mark_unhealthy(self, provider_name: str, duration: Optional[float] = None) -> None:
        """Mark provider unhealthy for a duration (defaulting to cooldown_seconds)."""
        cooldown = duration if duration is not None else self.cooldown_seconds
        self._cooldowns[provider_name] = time.time() + cooldown

    def mark_healthy(self, provider_name: str) -> None:
        """Clear unhealthy cooldown status."""
        self._cooldowns.pop(provider_name, None)

    def reset(self) -> None:
        """Reset all tracking."""
        self._cooldowns.clear()


# Global tracker instance
HEALTH_TRACKER = ProviderHealthTracker(cooldown_seconds=300.0)


class FallbackRouter(BaseLLMProvider):
    """Centralized multi-provider router that cascades through a priority fallback chain.

    If a provider encounters recoverable errors (HTTP 429, HTTP 503, timeouts, connection
    drops), the router automatically delegates to the next configured provider without
    crashing the narrative loop or exposing secret keys.
    """

    def __init__(
        self,
        providers: Optional[list[BaseLLMProvider]] = None,
        health_tracker: Optional[ProviderHealthTracker] = None,
    ) -> None:
        self.providers = providers or []
        self.tracker = health_tracker or HEALTH_TRACKER
        model_name = self.providers[0].model_name if self.providers else "fallback-router"
        super().__init__(model_name=model_name)

    @property
    def active_model_name(self) -> str:
        """Return the current model name of the first available provider."""
        for p in self.providers:
            p_name = getattr(p, "provider_name", None) or type(p).__name__
            if self.tracker.is_healthy(p_name):
                return p.model_name
        return self.providers[0].model_name if self.providers else "none"

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Optional[int]]:
        """Attempt generation through the fallback chain with latency tracking."""
        if not self.providers:
            raise AIConfigurationError(
                "No AI providers configured in fallback chain. Set GEMINI_API_KEY, OPENAI_API_KEY, or OLLAMA_MODEL."
            )

        errors: list[str] = []

        # Try healthy providers first
        healthy_providers = [
            p for p in self.providers
            if self.tracker.is_healthy(getattr(p, "provider_name", None) or type(p).__name__)
        ]
        # If all providers are in cooldown, don't give up: try all configured providers anyway
        candidates = healthy_providers if healthy_providers else self.providers

        for provider in candidates:
            provider_name = getattr(provider, "provider_name", None) or type(provider).__name__
            t_start = time.perf_counter()
            try:
                try:
                    result, tokens = provider.generate(
                        prompt,
                        system_instruction=system_instruction,
                        max_tokens=max_tokens,
                        **kwargs,
                    )
                except TypeError:
                    result, tokens = provider.generate(
                        prompt,
                        system_instruction=system_instruction,
                    )

                dur = time.perf_counter() - t_start
                logger.info(f"[TIMING] LLM Provider Success: {dur:.3f}s | provider={provider_name} | model={provider.model_name} | tokens={tokens}")
                # Success: mark healthy and update active model
                self.tracker.mark_healthy(provider_name)
                self.model_name = provider.model_name
                return result, tokens
            except (AIRateLimitError, AITimeoutError) as exc:
                dur = time.perf_counter() - t_start
                logger.warning(f"[TIMING] LLM Provider Recoverable Failure: {dur:.3f}s | provider={provider_name} | error={exc}")
                # Recoverable error: mark provider unhealthy for cooldown and try next
                self.tracker.mark_unhealthy(provider_name)
                sanitized_err = f"[{provider_name}] {exc.__class__.__name__}: {exc}"
                errors.append(sanitized_err)
                continue
            except AIProviderError as exc:
                dur = time.perf_counter() - t_start
                logger.warning(f"[TIMING] LLM Provider Error: {dur:.3f}s | provider={provider_name} | error={exc}")
                # Recoverable if 5xx server error, or connection error, or 429
                status = getattr(exc, "status_code", None)
                if status == 429 or (status and 500 <= status < 600) or status is None:
                    self.tracker.mark_unhealthy(provider_name)
                    sanitized_err = f"[{provider_name}] Server/Connection error ({status}): {exc}"
                    errors.append(sanitized_err)
                    continue
                # Non-recoverable client error (e.g. 400 Bad Request) - try next provider in case of schema/model incompatibility
                sanitized_err = f"[{provider_name}] Client error ({status}): {exc}"
                errors.append(sanitized_err)
                continue
            except Exception as exc:
                dur = time.perf_counter() - t_start
                logger.warning(f"[TIMING] LLM Provider Unexpected Failure: {dur:.3f}s | provider={provider_name} | error={exc}")
                sanitized_err = f"[{provider_name}] Unexpected failure: {exc}"
                errors.append(sanitized_err)
                continue

        # All providers failed
        error_summary = " | ".join(errors)
        raise AIProviderError(
            f"All configured AI providers failed. Outages: {error_summary}",
            status_code=503,
        )


# ---------------------------------------------------------------------------
# Provider Factory
# ---------------------------------------------------------------------------


def build_fallback_chain() -> list[BaseLLMProvider]:
    """Assemble configured providers in default priority order: Gemini -> OpenAI -> Ollama."""
    providers: list[BaseLLMProvider] = []

    # Priority 1: Gemini
    if os.getenv("GEMINI_API_KEY"):
        try:
            providers.append(GeminiProvider())
        except Exception:
            pass

    # Priority 2: OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            providers.append(OpenAIProvider())
        except Exception:
            pass

    # Priority 3: Ollama (if explicitly configured via OLLAMA_MODEL or AI_FALLBACK_PROVIDERS has ollama AND OLLAMA_MODEL is set)
    fallback_cfg = [p.strip().lower() for p in os.getenv("AI_FALLBACK_PROVIDERS", "gemini,openai,ollama").split(",") if p.strip()]
    if "ollama" in fallback_cfg and os.getenv("OLLAMA_MODEL"):
        try:
            ollama_base = os.getenv("OLLAMA_API_BASE", OllamaProvider.DEFAULT_BASE_URL).rstrip("/")
            # Fast ping (0.5s timeout) to see if local server is reachable
            with httpx.Client(timeout=0.5) as client:
                resp = client.get(f"{ollama_base}/api/tags")
                if resp.status_code == 200:
                    providers.append(OllamaProvider())
        except Exception:
            pass

    return providers


def get_default_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """Resolve and instantiate the configured LLM provider or FallbackRouter.

    Resolution:
    1. Explicit ``provider_type`` ("gemini", "openai", "ollama") -> Single dedicated provider
    2. Explicit ``AI_PROVIDER`` set to "gemini" / "openai" / "ollama" (single mode)
    3. Multi-provider fallback router (default behavior)
    """
    selected = (provider_type or os.getenv("AI_PROVIDER") or "").strip().lower()

    if selected == "gemini" and not os.getenv("AI_FALLBACK_PROVIDERS"):
        return GeminiProvider()
    if selected == "openai" and not os.getenv("AI_FALLBACK_PROVIDERS"):
        return OpenAIProvider()
    if selected == "ollama" and not os.getenv("AI_FALLBACK_PROVIDERS"):
        return OllamaProvider()

    chain = build_fallback_chain()
    if chain:
        # If user explicitly pinned single AI_PROVIDER, sort that to the front
        if selected in ("gemini", "openai", "ollama"):
            chain.sort(key=lambda p: 0 if selected in type(p).__name__.lower() else 1)
        return FallbackRouter(providers=chain)

    raise AIConfigurationError(
        "No AI provider configured. Please set GEMINI_API_KEY or OPENAI_API_KEY in the environment."
    )

