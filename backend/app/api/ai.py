from fastapi import APIRouter, Depends, status

from backend.app.api.auth import get_current_user
from backend.app.models.user import User
from backend.app.schemas.ai import (
    LocationImageGenerateRequest,
    LocationImageGenerateResponse,
)
from backend.app.services.image_generation_service import (
    generate_custom_location_image,
)

router = APIRouter(prefix="/ai", tags=["AI & Image Generation"])

# NOTE: Narrative, choice, action and interpret endpoints are served by the
# stories router in backend/app/api/state.py at:
#   POST /stories/{story_id}/generate-narrative
#   GET  /stories/{story_id}/dynamic-choices
#   POST /stories/{story_id}/ai-action
#   POST /stories/{story_id}/interpret-action
# The /ai/stories/{story_id}/... mirrors have been removed to avoid duplicate
# route registration.


@router.post(
    "/generate-location-image",
    response_model=LocationImageGenerateResponse,
    status_code=status.HTTP_200_OK,
)
def generate_location_image_endpoint(
    data: LocationImageGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Generates an atmospheric environmental image for a custom location using real AI providers (Gemini/OpenAI)."""
    return generate_custom_location_image(data)
