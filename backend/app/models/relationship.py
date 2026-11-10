from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKeyConstraint,
    Identity,
    SmallInteger,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Relationship(Base):
    """Directed emotional relationship from one character to another.

    ``from_character → to_character`` and ``to_character → from_character``
    are stored separately because feelings may differ in each direction.

    Composite FKs prevent linking characters from different playthroughs.
    """

    __tablename__ = "relationships"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "from_character",
            "to_character",
            name="uq_relationships_story_from_to",
        ),
        CheckConstraint(
            "from_character <> to_character",
            name="ck_relationships_no_self_loop",
        ),
        CheckConstraint("trust BETWEEN 0 AND 100", name="ck_relationships_trust"),
        CheckConstraint("friendship BETWEEN 0 AND 100", name="ck_relationships_friendship"),
        CheckConstraint("suspicion BETWEEN 0 AND 100", name="ck_relationships_suspicion"),
        CheckConstraint("fear BETWEEN 0 AND 100", name="ck_relationships_fear"),
        CheckConstraint("dependency BETWEEN 0 AND 100", name="ck_relationships_dependency"),
        ForeignKeyConstraint(
            ["from_character", "story_id"],
            ["characters.id", "characters.story_id"],
            name="fk_relationships_from_character_story",
        ),
        ForeignKeyConstraint(
            ["to_character", "story_id"],
            ["characters.id", "characters.story_id"],
            name="fk_relationships_to_character_story",
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

    from_character: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    to_character: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    trust: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=50,
        server_default=text("50"),
    )

    friendship: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=50,
        server_default=text("50"),
    )

    suspicion: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    fear: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    dependency: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
