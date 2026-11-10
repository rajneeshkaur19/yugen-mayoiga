"""Service operations for character memories."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.memory import Memory
from backend.app.models.character import Character
from backend.app.schemas.memory import MemoryCreate, MemoryUpdate


def _character_in_story(db: Session, story_id: int, character_id: int) -> bool:
    return (
        db.scalar(
            select(Character.id).where(
                Character.id == character_id,
                Character.story_id == story_id,
            )
        )
        is not None
    )


def create_memory(db: Session, story_id: int, data: MemoryCreate) -> Memory:
    if not _character_in_story(db, story_id, data.character_id):
        raise ValueError("Character does not belong to this story")

    memory = Memory(
        story_id=story_id,
        character_id=data.character_id,
        event=data.event,
        type=data.type,
        importance=data.importance,
        emotional_weight=data.emotional_weight,
        status=data.status,
        created_turn=data.created_turn,
        embedding=data.embedding,
    )
    try:
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory
    except Exception:
        db.rollback()
        raise


def get_memory(db: Session, story_id: int, memory_id: int) -> Memory | None:
    return db.scalar(
        select(Memory).where(
            Memory.id == memory_id,
            Memory.story_id == story_id,
        )
    )


def list_memories(
    db: Session,
    story_id: int,
    character_id: int | None = None,
) -> list[Memory]:
    stmt = select(Memory).where(Memory.story_id == story_id)
    if character_id is not None:
        stmt = stmt.where(Memory.character_id == character_id)
    return list(db.scalars(stmt.order_by(Memory.created_turn)).all())


def update_memory(
    db: Session,
    story_id: int,
    memory_id: int,
    data: MemoryUpdate,
) -> Memory | None:
    memory = get_memory(db, story_id, memory_id)
    if memory is None:
        return None
    updates = data.model_dump(exclude_unset=True, exclude_none=True)
    try:
        for field, value in updates.items():
            setattr(memory, field, value)
        db.commit()
        db.refresh(memory)
        return memory
    except Exception:
        db.rollback()
        raise


def delete_memory(db: Session, story_id: int, memory_id: int) -> bool:
    memory = get_memory(db, story_id, memory_id)
    if memory is None:
        return False
    try:
        db.delete(memory)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
