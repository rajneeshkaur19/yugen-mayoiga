"""Choice API endpoints — CRUD for scene choices (story graph edges)."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.choice import ChoiceCreate, ChoiceRead, ChoiceUpdate
from backend.app.services.choice_service import (
    create_choice,
    delete_choice,
    get_choice,
    list_choices,
    update_choice,
)
from backend.app.services.story_service import get_story

router = APIRouter(
    prefix="/stories/{story_id}/scenes/{scene_id}/choices",
    tags=["Choices"],
)


def _require_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.post("", response_model=ChoiceRead, status_code=status.HTTP_201_CREATED)
def create_new_choice(
    story_id: int,
    scene_id: int,
    data: ChoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a choice to a scene."""
    _require_story(story_id, current_user, db)
    try:
        return create_choice(db, story_id, scene_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=list[ChoiceRead])
def list_scene_choices(
    story_id: int,
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all choices for a scene."""
    _require_story(story_id, current_user, db)
    return list_choices(db, story_id, scene_id)


@router.get("/{choice_id}", response_model=ChoiceRead)
def get_scene_choice(
    story_id: int,
    scene_id: int,
    choice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific choice."""
    _require_story(story_id, current_user, db)
    choice = get_choice(db, story_id, scene_id, choice_id)
    if choice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Choice not found")
    return choice


@router.patch("/{choice_id}", response_model=ChoiceRead)
def edit_choice(
    story_id: int,
    scene_id: int,
    choice_id: int,
    data: ChoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a choice's text, effects or destination."""
    _require_story(story_id, current_user, db)
    try:
        choice = update_choice(db, story_id, scene_id, choice_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if choice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Choice not found")
    return choice


@router.delete("/{choice_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_choice(
    story_id: int,
    scene_id: int,
    choice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a choice."""
    _require_story(story_id, current_user, db)
    deleted = delete_choice(db, story_id, scene_id, choice_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Choice not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
