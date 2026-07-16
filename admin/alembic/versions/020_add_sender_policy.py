"""Add sender_policy to smtp_users (strict sender binding, portal ADR 0009)

Revision ID: 020
Revises: 019
Create Date: 2026-07-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def upgrade() -> None:
    # 'unrestricted' for every existing row — behaviour stays unchanged until
    # the portal pushes explicit values and the strict switch is turned on.
    if not _has_column("smtp_users", "sender_policy"):
        op.add_column(
            "smtp_users",
            sa.Column("sender_policy", sa.String(), nullable=False, server_default="unrestricted"),
        )


def downgrade() -> None:
    op.drop_column("smtp_users", "sender_policy")
