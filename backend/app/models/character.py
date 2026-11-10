from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    Identity,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Character(Base):
    """Represents a character belonging to a story playthrough."""

    __tablename__ = "characters"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "name",
            name="uq_characters_story_id_name",
        ),
        UniqueConstraint(
            "id",
            "story_id",
            name="uq_characters_id_story_id",
        ),
        CheckConstraint(
            "age IS NULL OR age > 0",
            name="ck_characters_age",
        ),
        ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
            name="fk_characters_story_id_stories",
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

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    age: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    background: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
    )

    goals: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    fears: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    secrets: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
