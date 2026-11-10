from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class WorldState(Base):
    """Flexible key-value store for world variables within a playthrough.

    Values are JSONB because a world variable may be a boolean, number, string,
    or small structured object (e.g., ``{"power": false, "time": "night"}``).
    ``UNIQUE (story_id, key)`` ensures one value per key per playthrough.
    """

    __tablename__ = "world_states"

    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "key",
            name="uq_world_states_story_id_key",
        ),
        ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
            name="fk_world_states_story_id_stories",
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

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    value: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
