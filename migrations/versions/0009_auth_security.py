"""auth security tables

Revision ID: 0009_auth_security
Revises: 0008_conversation
Create Date: 2026-08-10

"""
import sqlalchemy as sa
from alembic import op


revision = "0009_auth_security"
down_revision = "0008_conversation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_refresh_tokens_token_hash",
            "refresh_tokens",
            ["token_hash"],
        )
        op.create_index(
            "ix_refresh_tokens_user_id",
            "refresh_tokens",
            ["user_id"],
        )

    if "login_attempts" not in tables:
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(32), nullable=False),
            sa.Column(
                "succeeded",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_login_attempts_username",
            "login_attempts",
            ["username"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "login_attempts" in tables:
        op.drop_index("ix_login_attempts_username", table_name="login_attempts")
        op.drop_table("login_attempts")
    if "refresh_tokens" in tables:
        op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
        op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
        op.drop_table("refresh_tokens")
