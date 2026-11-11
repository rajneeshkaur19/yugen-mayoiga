"""World State Engine for Yūgen Mayoiga.

Handles:
- Persistent key-value world variables (weather, time, door, power, etc.)
- Values stored as JSONB
- Deterministic updates from choices and story events
- Story isolation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.world_state import WorldState


def get_all_world_vars(db: Session, story_id: int) -> dict[str, Any]:
    """Return all world state variables for a story as a Python dictionary."""
    records = list(
        db.scalars(
            select(WorldState)
            .where(WorldState.story_id == story_id)
            .order_by(WorldState.key)
        ).all()
    )
    return {r.key: r.value for r in records}


def get_world_var(db: Session, story_id: int, key: str, default: Any = None) -> Any:
    """Get a single world variable value."""
    record = db.scalar(
        select(WorldState).where(
            WorldState.story_id == story_id,
            WorldState.key == key,
        )
    )
    if record is None:
        return default
    return record.value


def set_world_var(
    db: Session,
    story_id: int,
    key: str,
    value: Any,
) -> WorldState:
    """Set or update a single world variable."""
    record = db.scalar(
        select(WorldState).where(
            WorldState.story_id == story_id,
            WorldState.key == key,
        )
    )
    now = datetime.now(timezone.utc)
    if record is None:
        record = WorldState(
            story_id=story_id,
            key=key,
            value=value,
            updated_at=now,
        )
        db.add(record)
    else:
        record.value = value
        record.updated_at = now

    return record


def update_world_state(
    db: Session,
    story_id: int,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Apply a dictionary of world state updates."""
    for k, v in updates.items():
        set_world_var(db, story_id, k, v)
    return get_all_world_vars(db, story_id)
