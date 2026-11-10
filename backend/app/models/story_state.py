from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Integer,
    SmallInteger,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class StoryState(Base):
    """Tracks the current state of a single story playthrough.

    One row per playthrough. The composite FK (current_scene_id, story_id) →
    scenes(id, story_id) ensures the current scene always belongs to the same
    playthrough.
    """

    __tablename__ = "story_states"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            name="uq_story_states_story_id",
        ),
        CheckConstraint(
            "yugen_meter BETWEEN 0 AND 100",
            name="ck_story_states_yugen_meter",
        ),
        CheckConstraint(
            "turn_number >= 0",
            name="ck_story_states_turn_number",
        ),
        ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
            name="fk_story_states_story_id_stories",
        ),
        ForeignKeyConstraint(
            ["current_scene_id", "story_id"],
            ["scenes.id", "scenes.story_id"],
            name="fk_story_states_current_scene_story",
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

    current_scene_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    hidden_variables: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    yugen_meter: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    turn_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
