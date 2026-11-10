from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class CharacterState(Base):
    """Emotion snapshot for a character at a specific story turn.

    Records emotion values per turn so that revisiting the same scene at a
    different turn produces a new snapshot rather than overwriting the old one.

    Composite FK (character_id, story_id) → characters(id, story_id) and
    (scene_id, story_id) → scenes(id, story_id) prevent cross-story links.
    """

    __tablename__ = "character_states"

    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "turn_number",
            name="uq_character_states_character_id_turn_number",
        ),
        CheckConstraint("fear BETWEEN 0 AND 100", name="ck_character_states_fear"),
        CheckConstraint("anxiety BETWEEN 0 AND 100", name="ck_character_states_anxiety"),
        CheckConstraint("anger BETWEEN 0 AND 100", name="ck_character_states_anger"),
        CheckConstraint("sadness BETWEEN 0 AND 100", name="ck_character_states_sadness"),
        CheckConstraint("happiness BETWEEN 0 AND 100", name="ck_character_states_happiness"),
        CheckConstraint("trust BETWEEN 0 AND 100", name="ck_character_states_trust"),
        CheckConstraint("turn_number >= 0", name="ck_character_states_turn_number"),
        ForeignKeyConstraint(
            ["character_id", "story_id"],
            ["characters.id", "characters.story_id"],
            name="fk_character_states_character_story",
        ),
        ForeignKeyConstraint(
            ["scene_id", "story_id"],
            ["scenes.id", "scenes.story_id"],
            name="fk_character_states_scene_story",
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

    scene_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    turn_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    fear: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    anxiety: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    anger: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    sadness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    happiness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    trust: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
