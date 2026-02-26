"""Add company and service fields to smtp_users

Revision ID: 005
Revises: 004
Create Date: 2026-02-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(smtp_users)"))]
    if "company" not in columns:
        op.add_column("smtp_users", sa.Column("company", sa.String(), nullable=True))
    if "service" not in columns:
        op.add_column("smtp_users", sa.Column("service", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("smtp_users", "service")
    op.drop_column("smtp_users", "company")
