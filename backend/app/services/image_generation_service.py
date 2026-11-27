"""Robust and validated image generation service for Yūgen Mayoiga.

Responsibilities:
1. Build style-controlled cinematic prompts for Japanese aesthetic mystery realms.
2. Validate non-empty image bytes and verify PNG/JPEG/WEBP magic bytes.
3. Reject corrupt, malformed, or non-image payloads before reporting success.
4. Cache valid images on disk keyed by SHA-256 of normalized prompt and settings.
5. Prevent duplicate concurrent generation for identical cache keys via per-key locks.
6. Primary provider: Google Gemini (gemini-3.1-flash-lite-image) with bounded retries and backoff.
7. Secondary provider: OpenAI DALL-E 3 with bounded retries for transient errors.
8. Tertiary fail-safe: Curated high-resolution static sanctuary artwork.
9. Configurable storage directory without writing to frontend source code directories.
10. Scrub credentials (API keys, bearer tokens) from error strings and logs.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

from backend.app.schemas.ai import (
    LocationImageGenerateRequest,
    LocationImageGenerateResponse,
)

# ---------------------------------------------------------------------------
# Path & Environment Configuration
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

DEFAULT_STORAGE_DIR = BACKEND_DIR / "storage" / "generated-images"
IMAGE_STORAGE_DIR = Path(
    os.getenv("IMAGE_STORAGE_DIR", str(DEFAULT_STORAGE_DIR))
).resolve()

# Magic byte signatures for image validation
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
WEBP_MAGIC_RIFF = b"RIFF"
WEBP_MAGIC_WEBP = b"WEBP"

# Concurrency locks per cache key to prevent duplicate simultaneous generation
_CACHE_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


# ---------------------------------------------------------------------------
# Image Integrity & Validation
# ---------------------------------------------------------------------------


def validate_image_bytes(data: bytes) -> Tuple[bool, str]:
    """Validate non-empty image bytes and verify magic byte signatures.

    Returns (is_valid, extension_or_error_message).
    """
    if not data or len(data) < 16:
        return False, "Image payload is empty or too small (< 16 bytes)."
    if data.startswith(PNG_MAGIC):
        return True, "png"
    if data.startswith(JPEG_MAGIC):
        return True, "jpeg"
    if data.startswith(WEBP_MAGIC_RIFF) and len(data) >= 12 and data[8:12] == WEBP_MAGIC_WEBP:
        return True, "webp"
    return False, "Invalid image data: corrupt or unrecognized magic bytes (not PNG, JPEG, or WEBP)."


def decode_and_validate_base64(raw_b64: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """Safely decode base64 string and validate image magic bytes.

    Returns (image_bytes, extension, error_message).
    """
    if not raw_b64 or not str(raw_b64).strip():
        return None, None, "Base64 image data is empty or whitespace."
    try:
        data = base64.b64decode(str(raw_b64).strip(), validate=True)
    except Exception as exc:
        return None, None, f"Malformed base64 image data: {exc}"

    is_valid, ext_or_err = validate_image_bytes(data)
    if not is_valid:
        return None, None, ext_or_err
    return data, ext_or_err, None


def sanitize_error(text: Any) -> str:
    """Scrub sensitive query parameters and bearer tokens from error strings."""
    s = str(text)
    s = re.sub(r"([?&]key=)[^&\s'\"]+", r"\1[REDACTED_API_KEY]", s)
    s = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED_TOKEN]", s)
    s = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_GEMINI_KEY]", s)
    s = re.sub(r"sk-[A-Za-z0-9]{20,}", "[REDACTED_OPENAI_KEY]", s)
    return s


# ---------------------------------------------------------------------------
# Caching & Concurrency Control
# ---------------------------------------------------------------------------


def compute_image_cache_key(prompt: str, settings: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of normalized prompt and settings."""
    normalized_prompt = " ".join(prompt.strip().lower().split())
    sorted_settings = {k: v for k, v in sorted(settings.items()) if v is not None}
    payload = json.dumps({"prompt": normalized_prompt, "settings": sorted_settings}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached_image(cache_key: str, storage_dir: Path) -> Optional[Tuple[Path, str]]:
    """Look for an existing valid cached image matching cache_key.

    Returns (file_path, relative_url) or None.
    """
    if not storage_dir.exists():
        return None
    for ext in ("png", "jpeg", "webp"):
        candidate = storage_dir / f"cache_{cache_key}.{ext}"
        if candidate.exists() and candidate.is_file():
            try:
                data = candidate.read_bytes()
                is_valid, _ = validate_image_bytes(data)
                if is_valid:
                    return candidate, f"/api/generated-images/cache_{cache_key}.{ext}"
                # Corrupt cache file, prune it
                candidate.unlink(missing_ok=True)
            except Exception:
                pass
    return None


def save_image_to_storage(data: bytes, ext: str, cache_key: str, storage_dir: Path) -> Tuple[Path, str]:
    """Atomically save valid image data into storage directory with cache key filename."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"cache_{cache_key}.{ext}"
    file_path = storage_dir / filename
    temp_path = storage_dir / f".tmp_{uuid.uuid4().hex[:8]}_{filename}"
    temp_path.write_bytes(data)
    temp_path.replace(file_path)
    return file_path, f"/api/generated-images/{filename}"


def _get_cache_lock(cache_key: str) -> threading.Lock:
    """Retrieve or create a thread lock for the given cache key."""
    with _LOCKS_GUARD:
        if cache_key not in _CACHE_LOCKS:
            if len(_CACHE_LOCKS) > 1000:
                _CACHE_LOCKS.clear()
            _CACHE_LOCKS[cache_key] = threading.Lock()
        return _CACHE_LOCKS[cache_key]


# ---------------------------------------------------------------------------
# Prompt Construction & Static Fallback
# ---------------------------------------------------------------------------


def build_cinematic_prompt(data: LocationImageGenerateRequest) -> str:
    """Constructs a style-controlled prompt adhering to the Yūgen Mayoiga aesthetic."""
    prompt_parts = [
        f"A cinematic environmental concept art film still of {data.name}.",
        f"Description: {data.description}.",
        f"Atmosphere: {data.atmosphere}.",
    ]
    if data.visual_details:
        prompt_parts.append(f"Visual details: {data.visual_details}.")

    # Style anchors enforcing dark Japanese mystery concept art aesthetic
    prompt_parts.append(
        "Style: Japanese psychological mystery, dark atmospheric nocturnal setting, "
        "dramatic directional lighting, warm amber lantern glow, deep rich blacks, "
        "cold silver moonlight, subtle mist and texture, sharp environmental details, "
        "widescreen 16:9 composition. NO people, NO characters, NO text, NO anime girls, NO faces."
    )
    return " ".join(prompt_parts)


def _select_curated_fallback_by_keywords(combined: str) -> str:
    """Selects an evocative high-resolution environmental artwork from the curated asset library based on keywords."""
    text = combined.lower()
    if any(k in text for k in ["station", "platform", "railway", "train"]):
        return "/assets/backgrounds/landing-hero.png"
    if any(k in text for k in ["shrine", "torii", "temple", "gate", "sacred", "rain"]):
        return "/assets/backgrounds/rain-soaked-shrine.png"
    if any(k in text for k in ["village", "street", "town", "machiya", "alley", "crossing"]):
        return "/assets/backgrounds/village-street-night.png"
    if any(k in text for k in ["bamboo", "grove", "forest", "woods"]):
        return "/assets/story-covers/cover-bamboo-forest.png"
    if any(k in text for k in ["engawa", "veranda", "corridor", "hall", "moon", "paper screen", "room", "chamber"]):
        return "/assets/backgrounds/midnight-engawa.png"
    return "/assets/backgrounds/mayoiga-estate-night.png"


def _select_curated_character_fallback(name: str, role: str) -> str:
    """Selects a curated visual asset for a character portrait."""
    combined = f"{name} {role}".lower()
    if any(k in combined for k in ["shrine", "maiden", "miko", "chiyo", "guardian", "spirit"]):
        return "/assets/backgrounds/rain-soaked-shrine.png"
    if any(k in combined for k in ["keeper", "ren", "stationmaster", "watchman", "jin"]):
        return "/assets/backgrounds/midnight-engawa.png"
    if any(k in combined for k in ["archivist", "aoi", "scholar", "weaver", "sachi", "shiori"]):
        return "/assets/story-covers/cover-midnight-letters.png"
    if any(k in combined for k in ["bamboo", "hermit", "takeo", "pilgrim", "kaito"]):
        return "/assets/story-covers/cover-bamboo-forest.png"
    return "/assets/backgrounds/mayoiga-estate-night.png"


def _select_curated_fallback_background(data: LocationImageGenerateRequest) -> str:
    """Selects an evocative high-resolution environmental artwork from the curated asset library."""
    combined = f"{data.name} {data.atmosphere} {data.description} {data.visual_details or ''}"
    return _select_curated_fallback_by_keywords(combined)


def build_scene_prompt(
    location: str,
    content: str = "",
    mood: Optional[str] = None,
    season: Optional[str] = None,
    tone: Optional[str] = None,
    genre: Optional[str] = None,
) -> str:
    """Constructs a style-controlled environmental prompt for a story scene."""
    clean_desc = content.strip().replace("\n", " ")[:300]
    prompt_parts = [
        f"A cinematic environmental concept art film still of {location}.",
    ]
    if clean_desc:
        prompt_parts.append(f"Scene setting: {clean_desc}.")
    if mood:
        prompt_parts.append(f"Atmosphere and mood: {mood}.")
    if season:
        prompt_parts.append(f"Season and weather: {season}.")
    if tone:
        prompt_parts.append(f"Narrative tone: {tone}.")
    if genre:
        prompt_parts.append(f"Story genre: {genre}.")

    prompt_parts.append(
        "Style: Japanese psychological mystery, dark atmospheric nocturnal setting, "
        "dramatic directional lighting, warm amber lantern glow, deep rich blacks, "
        "cold silver moonlight, subtle mist and texture, sharp environmental details, "
        "widescreen 16:9 composition. NO people, NO characters, NO text, NO anime girls, NO faces."
    )
    return " ".join(prompt_parts)


# ---------------------------------------------------------------------------
# Provider Execution with Retries & Exponential Backoff
# ---------------------------------------------------------------------------


def _generate_with_gemini(
    prompt: str,
    gemini_key: str,
    model: str,
    timeout: float,
    max_retries: int,
) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """Attempt image generation with Google Gemini.

    Returns (image_bytes, extension, error_summary).
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
        },
    }

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(url, json=payload)

            if res.status_code == 200:
                result_json = res.json()
                candidates = result_json.get("candidates", [])
                if not candidates:
                    return None, None, "Gemini returned 200 but candidate list is empty."
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    return None, None, "Gemini returned 200 but candidate content parts are empty."

                raw_b64 = None
                for part in parts:
                    inline_data = part.get("inlineData")
                    if inline_data and "data" in inline_data:
                        raw_b64 = inline_data["data"]
                        break

                if not raw_b64:
                    return None, None, "Gemini returned 200 but no inlineData image payload was found."

                img_bytes, ext, err = decode_and_validate_base64(raw_b64)
                if img_bytes is None:
                    return None, None, f"Gemini payload validation failed: {err}"
                return img_bytes, ext, None

            status = res.status_code
            try:
                error_body = res.json()
            except Exception:
                error_body = {}
            raw_err = error_body.get("error", {}).get("message", f"HTTP {status}")
            clean_err = sanitize_error(raw_err)

            # Permanent non-retryable client errors (auth, bad request, model not found)
            if status in (400, 401, 403, 404):
                return None, None, f"Gemini non-retryable error ({status}): {clean_err}"

            # Transient errors: 429 rate limit or 5xx server error
            if attempt < max_retries:
                time.sleep(0.5 * (2**attempt))
                continue
            return None, None, f"Gemini exhausted retries ({status}): {clean_err}"

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt < max_retries:
                time.sleep(0.5 * (2**attempt))
                continue
            return None, None, f"Gemini connection error after retries: {sanitize_error(exc)}"
        except Exception as exc:
            return None, None, f"Gemini unexpected error: {sanitize_error(exc)}"

    return None, None, "Gemini generation failed."


