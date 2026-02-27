"""Add auth_failed_count to stats_hourly

Revision ID: 010
Revises: 009
Create Date: 2026-02-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stats_hourly", sa.Column("auth_failed_count", sa.Integer(), server_default="0"))


def downgrade() -> None:
    op.drop_column("stats_hourly", "auth_failed_count")
