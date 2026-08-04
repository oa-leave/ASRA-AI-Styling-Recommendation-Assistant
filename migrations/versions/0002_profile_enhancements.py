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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}

    if "fit_tags" not in columns:
        op.add_column("user_profiles", sa.Column("fit_tags", sa.JSON(), nullable=True))
    if "avoid_colors" not in columns:
        op.add_column("user_profiles", sa.Column("avoid_colors", sa.JSON(), nullable=True))
    if "occasion_preferences" not in columns:
        op.add_column(
            "user_profiles",
            sa.Column("occasion_preferences", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}

    if "occasion_preferences" in columns:
        op.drop_column("user_profiles", "occasion_preferences")
    if "avoid_colors" in columns:
        op.drop_column("user_profiles", "avoid_colors")
    if "fit_tags" in columns:
        op.drop_column("user_profiles", "fit_tags")