def _generate_with_openai(
    prompt: str,
    openai_key: str,
    model: str,
    timeout: float,
    max_retries: int,
) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
    """Attempt image generation with OpenAI DALL-E.

    Returns (image_bytes, extension, error_summary).
    """
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": "1792x1024",
        "response_format": "b64_json",
    }

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(url, json=payload, headers=headers)

            if res.status_code == 200:
                result_json = res.json()
                data_list = result_json.get("data", [])
                if not data_list or "b64_json" not in data_list[0]:
                    return None, None, "OpenAI returned 200 but data list has no b64_json."

                raw_b64 = data_list[0]["b64_json"]
                img_bytes, ext, err = decode_and_validate_base64(raw_b64)
                if img_bytes is None:
                    return None, None, f"OpenAI payload validation failed: {err}"
                return img_bytes, ext, None

            status = res.status_code
            try:
                error_body = res.json()
            except Exception:
                error_body = {}
            raw_err = error_body.get("error", {}).get("message", f"HTTP {status}")
            clean_err = sanitize_error(raw_err)

            if status in (400, 401, 403, 404):
                return None, None, f"OpenAI non-retryable error ({status}): {clean_err}"

            if attempt < max_retries:
                time.sleep(0.5 * (2**attempt))
                continue
            return None, None, f"OpenAI exhausted retries ({status}): {clean_err}"

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt < max_retries:
                time.sleep(0.5 * (2**attempt))
                continue
            return None, None, f"OpenAI connection error after retries: {sanitize_error(exc)}"
        except Exception as exc:
            return None, None, f"OpenAI unexpected error: {sanitize_error(exc)}"

    return None, None, "OpenAI generation failed."


