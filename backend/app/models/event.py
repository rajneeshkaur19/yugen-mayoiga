from typing import Any, Optional

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Event(Base):
    """A scheduled story event managed by the priority-queue engine.

    ``due_turn`` and ``priority`` drive ordering. ``trigger_condition`` is a
    nullable JSONB object used by the engine to decide when to promote a
    pending event to ready.
    """

    __tablename__ = "events"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'ready', 'done')",
            name="ck_events_status",
        ),
        CheckConstraint(
            "due_turn >= 0",
            name="ck_events_due_turn",
        ),
        ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
            name="fk_events_story_id_stories",
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

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    priority: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    due_turn: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    trigger_condition: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    effects: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
