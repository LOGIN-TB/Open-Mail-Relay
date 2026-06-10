"""Add provider_blocks table for provider-internal sending-block monitoring

Revision ID: 015
Revises: 014
Create Date: 2026-06-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = [row[0] for row in conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ))]
    if "provider_blocks" in existing:
        return

    op.create_table(
        "provider_blocks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_label", sa.String(), nullable=False, server_default=""),
        sa.Column("blocked_ip", sa.String(), nullable=False),
        sa.Column("relay_host", sa.String(), server_default=""),
        sa.Column("block_code", sa.String(), server_default=""),
        sa.Column("sample_response", sa.Text(), server_default=""),
        sa.Column("sample_queue_id", sa.String(), server_default=""),
        sa.Column("first_seen", sa.DateTime(), nullable=True),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.Column("hit_count", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("delisting_submitted_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.String(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "blocked_ip", name="uq_provider_block_ip"),
    )
    op.create_index("ix_provider_blocks_provider", "provider_blocks", ["provider"])
    op.create_index("ix_provider_blocks_blocked_ip", "provider_blocks", ["blocked_ip"])
    op.create_index("ix_provider_blocks_last_seen", "provider_blocks", ["last_seen"])
    op.create_index("ix_provider_blocks_status", "provider_blocks", ["status"])


def downgrade() -> None:
    op.drop_table("provider_blocks")
