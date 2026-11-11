"""Endings and Endings Gallery API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.ending import EndingCreate, EndingRead, UserEndingRead
from backend.app.services.ending_engine import (
    create_ending,
    get_user_endings,
    list_story_endings,
)
from backend.app.services.story_service import get_story

router = APIRouter(tags=["Endings & Gallery"])


def _require_user_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.get("/stories/{story_id}/endings", response_model=list[EndingRead])
def get_story_endings(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List defined endings for a story."""
    _require_user_story(story_id, current_user, db)
    return list_story_endings(db, story_id)


@router.post(
    "/stories/{story_id}/endings",
    response_model=EndingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_story_ending(
    story_id: int,
    data: EndingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Define a new conditional ending for a story."""
    _require_user_story(story_id, current_user, db)
    try:
        return create_ending(
            db=db,
            story_id=story_id,
            name=data.name,
            conditions=data.conditions,
            seal_text=data.seal_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/users/me/endings", response_model=list[UserEndingRead])
def get_my_endings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all endings unlocked by the authenticated user across stories."""
    return get_user_endings(db, current_user.id)
