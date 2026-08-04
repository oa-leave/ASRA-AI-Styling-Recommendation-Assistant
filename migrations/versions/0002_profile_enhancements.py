"""profile enhancements

Revision ID: 0002_profile_enhancements
Revises: 0001_initial
Create Date: 2026-08-04

"""
import sqlalchemy as sa
from alembic import op


revision = "0002_profile_enhancements"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("fit_tags", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("avoid_colors", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("occasion_preferences", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "occasion_preferences")
    op.drop_column("user_profiles", "avoid_colors")
    op.drop_column("user_profiles", "fit_tags")
