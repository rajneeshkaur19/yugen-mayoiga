from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.models.scene import Scene
from backend.app.models.story import Story
from backend.app.models.story_state import StoryState
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

    statement = (
        select(Story, Scene.is_ending)
        .outerjoin(StoryState, StoryState.story_id == Story.id)
        .outerjoin(Scene, Scene.id == StoryState.current_scene_id)
        .where(
            Story.id == story_id,
            Story.user_id == user_id,
        )
    )

    row = db.execute(statement).first()
    if row is None:
        return None

    story, is_ending = row
    if is_ending and story.status == "active":
        story.status = "completed"
    return story


def get_user_stories(
    db: Session,
    user_id: int,
) -> list[Story]:
    """Retrieve all stories belonging to a user."""

    statement = (
        select(Story, Scene.is_ending)
        .outerjoin(StoryState, StoryState.story_id == Story.id)
        .outerjoin(Scene, Scene.id == StoryState.current_scene_id)
        .where(Story.user_id == user_id)
        .order_by(Story.created_at.desc())
    )

    rows = db.execute(statement).all()
    stories = []
    for story, is_ending in rows:
        if is_ending and story.status == "active":
            story.status = "completed"
        stories.append(story)

    return stories


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
    """Delete a user's story and safely remove all dependent child records."""

    from sqlalchemy import delete
    from backend.app.models.character import Character
    from backend.app.models.character_state import CharacterState
    from backend.app.models.choice import Choice
    from backend.app.models.ending import Ending
    from backend.app.models.event import Event
    from backend.app.models.memory import Memory
    from backend.app.models.relationship import Relationship
    from backend.app.models.scene import Scene
    from backend.app.models.story_state import StoryState
    from backend.app.models.user_choices_log import UserChoicesLog
    from backend.app.models.world_state import WorldState

    story = get_story(db, story_id, user_id)

    if story is None:
        return False

    try:
        # Remove runtime/log tables that may reference scenes or characters with RESTRICT FKs.
        db.execute(delete(UserChoicesLog).where(UserChoicesLog.story_id == story_id))
        db.execute(delete(CharacterState).where(CharacterState.story_id == story_id))
        db.execute(delete(StoryState).where(StoryState.story_id == story_id))
        db.execute(delete(Memory).where(Memory.story_id == story_id))
        db.execute(delete(Relationship).where(Relationship.story_id == story_id))
        db.execute(delete(Event).where(Event.story_id == story_id))
        db.execute(delete(WorldState).where(WorldState.story_id == story_id))
        db.execute(
            update(Choice)
            .where(Choice.story_id == story_id)
            .values(next_scene_id=None)
        )
        db.execute(delete(Choice).where(Choice.story_id == story_id))
        db.execute(delete(Character).where(Character.story_id == story_id))
        db.execute(delete(Scene).where(Scene.story_id == story_id))
        db.execute(delete(Ending).where(Ending.story_id == story_id))

        db.delete(story)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise
