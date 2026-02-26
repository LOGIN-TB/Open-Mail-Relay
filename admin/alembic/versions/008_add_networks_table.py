"""Add networks table

Revision ID: 008
Revises: 007
Create Date: 2026-02-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pathlib import Path

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROTECTED_NETWORKS = {"127.0.0.0/8", "172.16.0.0/12"}
MYNETWORKS_FILE = Path("/etc/postfix-config/mynetworks")


def upgrade() -> None:
    conn = op.get_bind()
    tables = [row[0] for row in conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))]
    if "networks" in tables:
        return

    op.create_table(
        "networks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cidr", sa.String(), nullable=False, unique=True),
        sa.Column("owner", sa.String(), server_default=""),
        sa.Column("is_protected", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_networks_cidr", "networks", ["cidr"])

    # Seed protected networks
    for cidr in sorted(PROTECTED_NETWORKS):
        conn.execute(sa.text(
            "INSERT INTO networks (cidr, owner, is_protected) VALUES (:cidr, 'System', 1)"
        ), {"cidr": cidr})

    # Migrate existing networks from file
    if MYNETWORKS_FILE.exists():
        content = MYNETWORKS_FILE.read_text().strip()
        for line in content.splitlines():
            cidr = line.strip()
            if not cidr or cidr.startswith("#"):
                continue
            if cidr in PROTECTED_NETWORKS:
                continue
            # Check for duplicates before inserting
            existing = conn.execute(sa.text(
                "SELECT id FROM networks WHERE cidr = :cidr"
            ), {"cidr": cidr}).fetchone()
            if not existing:
                conn.execute(sa.text(
                    "INSERT INTO networks (cidr, owner, is_protected) VALUES (:cidr, '', 0)"
                ), {"cidr": cidr})


def downgrade() -> None:
    op.drop_index("ix_networks_cidr", table_name="networks")
    op.drop_table("networks")
