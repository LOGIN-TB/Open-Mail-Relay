"""Add system_settings table and status index

Revision ID: 002
Revises: 001
Create Date: 2026-02-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
    )

    op.create_index("ix_mail_events_status", "mail_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_mail_events_status", table_name="mail_events")
    op.drop_table("system_settings")
