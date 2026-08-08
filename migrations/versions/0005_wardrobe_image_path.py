"""wardrobe image path

Revision ID: 0005_wardrobe_image_path
Revises: 0004_recommendation_history
Create Date: 2026-08-07

"""
import sqlalchemy as sa
from alembic import op


revision = "0005_wardrobe_image_path"
down_revision = "0004_recommendation_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("wardrobes")}
    if "image_path" not in columns:
        op.add_column("wardrobes", sa.Column("image_path", sa.String(255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("wardrobes")}
    if "image_path" in columns:
        op.drop_column("wardrobes", "image_path")
