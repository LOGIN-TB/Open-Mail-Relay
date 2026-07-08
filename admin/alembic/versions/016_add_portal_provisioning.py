"""Add portal provisioning fields to smtp_users

password_hash + nullable password_encrypted enable hash-only credentials
(Dovecot {SHA512-CRYPT}); origin/portal_managed/portal_access_id mark
portal-provisioned users; allowed_domains/enforcement_mode prepare domain
binding; updated_at drives the portal reconciler's incremental sync.

Revision ID: 016
Revises: 015
Create Date: 2026-07-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(smtp_users)"))]

    # batch_alter_table recreates the table (SQLite cannot ALTER nullability
    # in place). Existing rows keep their Fernet-encrypted passwords.
    with op.batch_alter_table("smtp_users") as batch:
        if "password_hash" not in existing:
            batch.add_column(sa.Column("password_hash", sa.String(), nullable=True))
        if "origin" not in existing:
            batch.add_column(sa.Column("origin", sa.String(), nullable=False, server_default="local"))
        if "portal_managed" not in existing:
            batch.add_column(sa.Column("portal_managed", sa.Boolean(), nullable=False, server_default="0"))
        if "portal_access_id" not in existing:
            batch.add_column(sa.Column("portal_access_id", sa.String(), nullable=True))
        if "allowed_domains" not in existing:
            batch.add_column(sa.Column("allowed_domains", sa.Text(), nullable=True))
        if "enforcement_mode" not in existing:
            batch.add_column(sa.Column("enforcement_mode", sa.String(), nullable=False, server_default="monitor"))
        if "updated_at" not in existing:
            batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.alter_column("password_encrypted", existing_type=sa.String(), nullable=True)

    # Initialize updated_at so the first incremental reconciler run sees
    # every user exactly once.
    conn.execute(sa.text(
        "UPDATE smtp_users SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)"
    ))


def downgrade() -> None:
    with op.batch_alter_table("smtp_users") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("enforcement_mode")
        batch.drop_column("allowed_domains")
        batch.drop_column("portal_access_id")
        batch.drop_column("portal_managed")
        batch.drop_column("origin")
        batch.drop_column("password_hash")
        batch.alter_column("password_encrypted", existing_type=sa.String(), nullable=False)
