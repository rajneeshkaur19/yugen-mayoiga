from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKeyConstraint,
    Identity,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Choice(Base):
    """Represents a branching choice or directed edge between scenes in a story graph."""

    __tablename__ = "choices"

    __table_args__ = (
        UniqueConstraint(
            "id",
            "story_id",
            name="uq_choices_id_story_id",
        ),
        ForeignKeyConstraint(
            ["scene_id", "story_id"],
            ["scenes.id", "scenes.story_id"],
            ondelete="CASCADE",
            name="fk_choices_scene_story",
        ),
        ForeignKeyConstraint(
            ["next_scene_id", "story_id"],
            ["scenes.id", "scenes.story_id"],
            ondelete="RESTRICT",
            name="fk_choices_next_scene_story",
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

    scene_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    choice_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    effects: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    condition: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    allow_loop: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    sort_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    next_scene_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
