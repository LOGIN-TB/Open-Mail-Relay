"""Add packages, billing reports, and user monthly usage tables

Revision ID: 011
Revises: 010
Create Date: 2026-03-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- packages table ---
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = inspector.get_table_names()

    if "packages" not in existing:
        packages_table = op.create_table(
            "packages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(), unique=True, nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("monthly_limit", sa.Integer(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default="1"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

        # Seed default packages
        op.bulk_insert(packages_table, [
            {"name": "Trans-S", "category": "transaction", "monthly_limit": 500, "description": "Transaktional bis 500 E-Mails/Monat"},
            {"name": "Trans-M", "category": "transaction", "monthly_limit": 1000, "description": "Transaktional bis 1.000 E-Mails/Monat"},
            {"name": "Trans-L", "category": "transaction", "monthly_limit": 5000, "description": "Transaktional bis 5.000 E-Mails/Monat"},
            {"name": "News-S", "category": "newsletter", "monthly_limit": 5000, "description": "Newsletter bis 5.000 E-Mails/Monat"},
            {"name": "News-M", "category": "newsletter", "monthly_limit": 10000, "description": "Newsletter bis 10.000 E-Mails/Monat"},
            {"name": "News-L", "category": "newsletter", "monthly_limit": 25000, "description": "Newsletter bis 25.000 E-Mails/Monat"},
            {"name": "News-XL", "category": "newsletter", "monthly_limit": 50000, "description": "Newsletter bis 50.000 E-Mails/Monat"},
            {"name": "Ext-1K", "category": "overage", "monthly_limit": 1000, "description": "Zusatzpaket 1.000 E-Mails"},
        ])

    # --- user_monthly_usage table ---
    if "user_monthly_usage" not in existing:
        op.create_table(
            "user_monthly_usage",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("smtp_user_id", sa.Integer(), sa.ForeignKey("smtp_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("year_month", sa.String(7), nullable=False),
            sa.Column("sent_count", sa.Integer(), server_default="0"),
            sa.Column("last_updated", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("smtp_user_id", "year_month", name="uq_user_month"),
        )

    # --- billing_reports table ---
    if "billing_reports" not in existing:
        op.create_table(
            "billing_reports",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("year_month", sa.String(7), nullable=False),
            sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("sent_to", sa.String(), nullable=True),
            sa.Column("report_data", sa.Text(), nullable=False),
        )

    # --- add package_id to smtp_users ---
    columns = [c["name"] for c in inspector.get_columns("smtp_users")]
    if "package_id" not in columns:
        # SQLite doesn't support ALTER with FK constraints, so add plain column
        op.add_column("smtp_users", sa.Column("package_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("smtp_users", "package_id")
    op.drop_table("billing_reports")
    op.drop_table("user_monthly_usage")
    op.drop_table("packages")
