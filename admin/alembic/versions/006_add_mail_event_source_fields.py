"""Add client_ip and sasl_username to mail_events

Revision ID: 006
Revises: 005
Create Date: 2026-02-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(mail_events)"))]
    if "client_ip" not in columns:
        op.add_column("mail_events", sa.Column("client_ip", sa.String(), nullable=True))
    if "sasl_username" not in columns:
        op.add_column("mail_events", sa.Column("sasl_username", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("mail_events", "sasl_username")
    op.drop_column("mail_events", "client_ip")
