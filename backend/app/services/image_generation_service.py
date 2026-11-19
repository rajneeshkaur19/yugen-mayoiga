import base64
import os
import time
import uuid
from pathlib import Path
from typing import Tuple, Optional

import httpx
from dotenv import load_dotenv
from backend.app.schemas.ai import LocationImageGenerateRequest, LocationImageGenerateResponse

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

FRONTEND_PUBLIC_DIR = Path(__file__).resolve().parents[3] / "frontend" / "public"
CUSTOM_LOCATIONS_DIR = FRONTEND_PUBLIC_DIR / "assets" / "custom-locations"


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


def generate_custom_location_image(
    data: LocationImageGenerateRequest,
) -> LocationImageGenerateResponse:
    """Generates an image via Gemini Imagen or OpenAI DALL-E 3, or returns exact missing credentials."""
    prompt = build_cinematic_prompt(data)

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not gemini_key and not openai_key:
        return LocationImageGenerateResponse(
            success=False,
            image_url=None,
            prompt_used=prompt,
            provider=None,
            missing_config="GEMINI_API_KEY or OPENAI_API_KEY",
            message=(
                "AI Image Generation provider is not configured. "
                "Please add GEMINI_API_KEY (Google Imagen) or OPENAI_API_KEY (DALL-E 3) to backend/.env."
            ),
        )

    CUSTOM_LOCATIONS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"custom_loc_{uuid.uuid4().hex[:12]}_{int(time.time())}.png"
    file_path = CUSTOM_LOCATIONS_DIR / filename
    relative_url = f"/assets/custom-locations/{filename}"

    # Try Google Imagen 3 if GEMINI_API_KEY is available
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={gemini_key}"
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9",
                    "outputMimeType": "image/png",
                },
            }
            with httpx.Client(timeout=45.0) as client:
                res = client.post(url, json=payload)

            if res.status_code == 200:
                result_json = res.json()
                predictions = result_json.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    img_data = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                    file_path.write_bytes(img_data)
                    return LocationImageGenerateResponse(
                        success=True,
                        image_url=relative_url,
                        prompt_used=prompt,
                        provider="Google Imagen 3",
                        missing_config=None,
                        message="Location image generated successfully with Google Imagen 3.",
                    )
            # If not 200, capture error message
            error_data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
            err_msg = error_data.get("error", {}).get("message", f"HTTP {res.status_code}")
            return LocationImageGenerateResponse(
                success=False,
                image_url=None,
                prompt_used=prompt,
                provider="Google Imagen 3",
                missing_config=None,
                message=f"Google Imagen API error: {err_msg}",
            )
        except Exception as exc:
            return LocationImageGenerateResponse(
                success=False,
                image_url=None,
                prompt_used=prompt,
                provider="Google Imagen 3",
                missing_config=None,
                message=f"Failed to connect to Google Imagen API: {str(exc)}",
            )

    # Try OpenAI DALL-E 3 if OPENAI_API_KEY is available
    if openai_key:
        try:
            url = "https://api.openai.com/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1792x1024",
                "response_format": "b64_json",
            }
            with httpx.Client(timeout=45.0) as client:
                res = client.post(url, json=payload, headers=headers)

            if res.status_code == 200:
                result_json = res.json()
                data_list = result_json.get("data", [])
                if data_list and "b64_json" in data_list[0]:
                    img_data = base64.b64decode(data_list[0]["b64_json"])
                    file_path.write_bytes(img_data)
                    return LocationImageGenerateResponse(
                        success=True,
                        image_url=relative_url,
                        prompt_used=prompt,
                        provider="OpenAI DALL-E 3",
                        missing_config=None,
                        message="Location image generated successfully with OpenAI DALL-E 3.",
                    )
            error_data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
            err_msg = error_data.get("error", {}).get("message", f"HTTP {res.status_code}")
            return LocationImageGenerateResponse(
                success=False,
                image_url=None,
                prompt_used=prompt,
                provider="OpenAI DALL-E 3",
                missing_config=None,
                message=f"OpenAI DALL-E 3 API error: {err_msg}",
            )
        except Exception as exc:
            return LocationImageGenerateResponse(
                success=False,
                image_url=None,
                prompt_used=prompt,
                provider="OpenAI DALL-E 3",
                missing_config=None,
                message=f"Failed to connect to OpenAI API: {str(exc)}",
            )

    return LocationImageGenerateResponse(
        success=False,
        image_url=None,
        prompt_used=prompt,
        provider=None,
        missing_config="GEMINI_API_KEY or OPENAI_API_KEY",
        message="No valid AI image provider configured.",
    )
