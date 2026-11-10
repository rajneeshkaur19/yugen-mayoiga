"""Character API endpoints — CRUD for characters and their traits."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.character import (
    CharacterCreate,
    CharacterRead,
    CharacterTraitsCreate,
    CharacterTraitsRead,
    CharacterUpdate,
)
from backend.app.services.character_service import (
    create_character,
    delete_character,
    get_character,
    get_traits,
    list_characters,
    update_character,
    upsert_traits,
)
from backend.app.services.story_service import get_story

router = APIRouter(
    prefix="/stories/{story_id}/characters",
    tags=["Characters"],
)


def _require_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.post("", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
def create_new_character(
    story_id: int,
    data: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a character to a story."""
    _require_story(story_id, current_user, db)
    try:
        return create_character(db, story_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("", response_model=list[CharacterRead])
def list_story_characters(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all characters in a story."""
    _require_story(story_id, current_user, db)
    return list_characters(db, story_id)


@router.get("/{character_id}", response_model=CharacterRead)
def get_story_character(
    story_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a character from a story."""
    _require_story(story_id, current_user, db)
    char = get_character(db, story_id, character_id)
    if char is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return char


@router.patch("/{character_id}", response_model=CharacterRead)
def edit_character(
    story_id: int,
    character_id: int,
    data: CharacterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a character's fields."""
    _require_story(story_id, current_user, db)
    try:
        char = update_character(db, story_id, character_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if char is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return char


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_character(
    story_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a character from a story."""
    _require_story(story_id, current_user, db)
    deleted = delete_character(db, story_id, character_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{character_id}/traits", response_model=CharacterTraitsRead)
def get_character_traits(
    story_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve personality traits for a character."""
    _require_story(story_id, current_user, db)
    char = get_character(db, story_id, character_id)
    if char is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    traits = get_traits(db, character_id)
    if traits is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Traits not set")
    return traits


@router.put("/{character_id}/traits", response_model=CharacterTraitsRead)
def set_character_traits(
    story_id: int,
    character_id: int,
    data: CharacterTraitsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or replace personality traits for a character."""
    _require_story(story_id, current_user, db)
    traits = upsert_traits(db, story_id, character_id, data.model_dump())
    if traits is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    return traits
