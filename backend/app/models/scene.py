from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Scene(Base):
    """Represents a scene node within a story graph."""

    __tablename__ = "scenes"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "scene_number",
            name="uq_scenes_story_id_scene_number",
        ),
        UniqueConstraint(
            "id",
            "story_id",
            name="uq_scenes_id_story_id",
        ),
        ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
            name="fk_scenes_story_id_stories",
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

    scene_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    mood: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    haiku: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    is_ending: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
