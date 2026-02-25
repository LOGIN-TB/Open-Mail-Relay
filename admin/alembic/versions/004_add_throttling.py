"""Add throttling tables (throttle_config, transport_rules, warmup_phases)

Revision ID: 004
Revises: 003
Create Date: 2026-02-25
"""
from datetime import date
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- throttle_config ---
    op.create_table(
        "throttle_config",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- transport_rules ---
    op.create_table(
        "transport_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("domain_pattern", sa.String(), nullable=False),
        sa.Column("transport_name", sa.String(), nullable=False),
        sa.Column("concurrency_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("rate_delay_seconds", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("description", sa.String(), nullable=True),
    )
    op.create_index("ix_transport_rules_domain", "transport_rules", ["domain_pattern"], unique=True)

    # --- warmup_phases ---
    op.create_table(
        "warmup_phases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phase_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("max_per_hour", sa.Integer(), nullable=False),
        sa.Column("max_per_day", sa.Integer(), nullable=False),
        sa.Column("burst_limit", sa.Integer(), nullable=False),
    )
    op.create_index("ix_warmup_phases_number", "warmup_phases", ["phase_number"], unique=True)

    # --- Seed: Default config ---
    config_table = sa.table(
        "throttle_config",
        sa.column("key", sa.String),
        sa.column("value", sa.String),
    )
    op.bulk_insert(config_table, [
        {"key": "enabled", "value": "false"},
        {"key": "warmup_start_date", "value": str(date.today())},
        {"key": "batch_interval_minutes", "value": "10"},
    ])

    # --- Seed: Default warmup phases ---
    phases_table = sa.table(
        "warmup_phases",
        sa.column("phase_number", sa.Integer),
        sa.column("name", sa.String),
        sa.column("duration_days", sa.Integer),
        sa.column("max_per_hour", sa.Integer),
        sa.column("max_per_day", sa.Integer),
        sa.column("burst_limit", sa.Integer),
    )
    op.bulk_insert(phases_table, [
        {"phase_number": 1, "name": "Woche 1-2", "duration_days": 14, "max_per_hour": 20, "max_per_day": 500, "burst_limit": 10},
        {"phase_number": 2, "name": "Woche 3-4", "duration_days": 14, "max_per_hour": 50, "max_per_day": 2000, "burst_limit": 25},
        {"phase_number": 3, "name": "Woche 5-6", "duration_days": 14, "max_per_hour": 100, "max_per_day": 5000, "burst_limit": 50},
        {"phase_number": 4, "name": "Etabliert", "duration_days": 0, "max_per_hour": 500, "max_per_day": 50000, "burst_limit": 200},
    ])

    # --- Seed: Default transport rules ---
    transport_table = sa.table(
        "transport_rules",
        sa.column("domain_pattern", sa.String),
        sa.column("transport_name", sa.String),
        sa.column("concurrency_limit", sa.Integer),
        sa.column("rate_delay_seconds", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("description", sa.String),
    )
    op.bulk_insert(transport_table, [
        {"domain_pattern": "gmail.com", "transport_name": "gmail_throttled", "concurrency_limit": 3, "rate_delay_seconds": 3, "is_active": True, "description": "Google Mail"},
        {"domain_pattern": "googlemail.com", "transport_name": "gmail_throttled", "concurrency_limit": 3, "rate_delay_seconds": 3, "is_active": True, "description": "Google Mail (alt)"},
        {"domain_pattern": "outlook.com", "transport_name": "outlook_throttled", "concurrency_limit": 2, "rate_delay_seconds": 5, "is_active": True, "description": "Microsoft Outlook"},
        {"domain_pattern": "hotmail.com", "transport_name": "outlook_throttled", "concurrency_limit": 2, "rate_delay_seconds": 5, "is_active": True, "description": "Microsoft Hotmail"},
        {"domain_pattern": "live.com", "transport_name": "outlook_throttled", "concurrency_limit": 2, "rate_delay_seconds": 5, "is_active": True, "description": "Microsoft Live"},
        {"domain_pattern": "yahoo.com", "transport_name": "yahoo_throttled", "concurrency_limit": 3, "rate_delay_seconds": 3, "is_active": True, "description": "Yahoo Mail"},
        {"domain_pattern": "yahoo.de", "transport_name": "yahoo_throttled", "concurrency_limit": 3, "rate_delay_seconds": 3, "is_active": True, "description": "Yahoo Mail DE"},
        {"domain_pattern": "*", "transport_name": "default_throttled", "concurrency_limit": 5, "rate_delay_seconds": 1, "is_active": True, "description": "Standard"},
    ])


def downgrade() -> None:
    op.drop_index("ix_warmup_phases_number", table_name="warmup_phases")
    op.drop_table("warmup_phases")
    op.drop_index("ix_transport_rules_domain", table_name="transport_rules")
    op.drop_table("transport_rules")
    op.drop_table("throttle_config")
