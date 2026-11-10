"""Scene API endpoints — CRUD for story scenes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.scene import SceneCreate, SceneRead, SceneUpdate
from backend.app.services.scene_service import (
    create_scene,
    delete_scene,
    get_scene,
    list_scenes,
    update_scene,
)
from backend.app.services.story_service import get_story

router = APIRouter(
    prefix="/stories/{story_id}/scenes",
    tags=["Scenes"],
)


def _require_story(story_id: int, user: User, db: Session):
    story = get_story(db, story_id, user.id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.post("", response_model=SceneRead, status_code=status.HTTP_201_CREATED)
def create_new_scene(
    story_id: int,
    data: SceneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a scene to a story."""
    _require_story(story_id, current_user, db)
    try:
        return create_scene(db, story_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("", response_model=list[SceneRead])
def list_story_scenes(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all scenes in a story, ordered by scene_number."""
    _require_story(story_id, current_user, db)
    return list_scenes(db, story_id)


@router.get("/{scene_id}", response_model=SceneRead)
def get_story_scene(
    story_id: int,
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a scene from a story."""
    _require_story(story_id, current_user, db)
    scene = get_scene(db, story_id, scene_id)
    if scene is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return scene


@router.patch("/{scene_id}", response_model=SceneRead)
def edit_scene(
    story_id: int,
    scene_id: int,
    data: SceneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a scene's fields."""
    _require_story(story_id, current_user, db)
    scene = update_scene(db, story_id, scene_id, data)
    if scene is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return scene


@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_scene(
    story_id: int,
    scene_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a scene from a story."""
    _require_story(story_id, current_user, db)
    deleted = delete_scene(db, story_id, scene_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
