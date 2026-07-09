"""Add monthly_limit_override and monthly_report_enabled to smtp_users

Revision ID: 018
Revises: 017
Create Date: 2026-07-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def upgrade() -> None:
    if not _has_column("smtp_users", "monthly_limit_override"):
        op.add_column("smtp_users", sa.Column("monthly_limit_override", sa.Integer(), nullable=True))
    if not _has_column("smtp_users", "monthly_report_enabled"):
        op.add_column(
            "smtp_users",
            sa.Column("monthly_report_enabled", sa.Boolean(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    op.drop_column("smtp_users", "monthly_report_enabled")
    op.drop_column("smtp_users", "monthly_limit_override")
