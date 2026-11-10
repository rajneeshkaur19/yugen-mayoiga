from typing import Any

from sqlalchemy import (
    BigInteger,
    ForeignKeyConstraint,
    Identity,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Ending(Base):
    """An ending definition for a story playthrough.

    ``conditions`` is a JSONB object evaluated by application logic against the
    current state. ``UNIQUE (story_id, name)`` prevents duplicate ending names
    within the same playthrough.
    """

    __tablename__ = "endings"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "name",
            name="uq_endings_story_id_name",
        ),
        ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
            name="fk_endings_story_id_stories",
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

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    conditions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    seal_text: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
