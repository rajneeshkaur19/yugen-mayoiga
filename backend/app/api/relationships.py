"""Relationship API endpoints — directed character-to-character dynamics."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.relationship import (
    RelationshipCreate,
    RelationshipRead,
    RelationshipUpdate,
)
from backend.app.services.relationship_engine import (
    create_or_update_relationship,
    get_relationship,
    list_story_relationships,
)
from backend.app.services.story_service import get_story

router = APIRouter(prefix="/stories/{story_id}/relationships", tags=["Relationships"])


def _require_user_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.get("", response_model=list[RelationshipRead])
def list_relationships(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all directed relationships in a story."""
    _require_user_story(story_id, current_user, db)
    return list_story_relationships(db, story_id)


@router.post("", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED)
def create_relationship(
    story_id: int,
    data: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or set a directed relationship."""
    _require_user_story(story_id, current_user, db)
    try:
        rel = create_or_update_relationship(
            db=db,
            story_id=story_id,
            from_character=data.from_character,
            to_character=data.to_character,
            values=data.model_dump(),
        )
        db.commit()
        db.refresh(rel)
        return rel
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
