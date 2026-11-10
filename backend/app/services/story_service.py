from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.story import Story
from backend.app.schemas.story import StoryCreate, StoryUpdate


def create_story(
    db: Session,
    user_id: int,
    story_data: StoryCreate,
) -> Story:
    """Create and persist a new story for a user."""

    story = Story(
        user_id=user_id,
        **story_data.model_dump(),
    )

    try:
        db.add(story)
        db.commit()
        db.refresh(story)
        return story
    except Exception:
        db.rollback()
        raise


def get_story(
    db: Session,
    story_id: int,
    user_id: int,
) -> Story | None:
    """Retrieve a story only if it belongs to the given user."""

    statement = select(Story).where(
        Story.id == story_id,
        Story.user_id == user_id,
    )

    return db.scalar(statement)


def get_user_stories(
    db: Session,
    user_id: int,
) -> list[Story]:
    """Retrieve all stories belonging to a user."""

    statement = (
        select(Story)
        .where(Story.user_id == user_id)
        .order_by(Story.created_at.desc())
    )

    return list(db.scalars(statement).all())


def update_story(
    db: Session,
    story_id: int,
    user_id: int,
    story_data: StoryUpdate,
) -> Story | None:
    """Update a user's story without modifying another user's data."""

    story = get_story(db, story_id, user_id)

    if story is None:
        return None

    updates = story_data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    if not updates:
        return story

    try:
        for field, value in updates.items():
            setattr(story, field, value)

        db.commit()
        db.refresh(story)
        return story
    except Exception:
        db.rollback()
        raise


def delete_story(
    db: Session,
    story_id: int,
    user_id: int,
) -> bool:
    """Delete a story only if it belongs to the given user."""

    story = get_story(db, story_id, user_id)

    if story is None:
        return False

    try:
        db.delete(story)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
