from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    SmallInteger,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class CharacterTraits(Base):
    """Represents stable Big Five-inspired personality traits for a character."""

    __tablename__ = "character_traits"

    __table_args__ = (
        ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
            ondelete="CASCADE",
            name="fk_character_traits_character_id_characters",
        ),
        CheckConstraint(
            "openness BETWEEN 0 AND 100",
            name="ck_character_traits_openness",
        ),
        CheckConstraint(
            "conscientiousness BETWEEN 0 AND 100",
            name="ck_character_traits_conscientiousness",
        ),
        CheckConstraint(
            "extraversion BETWEEN 0 AND 100",
            name="ck_character_traits_extraversion",
        ),
        CheckConstraint(
            "agreeableness BETWEEN 0 AND 100",
            name="ck_character_traits_agreeableness",
        ),
        CheckConstraint(
            "neuroticism BETWEEN 0 AND 100",
            name="ck_character_traits_neuroticism",
        ),
    )

    character_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    openness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    conscientiousness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    extraversion: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    agreeableness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    neuroticism: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
