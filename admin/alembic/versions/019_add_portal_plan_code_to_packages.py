"""Add portal_plan_code to packages (portal-managed plan mirror)

Revision ID: 019
Revises: 018
Create Date: 2026-07-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def upgrade() -> None:
    if not _has_column("packages", "portal_plan_code"):
        op.add_column("packages", sa.Column("portal_plan_code", sa.String(), nullable=True))
        op.create_index(
            "ix_packages_portal_plan_code", "packages", ["portal_plan_code"], unique=True
        )


def downgrade() -> None:
    op.drop_index("ix_packages_portal_plan_code", table_name="packages")
    op.drop_column("packages", "portal_plan_code")
