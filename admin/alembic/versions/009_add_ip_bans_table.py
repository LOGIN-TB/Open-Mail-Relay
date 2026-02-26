"""Add ip_bans table

Revision ID: 009
Revises: 008
Create Date: 2026-02-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    tables = [row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))]
    if "ip_bans" in tables:
        return

    op.create_table(
        "ip_bans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ip_address", sa.String(), nullable=False, unique=True),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("ban_count", sa.Integer(), server_default="1"),
        sa.Column("fail_count", sa.Integer(), server_default="0"),
        sa.Column("first_fail_at", sa.DateTime(), nullable=True),
        sa.Column("banned_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("notes", sa.String(), server_default=""),
    )
    op.create_index("ix_ip_bans_ip_address", "ip_bans", ["ip_address"])


def downgrade() -> None:
    op.drop_index("ix_ip_bans_ip_address", table_name="ip_bans")
    op.drop_table("ip_bans")
