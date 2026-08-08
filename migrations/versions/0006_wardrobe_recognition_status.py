"""wardrobe recognition status

Revision ID: 0006_wardrobe_recognition_status
Revises: 0005_wardrobe_image_path
Create Date: 2026-08-08

"""
import sqlalchemy as sa
from alembic import op


revision = "0006_wardrobe_recognition_status"
down_revision = "0005_wardrobe_image_path"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("wardrobes")}
    if "recognition_status" not in columns:
        op.add_column(
            "wardrobes",
            sa.Column("recognition_status", sa.String(30), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("wardrobes")}
    if "recognition_status" in columns:
        op.drop_column("wardrobes", "recognition_status")
