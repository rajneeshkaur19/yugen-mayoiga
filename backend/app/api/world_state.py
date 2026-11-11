"""World State API endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.world_state import WorldStateUpdate
from backend.app.services.story_service import get_story
from backend.app.services.world_state_engine import (
    get_all_world_vars,
    set_world_var,
)

router = APIRouter(prefix="/stories/{story_id}/world-state", tags=["World State"])


def _require_user_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.get("", response_model=dict[str, Any])
def get_world_state(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all key-value world variables for a story."""
    _require_user_story(story_id, current_user, db)
    return get_all_world_vars(db, story_id)


@router.put("", response_model=dict[str, Any])
def put_world_var(
    story_id: int,
    data: WorldStateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set or update a world variable."""
    _require_user_story(story_id, current_user, db)
    set_world_var(db, story_id, data.key, data.value)
    db.commit()
    return get_all_world_vars(db, story_id)
