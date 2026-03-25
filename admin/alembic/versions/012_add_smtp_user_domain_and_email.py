"""Add mail_domain and contact_email to smtp_users

Revision ID: 012
Revises: 011
Create Date: 2026-03-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("smtp_users", sa.Column("mail_domain", sa.String(), nullable=True))
    op.add_column("smtp_users", sa.Column("contact_email", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("smtp_users", "contact_email")
    op.drop_column("smtp_users", "mail_domain")
