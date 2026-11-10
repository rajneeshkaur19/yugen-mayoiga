"""Service operations for characters and their traits."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.character import Character
from backend.app.models.character_traits import CharacterTraits
from backend.app.schemas.character import CharacterCreate, CharacterUpdate


def _get_story_character(
    db: Session,
    story_id: int,
    character_id: int,
) -> Character | None:
    """Return a character only if it belongs to the given story."""
    return db.scalar(
        select(Character).where(
            Character.id == character_id,
            Character.story_id == story_id,
        )
    )


def create_character(
    db: Session,
    story_id: int,
    data: CharacterCreate,
) -> Character:
    """Create a character (and optional traits) within a story."""
    traits_data = data.traits
    char = Character(
        story_id=story_id,
        name=data.name,
        role=data.role,
        age=data.age,
        background=data.background,
        goals=data.goals,
        fears=data.fears,
        secrets=data.secrets,
    )
    try:
        db.add(char)
        db.flush()  # populate char.id before creating traits

        if traits_data is not None:
            traits = CharacterTraits(
                character_id=char.id,
                **traits_data.model_dump(),
            )
            db.add(traits)

        db.commit()
        db.refresh(char)
        return char
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A character with this name already exists in the story"
        ) from exc
    except Exception:
        db.rollback()
        raise


def get_character(
    db: Session,
    story_id: int,
    character_id: int,
) -> Character | None:
    """Return a single character belonging to a story."""
    return _get_story_character(db, story_id, character_id)


def list_characters(db: Session, story_id: int) -> list[Character]:
    """Return all characters for a story."""
    return list(
        db.scalars(
            select(Character)
            .where(Character.story_id == story_id)
            .order_by(Character.id)
        ).all()
    )


def update_character(
    db: Session,
    story_id: int,
    character_id: int,
    data: CharacterUpdate,
) -> Character | None:
    """Update a character's fields (not traits)."""
    char = _get_story_character(db, story_id, character_id)
    if char is None:
        return None

    updates = data.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        return char

    try:
        for field, value in updates.items():
            setattr(char, field, value)
        db.commit()
        db.refresh(char)
        return char
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A character with this name already exists in the story"
        ) from exc
    except Exception:
        db.rollback()
        raise


def delete_character(
    db: Session,
    story_id: int,
    character_id: int,
) -> bool:
    """Delete a character. Returns True if deleted, False if not found."""
    char = _get_story_character(db, story_id, character_id)
    if char is None:
        return False
    try:
        db.delete(char)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def get_traits(
    db: Session,
    character_id: int,
) -> CharacterTraits | None:
    """Return the traits for a character."""
    return db.get(CharacterTraits, character_id)


def upsert_traits(
    db: Session,
    story_id: int,
    character_id: int,
    data: dict,
) -> CharacterTraits | None:
    """Create or replace the traits for a character in the given story."""
    # Verify character belongs to this story
    char = _get_story_character(db, story_id, character_id)
    if char is None:
        return None

    traits = db.get(CharacterTraits, character_id)
    try:
        if traits is None:
            traits = CharacterTraits(character_id=character_id, **data)
            db.add(traits)
        else:
            for field, value in data.items():
                setattr(traits, field, value)
        db.commit()
        db.refresh(traits)
        return traits
    except Exception:
        db.rollback()
        raise
