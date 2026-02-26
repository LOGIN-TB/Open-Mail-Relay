"""Add last_used_at to smtp_users

Revision ID: 007
Revises: 006
Create Date: 2026-02-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(smtp_users)"))]
    if "last_used_at" not in columns:
        op.add_column("smtp_users", sa.Column("last_used_at", sa.DateTime(), nullable=True))

    # Backfill from existing mail_events
    conn.execute(sa.text("""
        UPDATE smtp_users
        SET last_used_at = (
            SELECT MAX(timestamp) FROM mail_events
            WHERE mail_events.sasl_username = smtp_users.username
        )
        WHERE EXISTS (
            SELECT 1 FROM mail_events
            WHERE mail_events.sasl_username = smtp_users.username
        )
    """))


def downgrade() -> None:
    op.drop_column("smtp_users", "last_used_at")
