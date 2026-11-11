"""Relationship Engine for Yūgen Mayoiga.

Handles:
- Directed character-to-character relationships (from_character -> to_character)
- Attributes: trust, friendship, suspicion, fear, dependency (clamped 0 to 100)
- Validation preventing self-loops and cross-story links
- Deterministic delta application
- Persistence in the relationships table
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from algorithms.state_store import RELATIONSHIP_ATTRS, clamp
from backend.app.models.character import Character
from backend.app.models.relationship import Relationship


def _verify_character_in_story(db: Session, story_id: int, character_id: int) -> bool:
    """Return True if character belongs to story."""
    return (
        db.scalar(
            select(Character.id).where(
                Character.id == character_id,
                Character.story_id == story_id,
            )
        )
        is not None
    )


def get_relationship(
    db: Session,
    story_id: int,
    from_character: int,
    to_character: int,
) -> Relationship | None:
    """Retrieve a directed relationship between two characters in the same story."""
    return db.scalar(
        select(Relationship).where(
            Relationship.story_id == story_id,
            Relationship.from_character == from_character,
            Relationship.to_character == to_character,
        )
    )


def list_story_relationships(
    db: Session,
    story_id: int,
    character_id: int | None = None,
) -> list[Relationship]:
    """List all relationships in a story, optionally filtered by participant."""
    stmt = select(Relationship).where(Relationship.story_id == story_id)
    if character_id is not None:
        stmt = stmt.where(
            (Relationship.from_character == character_id)
            | (Relationship.to_character == character_id)
        )
    return list(db.scalars(stmt.order_by(Relationship.id)).all())


def create_or_update_relationship(
    db: Session,
    story_id: int,
    from_character: int,
    to_character: int,
    values: dict[str, int],
) -> Relationship:
    """Create or update a directed relationship with clamped values."""
    if from_character == to_character:
        raise ValueError("A character cannot have a relationship with themselves.")

    if not _verify_character_in_story(db, story_id, from_character):
        raise ValueError(f"Character {from_character} does not belong to story {story_id}.")
    if not _verify_character_in_story(db, story_id, to_character):
        raise ValueError(f"Character {to_character} does not belong to story {story_id}.")

    rel = get_relationship(db, story_id, from_character, to_character)

    if rel is None:
        rel = Relationship(
            story_id=story_id,
            from_character=from_character,
            to_character=to_character,
            trust=clamp(values.get("trust", 50)),
            friendship=clamp(values.get("friendship", 50)),
            suspicion=clamp(values.get("suspicion", 0)),
            fear=clamp(values.get("fear", 0)),
            dependency=clamp(values.get("dependency", 0)),
        )
        db.add(rel)
    else:
        for attr in RELATIONSHIP_ATTRS:
            if attr in values and isinstance(values[attr], (int, float)):
                setattr(rel, attr, clamp(values[attr]))

    return rel


def apply_relationship_deltas(
    db: Session,
    story_id: int,
    from_character: int,
    to_character: int,
    deltas: dict[str, int],
) -> Relationship:
    """Apply relative deltas to a directed relationship."""
    rel = get_relationship(db, story_id, from_character, to_character)

    if rel is None:
        # Create baseline and apply deltas
        base = {
            "trust": 50,
            "friendship": 50,
            "suspicion": 0,
            "fear": 0,
            "dependency": 0,
        }
        for attr, delta in deltas.items():
            if attr in RELATIONSHIP_ATTRS and isinstance(delta, (int, float)):
                base[attr] = clamp(base[attr] + int(delta))
        return create_or_update_relationship(db, story_id, from_character, to_character, base)

    for attr, delta in deltas.items():
        if attr in RELATIONSHIP_ATTRS and isinstance(delta, (int, float)):
            curr = getattr(rel, attr)
            setattr(rel, attr, clamp(curr + int(delta)))

    return rel
