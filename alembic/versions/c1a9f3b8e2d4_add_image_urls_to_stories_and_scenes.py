"""add image urls to stories and scenes

Revision ID: c1a9f3b8e2d4
Revises: 084b1ba43ffb
Create Date: 2026-11-27 21:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a9f3b8e2d4'
down_revision: Union[str, Sequence[str], None] = '084b1ba43ffb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('stories', sa.Column('cover_image_url', sa.String(length=500), nullable=True))
    op.add_column('scenes', sa.Column('scene_image_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('scenes', 'scene_image_url')
    op.drop_column('stories', 'cover_image_url')
