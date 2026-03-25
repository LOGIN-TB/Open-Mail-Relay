"""Add receive_reports to smtp_users

Revision ID: 013
Revises: 012
Create Date: 2026-03-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("smtp_users", sa.Column("receive_reports", sa.Boolean(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("smtp_users", "receive_reports")
