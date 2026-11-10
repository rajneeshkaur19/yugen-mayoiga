"""Memory API endpoints — CRUD for character memories."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.memory import MemoryCreate, MemoryRead, MemoryUpdate
from backend.app.services.memory_service import (
    create_memory,
    delete_memory,
    get_memory,
    list_memories,
    update_memory,
)
from backend.app.services.story_service import get_story

router = APIRouter(
    prefix="/stories/{story_id}/memories",
    tags=["Memories"],
)


def _require_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_new_memory(
    story_id: int,
    data: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a memory for a character in a story."""
    _require_story(story_id, current_user, db)
    try:
        return create_memory(db, story_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=list[MemoryRead])
def list_story_memories(
    story_id: int,
    character_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List memories for a story, optionally filtered by character."""
    _require_story(story_id, current_user, db)
    return list_memories(db, story_id, character_id)


@router.get("/{memory_id}", response_model=MemoryRead)
def get_story_memory(
    story_id: int,
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific memory."""
    _require_story(story_id, current_user, db)
    memory = get_memory(db, story_id, memory_id)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory


@router.patch("/{memory_id}", response_model=MemoryRead)
def edit_memory(
    story_id: int,
    memory_id: int,
    data: MemoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a memory's importance, emotional weight or status."""
    _require_story(story_id, current_user, db)
    memory = update_memory(db, story_id, memory_id, data)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_memory(
    story_id: int,
    memory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a memory."""
    _require_story(story_id, current_user, db)
    deleted = delete_memory(db, story_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
