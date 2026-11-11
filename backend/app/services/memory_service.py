"""Service operations for character memories with DSA retrieval and promotion."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from algorithms.memory_retrieval import MemoryRecord, MemoryStore
from backend.app.models.character import Character
from backend.app.models.memory import Memory
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
    memory_type: str | None = None,
) -> list[Memory]:
    stmt = select(Memory).where(Memory.story_id == story_id)
    if character_id is not None:
        stmt = stmt.where(Memory.character_id == character_id)
    if memory_type is not None:
        stmt = stmt.where(Memory.type == memory_type)
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


def promote_memory(
    db: Session,
    story_id: int,
    memory_id: int,
    new_type: str,
    new_status: str | None = None,
) -> Memory | None:
    """Promote a memory (e.g. short_term -> long_term, or normal -> gilded)."""
    if new_type not in ("short_term", "long_term", "emotional", "player_choice"):
        raise ValueError(f"Invalid memory type '{new_type}'")
    if new_status is not None and new_status not in ("normal", "cracked", "gilded"):
        raise ValueError(f"Invalid memory status '{new_status}'")

    memory = get_memory(db, story_id, memory_id)
    if memory is None:
        return None

    memory.type = new_type
    if new_status:
        memory.status = new_status

    db.commit()
    db.refresh(memory)
    return memory


def retrieve_relevant_memories(
    db: Session,
    story_id: int,
    query: str,
    current_turn: int,
    k: int = 5,
    character_id: int | None = None,
) -> list[tuple[Memory, float]]:
    """Retrieve top-k relevant memories using O(n log k) heap retrieval."""
    all_story_memories = list_memories(db, story_id, character_id=character_id)
    if not all_story_memories:
        return []

    store = MemoryStore()
    id_to_model: dict[int, Memory] = {}
    for m in all_story_memories:
        record = MemoryRecord(
            memory_id=m.id,
            character_id=m.character_id,
            event=m.event,
            type=m.type,
            importance=m.importance,
            emotional_weight=m.emotional_weight,
            status=m.status,
            created_turn=m.created_turn,
            story_id=m.story_id,
        )
        store.add_memory(record)
        id_to_model[m.id] = m

    top_records = store.retrieve_top_k(
        query=query,
        current_turn=current_turn,
        k=k,
        character_id=character_id,
    )

    return [(id_to_model[rec.memory_id], score) for rec, score in top_records if rec.memory_id in id_to_model]
