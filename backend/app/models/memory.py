from typing import Any, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    Identity,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, REAL
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Memory(Base):
    """A character memory from a specific story turn.

    Memories are categorised as short_term, long_term, emotional or
    player_choice. The optional ``embedding`` column supports future semantic
    retrieval (Week 6+) and may remain NULL until then.

    Composite FK (character_id, story_id) → characters(id, story_id) prevents
    memories from accidentally referencing characters in other playthroughs.
    """

    __tablename__ = "memories"

    __table_args__ = (
        CheckConstraint(
            "importance BETWEEN 0 AND 100",
            name="ck_memories_importance",
        ),
        CheckConstraint(
            "emotional_weight BETWEEN -100 AND 100",
            name="ck_memories_emotional_weight",
        ),
        CheckConstraint(
            "type IN ('short_term', 'long_term', 'emotional', 'player_choice')",
            name="ck_memories_type",
        ),
        CheckConstraint(
            "status IN ('normal', 'cracked', 'gilded')",
            name="ck_memories_status",
        ),
        CheckConstraint(
            "created_turn >= 0",
            name="ck_memories_created_turn",
        ),
        ForeignKeyConstraint(
            ["character_id", "story_id"],
            ["characters.id", "characters.story_id"],
            name="fk_memories_character_story",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    story_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    character_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    event: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    importance: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=50,
        server_default=text("50"),
    )

    emotional_weight: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="normal",
        server_default=text("'normal'"),
    )

    created_turn: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Optional semantic-search embedding (Week 6+). Stored as a REAL[] array.
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(REAL),
        nullable=True,
    )
