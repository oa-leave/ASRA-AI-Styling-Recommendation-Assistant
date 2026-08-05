"""recommendation history

Revision ID: 0004_recommendation_history
Revises: 0003_wardrobe_occasion_tags
Create Date: 2026-08-05

"""
import sqlalchemy as sa
from alembic import op


revision = "0004_recommendation_history"
down_revision = "0003_wardrobe_occasion_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "recommendation_history" not in inspector.get_table_names():
        op.create_table(
            "recommendation_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("request_context", sa.JSON(), nullable=True),
            sa.Column("response_snapshot", sa.JSON(), nullable=True),
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
    if "recommendation_history" in inspector.get_table_names():
        op.drop_table("recommendation_history")
