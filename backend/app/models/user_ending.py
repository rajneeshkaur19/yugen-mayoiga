from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class UserEnding(Base):
    """Records an ending that a user has achieved.

    ``UNIQUE (user_id, ending_id)`` prevents the same user from recording the
    same ending twice.
    """

    __tablename__ = "user_endings"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "ending_id",
            name="uq_user_endings_user_id_ending_id",
        ),
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_user_endings_user_id_users",
        ),
        ForeignKeyConstraint(
            ["ending_id"],
            ["endings.id"],
            ondelete="CASCADE",
            name="fk_user_endings_ending_id_endings",
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

    ending_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    achieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
