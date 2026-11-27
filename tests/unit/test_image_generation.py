"""Focused isolated unit tests for Yūgen Mayoiga image generation subsystem.

Coverage:
1. Valid Gemini image response (decodes base64, verifies magic bytes, saves to storage, returns URL).
2. Invalid base64 (rejects malformed string, falls through to fallback).
3. Invalid magic bytes (rejects HTML/text payloads masquerading as images).
4. Empty image data (rejects empty or truncated payloads).
5. Gemini timeout and retry with exponential backoff.
6. Gemini 429 rate limit and retry policy.
7. Gemini authentication failure (HTTP 401/403: verifies NO retry, immediate fallback).
8. OpenAI fallback (Gemini fails -> OpenAI succeeds).
9. Both providers failing -> Curated static fallback with accurate provider metadata.
10. Cache hit and duplicate prevention (reusing cached image without invoking provider).
11. API key redaction in error messages and logs.
"""

from __future__ import annotations

import base64
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.app.schemas.ai import LocationImageGenerateRequest
from backend.app.services.image_generation_service import (
    JPEG_MAGIC,
    PNG_MAGIC,
    _generate_with_gemini,
    _generate_with_openai,
    build_cinematic_prompt,
    compute_image_cache_key,
    decode_and_validate_base64,
    generate_custom_location_image,
    sanitize_error,
    validate_image_bytes,
)

# Sample valid 1x1 PNG bytes
VALID_PNG_BYTES = (
    PNG_MAGIC
    + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    + b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    + b"\x00\x00\x00\x00IEND\xaeB`\x82"
)
VALID_PNG_B64 = base64.b64encode(VALID_PNG_BYTES).decode("utf-8")

# Sample valid JPEG header + data
VALID_JPEG_BYTES = JPEG_MAGIC + b"\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"\x00" * 20
VALID_JPEG_B64 = base64.b64encode(VALID_JPEG_BYTES).decode("utf-8")


@pytest.fixture
def temp_storage(monkeypatch):
    """Provide an isolated temporary directory for generated image storage."""
    temp_dir = tempfile.mkdtemp(prefix="yugen_test_images_")
    monkeypatch.setenv("IMAGE_STORAGE_DIR", temp_dir)
    monkeypatch.setattr(
        "backend.app.services.image_generation_service.IMAGE_STORAGE_DIR",
        Path(temp_dir),
    )
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_request() -> LocationImageGenerateRequest:
    return LocationImageGenerateRequest(
        name="Rain-Veiled Pagoda",
        description="A weathered cedar pagoda beside an overgrown lotus pond.",
        atmosphere="Damp cedar, twilight, distant thunder",
        visual_details="Moss on stone lanterns, cold rain ripples on black water",
    )


# ---------------------------------------------------------------------------
# 1. Image Integrity & Magic Byte Validation
# ---------------------------------------------------------------------------


def test_validate_image_bytes_valid_png():
    is_valid, ext = validate_image_bytes(VALID_PNG_BYTES)
    assert is_valid is True
    assert ext == "png"


def test_validate_image_bytes_valid_jpeg():
    is_valid, ext = validate_image_bytes(VALID_JPEG_BYTES)
    assert is_valid is True
    assert ext == "jpeg"


def test_validate_image_bytes_invalid_magic_bytes():
    corrupt_data = b"<html><head><title>500 Internal Error</title></head></html>"
    is_valid, err = validate_image_bytes(corrupt_data)
    assert is_valid is False
    assert "Invalid image data" in err


def test_validate_image_bytes_empty():
    is_valid, err = validate_image_bytes(b"")
    assert is_valid is False
    assert "empty or too small" in err


def test_decode_and_validate_base64_valid():
    img_bytes, ext, err = decode_and_validate_base64(VALID_PNG_B64)
    assert err is None
    assert ext == "png"
    assert img_bytes == VALID_PNG_BYTES


def test_decode_and_validate_base64_invalid_b64():
    img_bytes, ext, err = decode_and_validate_base64("not-valid-base64!@#$%^&*")
    assert img_bytes is None
    assert "Malformed base64" in err


