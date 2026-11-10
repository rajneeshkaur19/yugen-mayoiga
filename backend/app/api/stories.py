from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.story import StoryCreate, StoryRead, StoryUpdate
from backend.app.services.story_service import (
    create_story,
    delete_story,
    get_story,
    get_user_stories,
    update_story,
)

router = APIRouter(prefix="/stories", tags=["Stories"])


@router.post(
    "",
    response_model=StoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_new_story(
    story_data: StoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_story(db, current_user.id, story_data)


@router.get("", response_model=list[StoryRead])
def list_stories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_stories(db, current_user.id)


@router.get("/{story_id}", response_model=StoryRead)
def retrieve_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    story = get_story(db, story_id, current_user.id)

    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    return story


@router.patch("/{story_id}", response_model=StoryRead)
def edit_story(
    story_id: int,
    story_data: StoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    story = update_story(db, story_id, current_user.id, story_data)

    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    return story


@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = delete_story(db, story_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
