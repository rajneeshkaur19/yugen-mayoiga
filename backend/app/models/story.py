
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Story(Base):
    """Represents a user's story playthrough."""

    __tablename__ = "stories"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')",
            name="ck_stories_status",
        ),
        CheckConstraint(
            "length IN ('short', 'medium', 'long')",
            name="ck_stories_length",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    genre: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    theme: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    tone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    season: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    length: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
