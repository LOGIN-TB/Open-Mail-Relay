from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, ForeignKey
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
    status = Column(String, nullable=False, index=True)  # sent, deferred, bounced, rejected
    relay = Column(String)
    delay = Column(Float)
    dsn = Column(String)
    size = Column(Integer)
    message = Column(Text)


class StatsHourly(Base):
    __tablename__ = "stats_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hour_start = Column(DateTime, unique=True, nullable=False, index=True)
    sent_count = Column(Integer, default=0)
    deferred_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class SmtpUser(Base):
    __tablename__ = "smtp_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_encrypted = Column(String, nullable=False)  # Fernet-encrypted
    is_active = Column(Boolean, default=True)
    company = Column(String, nullable=True)
    service = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text)
    ip_address = Column(String)
