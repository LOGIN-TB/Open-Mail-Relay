"""Add dsn_code and remote_response to mail_events

Revision ID: 014
Revises: 013
Create Date: 2026-04-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(mail_events)"))]
    if "dsn_code" not in columns:
        op.add_column("mail_events", sa.Column("dsn_code", sa.String(), nullable=True))
    if "remote_response" not in columns:
        op.add_column("mail_events", sa.Column("remote_response", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("mail_events", "remote_response")
    op.drop_column("mail_events", "dsn_code")
