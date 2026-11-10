"""Service operations for choices (story graph edges)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.choice import Choice
from backend.app.models.scene import Scene
from backend.app.schemas.choice import ChoiceCreate, ChoiceUpdate


def _scene_in_story(db: Session, story_id: int, scene_id: int) -> bool:
    """Return True if the scene belongs to the story."""
    return (
        db.scalar(
            select(Scene.id).where(
                Scene.id == scene_id,
                Scene.story_id == story_id,
            )
        )
        is not None
    )


def create_choice(
    db: Session,
    story_id: int,
    scene_id: int,
    data: ChoiceCreate,
) -> Choice:
    """Create a choice on a scene.  Validates next_scene_id same-story membership."""
    if not _scene_in_story(db, story_id, scene_id):
        raise ValueError("Source scene does not belong to this story")

    if data.next_scene_id is not None and not _scene_in_story(
        db, story_id, data.next_scene_id
    ):
        raise ValueError("Destination scene does not belong to this story")

    choice = Choice(
        story_id=story_id,
        scene_id=scene_id,
        choice_text=data.choice_text,
        effects=data.effects,
        condition=data.condition,
        allow_loop=data.allow_loop,
        sort_order=data.sort_order,
        next_scene_id=data.next_scene_id,
    )
    try:
        db.add(choice)
        db.commit()
        db.refresh(choice)
        return choice
    except Exception:
        db.rollback()
        raise


def get_choice(db: Session, story_id: int, scene_id: int, choice_id: int) -> Choice | None:
    return db.scalar(
        select(Choice).where(
            Choice.id == choice_id,
            Choice.scene_id == scene_id,
            Choice.story_id == story_id,
        )
    )


def list_choices(db: Session, story_id: int, scene_id: int) -> list[Choice]:
    return list(
        db.scalars(
            select(Choice)
            .where(
                Choice.scene_id == scene_id,
                Choice.story_id == story_id,
            )
            .order_by(Choice.sort_order, Choice.id)
        ).all()
    )


def update_choice(
    db: Session,
    story_id: int,
    scene_id: int,
    choice_id: int,
    data: ChoiceUpdate,
) -> Choice | None:
    choice = get_choice(db, story_id, scene_id, choice_id)
    if choice is None:
        return None

    if data.next_scene_id is not None and not _scene_in_story(
        db, story_id, data.next_scene_id
    ):
        raise ValueError("Destination scene does not belong to this story")

    updates = data.model_dump(exclude_unset=True)
    try:
        for field, value in updates.items():
            setattr(choice, field, value)
        db.commit()
        db.refresh(choice)
        return choice
    except Exception:
        db.rollback()
        raise


def delete_choice(
    db: Session,
    story_id: int,
    scene_id: int,
    choice_id: int,
) -> bool:
    choice = get_choice(db, story_id, scene_id, choice_id)
    if choice is None:
        return False
    try:
        db.delete(choice)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