# ---------------------------------------------------------------------------
# Public Orchestrator
# ---------------------------------------------------------------------------


def _orchestrate_generation(
    prompt: str,
    fallback_keywords: str,
    context_label: str = "Location",
) -> LocationImageGenerateResponse:
    """Core orchestration pipeline: cache check -> lock -> Gemini -> OpenAI -> Curated Fallback."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    gemini_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image")
    gemini_timeout = float(os.getenv("GEMINI_IMAGE_TIMEOUT", "20.0"))

    openai_model = os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")
    openai_timeout = float(os.getenv("OPENAI_IMAGE_TIMEOUT", "25.0"))

    max_retries = int(os.getenv("IMAGE_GEN_MAX_RETRIES", "2"))

    settings = {
        "gemini_model": gemini_model,
        "openai_model": openai_model,
        "aspect_ratio": "16:9",
    }
    cache_key = compute_image_cache_key(prompt, settings)

    # 1. Check cache & lock duplicate concurrent generation
    lock = _get_cache_lock(cache_key)
    with lock:
        cached = get_cached_image(cache_key, IMAGE_STORAGE_DIR)
        if cached is not None:
            _, rel_url = cached
            return LocationImageGenerateResponse(
                success=True,
                image_url=rel_url,
                prompt_used=prompt,
                provider="Cache",
                source_type="cached",
                is_fallback=False,
                quota_exhausted=False,
                missing_config=None,
                message=f"{context_label} image retrieved from local cache.",
            )

        errors_encountered: List[str] = []

        # 2. Primary Provider: Google Gemini
        if gemini_key:
            img_bytes, ext, err = _generate_with_gemini(
                prompt=prompt,
                gemini_key=gemini_key,
                model=gemini_model,
                timeout=gemini_timeout,
                max_retries=max_retries,
            )
            if img_bytes is not None and ext is not None:
                _, rel_url = save_image_to_storage(img_bytes, ext, cache_key, IMAGE_STORAGE_DIR)
                return LocationImageGenerateResponse(
                    success=True,
                    image_url=rel_url,
                    prompt_used=prompt,
                    provider="Google Gemini Image",
                    source_type="ai_generated",
                    is_fallback=False,
                    quota_exhausted=False,
                    missing_config=None,
                    message=f"{context_label} image generated successfully with Google Gemini Image.",
                )
            if err:
                errors_encountered.append(err)
        else:
            errors_encountered.append("GEMINI_API_KEY not configured")

        # 3. Secondary Fallback Provider: OpenAI DALL-E
        if openai_key:
            img_bytes, ext, err = _generate_with_openai(
                prompt=prompt,
                openai_key=openai_key,
                model=openai_model,
                timeout=openai_timeout,
                max_retries=max_retries,
            )
            if img_bytes is not None and ext is not None:
                _, rel_url = save_image_to_storage(img_bytes, ext, cache_key, IMAGE_STORAGE_DIR)
                return LocationImageGenerateResponse(
                    success=True,
                    image_url=rel_url,
                    prompt_used=prompt,
                    provider="OpenAI DALL-E 3",
                    source_type="ai_generated",
                    is_fallback=False,
                    quota_exhausted=False,
                    missing_config=None,
                    message=f"{context_label} image generated successfully with OpenAI DALL-E 3.",
                )
            if err:
                errors_encountered.append(err)
        else:
            errors_encountered.append("OPENAI_API_KEY not configured")

        # 4. Tertiary Fail-Safe: Curated Local Asset
        if fallback_keywords.startswith("character "):
            parts = fallback_keywords.split(" ", 2)
            char_name = parts[1] if len(parts) > 1 else ""
            char_role = parts[2] if len(parts) > 2 else ""
            fallback_url = _select_curated_character_fallback(char_name, char_role)
        else:
            fallback_url = _select_curated_fallback_by_keywords(fallback_keywords)
        error_summary = " | ".join(errors_encountered) if errors_encountered else "Provider credentials unavailable"
        quota_exhausted = any(
            token in error_summary.lower()
            for token in ("429", "quota", "credits", "billing", "rate limit")
        )

        return LocationImageGenerateResponse(
            success=True,
            image_url=fallback_url,
            prompt_used=prompt,
            provider="Curated Environmental Fallback",
            source_type="curated_fallback",
            is_fallback=True,
            quota_exhausted=quota_exhausted,
            missing_config=None,
            message=(
                f"Curated environmental artwork matched to your sanctuary atmosphere. "
                f"(AI generation unavailable: {error_summary[:160]})"
            ),
        )


def generate_custom_location_image(
    data: LocationImageGenerateRequest,
) -> LocationImageGenerateResponse:
    """Generates an environmental image via Gemini Image or OpenAI DALL-E, with caching and curated fallback."""
    prompt = build_cinematic_prompt(data)
    fallback_keywords = f"{data.name} {data.atmosphere} {data.description} {data.visual_details or ''}"
    return _orchestrate_generation(prompt, fallback_keywords, context_label="Location")


def generate_scene_image(
    location: str,
    content: str = "",
    mood: Optional[str] = None,
    season: Optional[str] = None,
    tone: Optional[str] = None,
    genre: Optional[str] = None,
) -> LocationImageGenerateResponse:
    """Generates a scene environmental artwork via Gemini/OpenAI/Curated fallback with caching."""
    prompt = build_scene_prompt(
        location=location,
        content=content,
        mood=mood,
        season=season,
        tone=tone,
        genre=genre,
    )
    fallback_keywords = f"{location} {mood or ''} {season or ''} {content[:100]}"
    return _orchestrate_generation(prompt, fallback_keywords, context_label="Scene")


def build_character_portrait_prompt(
    name: str,
    role: str,
    visual_description: Optional[str] = None,
    visual_prompt_anchor: Optional[str] = None,
    background: Optional[str] = None,
    tone: Optional[str] = None,
    genre: Optional[str] = None,
) -> str:
    """Constructs a style-controlled prompt for character portraits adhering to Japanese gothic / ukiyo-e aesthetics."""
    prompt_parts = [
        f"A masterwork cinematic character portrait bust of {name}, the {role}.",
    ]
    if visual_prompt_anchor:
        prompt_parts.append(f"Visual identity: {visual_prompt_anchor}.")
    if visual_description:
        prompt_parts.append(f"Physical appearance and garments: {visual_description}.")
    elif background:
        clean_bg = background.strip().replace("\n", " ")[:150]
        prompt_parts.append(f"Background nuance: {clean_bg}.")
    if tone:
        prompt_parts.append(f"Atmospheric mood: {tone}.")
    if genre:
        prompt_parts.append(f"Story genre: {genre}.")

    prompt_parts.append(
        "Style: Atmospheric Japanese gothic mystery portrait, dark anime and ukiyo-e ink-wash influences, "
        "refined woodblock linework, chiaroscuro rim lighting, warm amber lantern glow against deep indigo shadows, "
        "textured washi paper finish, solo bust portrait, expressive eyes, hauntingly calm countenance, "
        "8k resolution, cinematic framing, no text, no watermark, no duplicate faces, clean composition."
    )
    return " ".join(prompt_parts)


def generate_character_portrait(
    name: str,
    role: str,
    visual_description: Optional[str] = None,
    visual_prompt_anchor: Optional[str] = None,
    background: Optional[str] = None,
    tone: Optional[str] = None,
    genre: Optional[str] = None,
) -> LocationImageGenerateResponse:
    """Generates a character portrait via Gemini Image/OpenAI DALL-E, with caching and curated fallback."""
    prompt = build_character_portrait_prompt(
        name=name,
        role=role,
        visual_description=visual_description,
        visual_prompt_anchor=visual_prompt_anchor,
        background=background,
        tone=tone,
        genre=genre,
    )
    fallback_keywords = f"character {name} {role}"
    return _orchestrate_generation(prompt, fallback_keywords, context_label="Character Portrait")
