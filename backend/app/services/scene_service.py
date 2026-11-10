"""Service operations for scene management."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.scene import Scene
from backend.app.schemas.scene import SceneCreate, SceneUpdate


def _get_story_scene(db: Session, story_id: int, scene_id: int) -> Scene | None:
    return db.scalar(
        select(Scene).where(
            Scene.id == scene_id,
            Scene.story_id == story_id,
        )
    )


def create_scene(db: Session, story_id: int, data: SceneCreate) -> Scene:
    scene = Scene(
        story_id=story_id,
        scene_number=data.scene_number,
        content=data.content,
        location=data.location,
        mood=data.mood,
        haiku=data.haiku,
        is_ending=data.is_ending,
    )
    try:
        db.add(scene)
        db.commit()
        db.refresh(scene)
        return scene
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A scene with this scene_number already exists in the story"
        ) from exc
    except Exception:
        db.rollback()
        raise


def get_scene(db: Session, story_id: int, scene_id: int) -> Scene | None:
    return _get_story_scene(db, story_id, scene_id)


def list_scenes(db: Session, story_id: int) -> list[Scene]:
    return list(
        db.scalars(
            select(Scene)
            .where(Scene.story_id == story_id)
            .order_by(Scene.scene_number)
        ).all()
    )


def update_scene(
    db: Session,
    story_id: int,
    scene_id: int,
    data: SceneUpdate,
) -> Scene | None:
    scene = _get_story_scene(db, story_id, scene_id)
    if scene is None:
        return None

    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return scene

    try:
        for field, value in updates.items():
            setattr(scene, field, value)
        db.commit()
        db.refresh(scene)
        return scene
    except Exception:
        db.rollback()
        raise


def delete_scene(db: Session, story_id: int, scene_id: int) -> bool:
    scene = _get_story_scene(db, story_id, scene_id)
    if scene is None:
        return False
    try:
        db.delete(scene)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
