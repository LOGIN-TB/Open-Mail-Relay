"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "mail_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("queue_id", sa.String(), nullable=True),
        sa.Column("sender", sa.String(), nullable=True),
        sa.Column("recipient", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("relay", sa.String(), nullable=True),
        sa.Column("delay", sa.Float(), nullable=True),
        sa.Column("dsn", sa.String(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
    )
    op.create_index("ix_mail_events_timestamp", "mail_events", ["timestamp"])
    op.create_index("ix_mail_events_queue_id", "mail_events", ["queue_id"])

    op.create_table(
        "stats_hourly",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("hour_start", sa.DateTime(), nullable=False, unique=True),
        sa.Column("sent_count", sa.Integer(), default=0),
        sa.Column("deferred_count", sa.Integer(), default=0),
        sa.Column("bounced_count", sa.Integer(), default=0),
        sa.Column("rejected_count", sa.Integer(), default=0),
    )
    op.create_index("ix_stats_hourly_hour_start", "stats_hourly", ["hour_start"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("stats_hourly")
    op.drop_table("mail_events")
    op.drop_table("users")
