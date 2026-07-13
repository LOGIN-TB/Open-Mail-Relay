from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


# --- Throttling ---

class ThrottleConfig(Base):
    __tablename__ = "throttle_config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TransportRule(Base):
    __tablename__ = "transport_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_pattern = Column(String, unique=True, nullable=False, index=True)
    transport_name = Column(String, nullable=False)
    concurrency_limit = Column(Integer, nullable=False, default=5)
    rate_delay_seconds = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)


class WarmupPhase(Base):
    __tablename__ = "warmup_phases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phase_number = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    duration_days = Column(Integer, nullable=False)
    max_per_hour = Column(Integer, nullable=False)
    max_per_day = Column(Integer, nullable=False)
    burst_limit = Column(Integer, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)


class MailEvent(Base):
    __tablename__ = "mail_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    queue_id = Column(String, index=True)
    sender = Column(String)
    recipient = Column(String)
    status = Column(String, nullable=False, index=True)  # sent, deferred, bounced, rejected, auth_failed
    relay = Column(String)
    delay = Column(Float)
    dsn = Column(String)
    size = Column(Integer)
    message = Column(Text)
    client_ip = Column(String)
    sasl_username = Column(String)
    dsn_code = Column(String, nullable=True)
    remote_response = Column(Text, nullable=True)


class StatsHourly(Base):
    __tablename__ = "stats_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hour_start = Column(DateTime, unique=True, nullable=False, index=True)
    sent_count = Column(Integer, default=0)
    deferred_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    auth_failed_count = Column(Integer, default=0)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False)  # transaction, newsletter, overage, portal
    monthly_limit = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    # Set = mirrored from the portal's plan catalogue (portal is the leading
    # system; local edits get overwritten by the next sync).
    portal_plan_code = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=func.now())


class SmtpUser(Base):
    __tablename__ = "smtp_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    # Legacy credential store (reversible). NULL for hash-only users; kept
    # during the portal migration so existing credentials stay valid.
    password_encrypted = Column(String, nullable=True)  # Fernet-encrypted
    # Dovecot-ready hash, e.g. "{SHA512-CRYPT}$6$...". Takes precedence over
    # password_encrypted in the passwd-file sync.
    password_hash = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    company = Column(String, nullable=True)
    service = Column(String, nullable=True)
    mail_domain = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    receive_reports = Column(Boolean, default=True, nullable=False, server_default="1")
    # R3 (Portal-API 2.7.0): the portal sends False as soon as its own monthly
    # reports are live — suppresses this relay's automatic usage reports for
    # the user (effective = receive_reports AND monthly_report_enabled).
    monthly_report_enabled = Column(Boolean, default=True, nullable=False, server_default="1")
    # R1 (Portal-API 2.7.0): portal-pushed monthly send limit (trial cap, plan
    # limit incl. released extra packs). Overrides the package limit; NULL =
    # package limit (or unlimited without a package). Enforced by the policy
    # server when quota_enforcement_enabled is on.
    monthly_limit_override = Column(Integer, nullable=True)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="SET NULL"), nullable=True)
    # Provisioning ownership: 'local' = created on this relay (admin UI),
    # 'portal' = provisioned by the central portal (control plane).
    origin = Column(String, nullable=False, default="local", server_default="local")
    portal_managed = Column(Boolean, nullable=False, default=False, server_default="0")
    portal_access_id = Column(String, nullable=True)  # portal smtp_accesses UUID
    # JSON array of sender domains this user may use (domain binding).
    allowed_domains = Column(Text, nullable=True)
    # JSON array — subset of allowed_domains that is ENFORCED: these domains
    # go into the Postfix sender_login_maps (reject_known_sender_login_mismatch
    # rejects only mapped domains; unmapped = monitor = unrestricted).
    enforced_domains = Column(Text, nullable=True)
    # Sender-binding rollout stage: 'monitor' (log only) | 'enforce' (reject).
    # Display info derived from enforced_domains since migration 017.
    enforcement_mode = Column(String, nullable=False, default="monitor", server_default="monitor")
    created_at = Column(DateTime, default=func.now())
    # Touched on every mutation (admin UI and portal API alike) — the portal
    # reconciler uses this for incremental inventory sync.
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_used_at = Column(DateTime, nullable=True)


class UserMonthlyUsage(Base):
    __tablename__ = "user_monthly_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    smtp_user_id = Column(Integer, ForeignKey("smtp_users.id", ondelete="CASCADE"), nullable=False)
    year_month = Column(String, nullable=False)
    sent_count = Column(Integer, default=0)
    last_updated = Column(DateTime, nullable=True)


class BillingReport(Base):
    __tablename__ = "billing_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_month = Column(String, nullable=False)
    generated_at = Column(DateTime, default=func.now())
    sent_to = Column(String, nullable=True)
    report_data = Column(Text, nullable=False)


class Network(Base):
    __tablename__ = "networks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cidr = Column(String, unique=True, nullable=False, index=True)
    owner = Column(String, default="")
    is_protected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


class IpBan(Base):
    __tablename__ = "ip_bans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String, unique=True, nullable=False, index=True)
    reason = Column(String, nullable=False)  # sasl_auth_failed, relay_rejected, manual
    ban_count = Column(Integer, default=1)
    fail_count = Column(Integer, default=0)
    first_fail_at = Column(DateTime, nullable=True)
    banned_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # NULL = permanent/manual
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    notes = Column(String, default="")


class ProviderBlock(Base):
    """A provider-internal sending block detected from bounce/deferred logs.

    Unlike RBL listings (queried actively via DNS), these blocks are only
    visible in the NDR text returned by large mailbox providers
    (Microsoft/Outlook, Google, Yahoo, T-Online, …). One row per
    (provider, blocked_ip) — the outbound relay IP that the provider rejected.
    """
    __tablename__ = "provider_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False, index=True)  # microsoft, google, yahoo, t-online, united-internet, other
    provider_label = Column(String, nullable=False, default="")
    blocked_ip = Column(String, nullable=False, index=True)  # our outbound IP the provider blocked
    relay_host = Column(String, default="")  # sample remote MX host, e.g. *.protection.outlook.com
    block_code = Column(String, default="")  # provider code if present, e.g. S3140
    sample_response = Column(Text, default="")  # the remote NDR text
    sample_queue_id = Column(String, default="")
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True, index=True)
    hit_count = Column(Integer, default=1)
    status = Column(String, nullable=False, default="active", index=True)  # active, resolved, acknowledged
    delisting_submitted_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notes = Column(String, default="")
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "blocked_ip", name="uq_provider_block_ip"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text)
    ip_address = Column(String)
