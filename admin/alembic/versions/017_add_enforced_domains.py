"""Add enforced_domains to smtp_users (per-domain sender binding)

Subset of allowed_domains that goes into the Postfix sender_login_maps.
Domains not listed stay in monitor mode (unrestricted).

Revision ID: 017
Revises: 016
Create Date: 2026-07-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(smtp_users)"))]
    if "enforced_domains" not in existing:
        op.add_column("smtp_users", sa.Column("enforced_domains", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("smtp_users", "enforced_domains")
