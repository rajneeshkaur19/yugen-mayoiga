"""Add JSONB effects to scheduled events.

Revision ID: a7f4c2d91e60
Revises: d34a3aaf62d4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a7f4c2d91e60"
down_revision: Union[str, Sequence[str], None] = "d34a3aaf62d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "effects",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "effects")