def test_decode_and_validate_base64_valid_b64_corrupt_content():
    # Valid base64 encoding of plain text
    text_b64 = base64.b64encode(b"This is just plain text, not an image.").decode("utf-8")
    img_bytes, ext, err = decode_and_validate_base64(text_b64)
    assert img_bytes is None
    assert "Invalid image data" in err


# ---------------------------------------------------------------------------
# 2. Prompt Construction & Credential Sanitization
# ---------------------------------------------------------------------------


def test_build_cinematic_prompt(sample_request):
    prompt = build_cinematic_prompt(sample_request)
    assert "Rain-Veiled Pagoda" in prompt
    assert "Damp cedar, twilight, distant thunder" in prompt
    assert "Japanese psychological mystery" in prompt
    assert "NO people, NO characters" in prompt


def test_sanitize_error_redacts_api_keys():
    raw_error = "Failed to connect: https://api.com/v1beta/models/img:predict?key=AIzaSyD-1234567890abcdef1234567890abcde"
    sanitized = sanitize_error(raw_error)
    assert "AIzaSyD" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized or "[REDACTED_GEMINI_KEY]" in sanitized


def test_sanitize_error_redacts_bearer_tokens():
    raw_error = "Authorization error: Bearer sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
    sanitized = sanitize_error(raw_error)
    assert "sk-proj-12345" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized or "[REDACTED_OPENAI_KEY]" in sanitized


# ---------------------------------------------------------------------------
# 3. Provider Reliability & Fallbacks
# ---------------------------------------------------------------------------


def test_gemini_image_generation_success(temp_storage, sample_request, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    fake_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": VALID_PNG_B64,
                            }
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        result = generate_custom_location_image(sample_request)
        assert result.success is True
        assert result.provider == "Google Gemini Image"
        assert result.image_url.startswith("/api/generated-images/cache_")
        assert result.image_url.endswith(".png")
        assert mock_post.call_count == 1

        # Confirm saved file on disk is valid
        filename = Path(result.image_url).name
        saved_file = temp_storage / filename
        assert saved_file.exists()
        assert saved_file.read_bytes().startswith(PNG_MAGIC)


def test_gemini_image_generation_corrupt_payload_triggers_fallback(
    temp_storage, sample_request, monkeypatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Gemini returns 200 with non-image text inside inlineData
    corrupt_b64 = base64.b64encode(b"Corrupted non-image bytes string").decode("utf-8")
    fake_response = {
        "candidates": [
            {"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": corrupt_b64}}]}}
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response

    with patch("httpx.Client.post", return_value=mock_resp):
        result = generate_custom_location_image(sample_request)
        # Never report invalid data as success from Gemini; falls through to curated
        assert result.success is True
        assert result.provider == "Curated Environmental Fallback"
        assert result.image_url.startswith("/assets/backgrounds/")


def test_gemini_timeout_with_retry_and_recovery(monkeypatch):
    """Test transient timeout triggers retry before succeeding."""
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"inlineData": {"data": VALID_PNG_B64}}]}}
        ]
    }

    # First attempt: TimeoutException; Second attempt: Success
    mock_post = MagicMock(side_effect=[httpx.TimeoutException("Read timeout"), mock_success])

    with patch("httpx.Client.post", mock_post), patch("time.sleep") as mock_sleep:
        img_bytes, ext, err = _generate_with_gemini(
            prompt="test prompt",
            gemini_key="test-key",
            model="gemini-3.1-flash-lite-image",
            timeout=5.0,
            max_retries=1,
        )
        assert img_bytes == VALID_PNG_BYTES
        assert ext == "png"
        assert err is None
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1


def test_gemini_429_rate_limit_retries_and_fails(monkeypatch):
    """Test HTTP 429 rate limit retries with backoff."""
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.json.return_value = {"error": {"message": "Resource exhausted: rate limit exceeded."}}

    with patch("httpx.Client.post", return_value=mock_429) as mock_post, patch("time.sleep") as mock_sleep:
        img_bytes, ext, err = _generate_with_gemini(
            prompt="test prompt",
            gemini_key="test-key",
            model="gemini-3.1-flash-lite-image",
            timeout=5.0,
            max_retries=2,
        )
        assert img_bytes is None
        assert "exhausted retries (429)" in err
        # initial + 2 retries = 3 calls
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2


