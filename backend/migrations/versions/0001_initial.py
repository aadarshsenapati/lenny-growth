"""initial schema: chat_sessions, messages, artifacts

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-15

Targets MySQL (InnoDB). UUIDs are stored as CHAR(36) -- MySQL has no native
UUID column type -- matching the portable `UUID` TypeDecorator in
app/db/models.py. `citations` uses MySQL's native JSON type (5.7.8+).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False, server_default="New chat"),
        sa.Column("user_id", sa.String(255), nullable=False, server_default="anonymous"),
        sa.Column("llm_provider", sa.String(32), nullable=False, server_default="groq"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.CHAR(36),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("skill_used", sa.String(64), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("llm_provider", sa.String(32), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.CHAR(36),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.CHAR(36),
            sa.ForeignKey("messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_artifacts_session_id", "artifacts", ["session_id"])


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("messages")
    op.drop_table("chat_sessions")
