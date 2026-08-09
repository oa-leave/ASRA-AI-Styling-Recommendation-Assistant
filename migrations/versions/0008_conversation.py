"""conversation session and messages

Revision ID: 0008_conversation
Revises: 0007_clothing_recognition_task
Create Date: 2026-08-09

"""
import sqlalchemy as sa
from alembic import op


revision = "0008_conversation"
down_revision = "0007_clothing_recognition_task"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "conversation_sessions" not in tables:
        op.create_table(
            "conversation_sessions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("context", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )

    if "conversation_messages" not in tables:
        op.create_table(
            "conversation_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.String(64), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("content", sa.JSON(), nullable=True),
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
    tables = set(inspector.get_table_names())
    if "conversation_messages" in tables:
        op.drop_table("conversation_messages")
    if "conversation_sessions" in tables:
        op.drop_table("conversation_sessions")