def test_gemini_auth_failure_does_not_retry():
    """Test HTTP 401/403 is non-retryable and aborts immediately."""
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.json.return_value = {"error": {"message": "API key not valid."}}

    with patch("httpx.Client.post", return_value=mock_401) as mock_post, patch("time.sleep") as mock_sleep:
        img_bytes, ext, err = _generate_with_gemini(
            prompt="test prompt",
            gemini_key="bad-key",
            model="gemini-3.1-flash-lite-image",
            timeout=5.0,
            max_retries=2,
        )
        assert img_bytes is None
        assert "non-retryable error (401)" in err
        # Must NOT retry auth failure
        assert mock_post.call_count == 1
        assert mock_sleep.call_count == 0


def test_openai_fallback_on_gemini_failure(temp_storage, sample_request, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    mock_gemini_fail = MagicMock()
    mock_gemini_fail.status_code = 503
    mock_gemini_fail.json.return_value = {"error": {"message": "Service unavailable."}}

    mock_openai_success = MagicMock()
    mock_openai_success.status_code = 200
    mock_openai_success.json.return_value = {
        "data": [{"b64_json": VALID_JPEG_B64}]
    }

    def fake_post(url, *args, **kwargs):
        if "generativelanguage.googleapis.com" in url:
            return mock_gemini_fail
        if "api.openai.com" in url:
            return mock_openai_success
        return MagicMock(status_code=404)

    with patch("httpx.Client.post", side_effect=fake_post), patch("time.sleep"):
        result = generate_custom_location_image(sample_request)
        assert result.success is True
        assert result.provider == "OpenAI DALL-E 3"
        assert result.image_url.startswith("/api/generated-images/cache_")
        assert result.image_url.endswith(".jpeg")

        filename = Path(result.image_url).name
        saved_file = temp_storage / filename
        assert saved_file.exists()
        assert saved_file.read_bytes().startswith(JPEG_MAGIC)


def test_both_providers_fail_triggers_curated_fallback(temp_storage, sample_request, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    mock_fail = MagicMock()
    mock_fail.status_code = 500
    mock_fail.json.return_value = {"error": {"message": "Internal error."}}

    with patch("httpx.Client.post", return_value=mock_fail), patch("time.sleep"):
        result = generate_custom_location_image(sample_request)
        assert result.success is True
        assert result.provider == "Curated Environmental Fallback"
        assert result.image_url.startswith("/assets/backgrounds/")
        assert "AI generation unavailable" in result.message


# ---------------------------------------------------------------------------
# 4. Caching & Duplicate Concurrent Generation
# ---------------------------------------------------------------------------


def test_cache_hit_prevents_duplicate_provider_calls(temp_storage, sample_request, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    fake_response = {
        "candidates": [
            {"content": {"parts": [{"inlineData": {"data": VALID_PNG_B64}}]}}
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        # First call: executes provider and writes cache
        res1 = generate_custom_location_image(sample_request)
        assert res1.provider == "Google Gemini Image"
        assert mock_post.call_count == 1

        # Second call with identical request: hits cache directly
        res2 = generate_custom_location_image(sample_request)
        assert res2.provider == "Cache"
        assert res2.image_url == res1.image_url
        assert "retrieved from local cache" in res2.message
        # Provider must NOT have been called a second time
        assert mock_post.call_count == 1


def test_concurrent_duplicate_generation_lock(temp_storage, sample_request, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    call_count = 0
    lock = threading.Lock()

    def slow_post(*args, **kwargs):
        nonlocal call_count
        with lock:
            call_count += 1
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"inlineData": {"data": VALID_PNG_B64}}]}}
            ]
        }
        return mock

    results = []

    def worker():
        res = generate_custom_location_image(sample_request)
        results.append(res)

    with patch("httpx.Client.post", side_effect=slow_post):
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    # Both succeeded and returned the same image URL
    assert len(results) == 2
    assert results[0].image_url == results[1].image_url
    # Due to concurrency lock, provider was called once; second thread hit cache
    assert call_count == 1
