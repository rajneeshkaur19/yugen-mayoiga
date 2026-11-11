"""State and story action API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.state import (
    StoryActionRequest,
    StoryActionResponse,
    StoryStateRead,
    YugenMeterRead,
)
from backend.app.services.action_pipeline import process_story_action
from backend.app.services.state_service import (
    get_or_create_story_state,
    get_unified_story_state,
)
from backend.app.services.story_service import get_story

router = APIRouter(prefix="/stories/{story_id}", tags=["Story State & Action Engine"])


def _require_user_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.get("/state", response_model=StoryStateRead)
def get_story_runtime_state(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full runtime narrative state (visible emotions, world state, relationships, turn, Yūgen Meter)."""
    _require_user_story(story_id, current_user, db)
    unified = get_unified_story_state(db, story_id, include_hidden=False)
    return unified


@router.post("/choice", response_model=StoryActionResponse)
def submit_story_choice(
    story_id: int,
    action_data: StoryActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a story button choice or action through the integrated deterministic pipeline."""
    _require_user_story(story_id, current_user, db)
    try:
        return process_story_action(
            db=db,
            user_id=current_user.id,
            story_id=story_id,
            choice_id=action_data.choice_id,
            free_text=action_data.free_text,
            active_character_id=action_data.character_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.post("/action", response_model=StoryActionResponse)
def submit_story_action(
    story_id: int,
    action_data: StoryActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a story free-text action or choice through the integrated pipeline."""
    return submit_story_choice(story_id, action_data, db, current_user)


@router.get("/yugen-meter", response_model=YugenMeterRead)
def get_story_yugen_meter(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve current Yūgen Meter value (0-100) reflecting unresolved mystery."""
    _require_user_story(story_id, current_user, db)
    state = get_or_create_story_state(db, story_id)
    val = state.yugen_meter

    if val >= 75:
        desc = "Deep obscurity; profound mysteries linger unrevealed."
    elif val >= 40:
        desc = "Veiled truth; clues have begun to surface."
    else:
        desc = "Clarity dawns; the core mystery has been largely unveiled."

    return {
        "story_id": story_id,
        "yugen_meter": val,
        "mystery_description": desc,
    }
