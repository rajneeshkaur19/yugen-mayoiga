"""add portrait fields to characters

Revision ID: d4e8a1f2b3c5
Revises: c1a9f3b8e2d4
Create Date: 2026-11-27 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e8a1f2b3c5'
down_revision: Union[str, Sequence[str], None] = 'c1a9f3b8e2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add character portrait and visual description columns."""
    op.add_column('characters', sa.Column('portrait_image_url', sa.String(length=500), nullable=True))
    op.add_column('characters', sa.Column('visual_description', sa.Text(), nullable=True))
    op.add_column('characters', sa.Column('visual_prompt_anchor', sa.String(length=300), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('characters', 'visual_prompt_anchor')
    op.drop_column('characters', 'visual_description')
    op.drop_column('characters', 'portrait_image_url')
