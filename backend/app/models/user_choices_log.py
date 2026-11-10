from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class UserChoicesLog(Base):
    """Append-only action log for every player action in a playthrough.

    Records both button choices (``choice_id`` set) and free-text actions
    (``free_text`` set). At least one must be non-NULL.

    ``UNIQUE (story_id, turn_number)`` enforces one action per turn.
    Composite FK (scene_id, story_id) → scenes(id, story_id) keeps the
    referenced scene in the same playthrough.
    """

    __tablename__ = "user_choices_log"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "turn_number",
            name="uq_user_choices_log_story_turn",
        ),
        CheckConstraint(
            "choice_id IS NOT NULL OR free_text IS NOT NULL",
            name="ck_user_choices_log_has_action",
        ),
        CheckConstraint(
            "turn_number >= 0",
            name="ck_user_choices_log_turn_number",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_user_choices_log_user_id_users",
        ),
        ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
            name="fk_user_choices_log_story_id_stories",
        ),
        ForeignKeyConstraint(
            ["scene_id", "story_id"],
            ["scenes.id", "scenes.story_id"],
            name="fk_user_choices_log_scene_story",
        ),
        ForeignKeyConstraint(
            ["choice_id", "story_id"],
            ["choices.id", "choices.story_id"],
            name="fk_user_choices_log_choice_story",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    story_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    turn_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    scene_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    choice_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    free_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    parsed_action: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    delta: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    undone: Mapped[bool] = mapped_column(
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
