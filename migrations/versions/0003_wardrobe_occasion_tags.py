"""wardrobe occasion tags

Revision ID: 0003_wardrobe_occasion_tags
Revises: 0002_profile_enhancements
Create Date: 2026-08-04

"""
import sqlalchemy as sa
from alembic import op


revision = "0003_wardrobe_occasion_tags"
down_revision = "0002_profile_enhancements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wardrobes", sa.Column("occasion_tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("wardrobes", "occasion_tags")
