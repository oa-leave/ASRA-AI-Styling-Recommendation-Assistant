"""clothing recognition task

Revision ID: 0007_clothing_recognition_task
Revises: 0006_wardrobe_recognition_status
Create Date: 2026-08-09

"""
import sqlalchemy as sa
from alembic import op


revision = "0007_clothing_recognition_task"
down_revision = "0006_wardrobe_recognition_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "clothing_recognition_tasks" not in inspector.get_table_names():
        op.create_table(
            "clothing_recognition_tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("image_path", sa.String(255), nullable=False),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(30), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "clothing_recognition_tasks" in inspector.get_table_names():
        op.drop_table("clothing_recognition_tasks")
