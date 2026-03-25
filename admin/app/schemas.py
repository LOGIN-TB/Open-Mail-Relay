import re
from datetime import datetime, timezone

from pydantic import BaseModel, field_validator
import ipaddress


# --- Auth ---

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime | None = None
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    password: str | None = None
    is_admin: bool | None = None


# --- Networks ---

class NetworkCreate(BaseModel):
    cidr: str
    owner: str = ""

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        ipaddress.ip_network(v, strict=False)
        return str(ipaddress.ip_network(v, strict=False))


class NetworkOut(BaseModel):
    id: int
    cidr: str
    owner: str
    is_protected: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class NetworkUpdate(BaseModel):
    owner: str


# --- Config ---

class ServerConfig(BaseModel):
    hostname: str
    domain: str
    relay_domains: str
    message_size_limit: int
    mynetworks_count: int


class ServerConfigUpdate(BaseModel):
    hostname: str | None = None
    domain: str | None = None


class TlsStatus(BaseModel):
    enabled: bool
    cert_exists: bool
    cert_expiry: datetime | None = None
    cert_subject: str | None = None
    postfix_has_cert: bool = False


class PortInfo(BaseModel):
    port: int
    protocol: str
    tls_mode: str
    tls_required: bool = False


class ConnectionInfo(BaseModel):
    smtp_host: str
    ports: list[PortInfo] = []
    auth_required: bool = False
    tls_available: bool = False
    allowed_networks: list[str] = []
    max_message_size_mb: int = 50


# --- Dashboard ---

class DashboardStats(BaseModel):
    sent_today: int = 0
    deferred_today: int = 0
    bounced_today: int = 0
    rejected_today: int = 0
    auth_failed_today: int = 0
    queue_size: int = 0
    success_rate: float = 0.0


class QueueEntry(BaseModel):
    queue_id: str
    size: str
    arrival_time: str
    sender: str
    recipients: list[str]


class MailEventOut(BaseModel):
    id: int
    timestamp: datetime
    queue_id: str | None = None
    sender: str | None = None
    recipient: str | None = None
    status: str
    relay: str | None = None
    delay: float | None = None
    dsn: str | None = None
    size: int | None = None
    message: str | None = None
    client_ip: str | None = None
    sasl_username: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class ChartData(BaseModel):
    labels: list[str]
    sent: list[int]
    deferred: list[int]
    bounced: list[int]
    rejected: list[int]
    auth_failed: list[int]


# --- Protokoll / Events ---

class PaginatedMailEvents(BaseModel):
    items: list[MailEventOut]
    total: int
    page: int
    per_page: int
    pages: int


class RetentionSettings(BaseModel):
    retention_days: int
    stats_retention_days: int


class RetentionUpdate(BaseModel):
    retention_days: int | None = None
    stats_retention_days: int | None = None


class TimezoneSettings(BaseModel):
    timezone: str


class TimezoneUpdate(BaseModel):
    timezone: str


# --- SMTP Users ---

class SmtpUserCreate(BaseModel):
    username: str
    company: str | None = None
    service: str | None = None
    mail_domain: str | None = None
    contact_email: str | None = None
    receive_reports: bool = True
    package_id: int | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]{4,16}$", v):
            raise ValueError("Benutzername muss 4-16 Zeichen lang sein (Buchstaben, Ziffern, - und _)")
        return v

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if v == "":
                return None
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
                raise ValueError("Ungueltige E-Mail-Adresse")
        return v


class SmtpUserOut(BaseModel):
    id: int
    username: str
    is_active: bool
    company: str | None = None
    service: str | None = None
    mail_domain: str | None = None
    contact_email: str | None = None
    receive_reports: bool = True
    package_id: int | None = None
    package_name: str | None = None
    created_at: datetime | None = None
    created_by: int | None = None
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class SmtpUserWithPassword(SmtpUserOut):
    password: str


class SmtpUserUpdate(BaseModel):
    is_active: bool | None = None
    company: str | None = None
    service: str | None = None
    mail_domain: str | None = None
    contact_email: str | None = None
    receive_reports: bool | None = None
    package_id: int | None = None

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if v == "":
                return None
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
                raise ValueError("Ungueltige E-Mail-Adresse")
        return v


# --- Audit ---

class AuditLogOut(BaseModel):
    id: int
    timestamp: datetime
    user_id: int | None
    action: str
    details: str | None
    ip_address: str | None

    model_config = {"from_attributes": True}


# --- Throttling ---

class ThrottleConfigOut(BaseModel):
    enabled: bool = False
    warmup_start_date: str = ""
    batch_interval_minutes: int = 10


class ThrottleConfigUpdate(BaseModel):
    enabled: bool | None = None
    batch_interval_minutes: int | None = None


class TransportRuleOut(BaseModel):
    id: int
    domain_pattern: str
    transport_name: str
    concurrency_limit: int
    rate_delay_seconds: int
    is_active: bool
    description: str | None = None

    model_config = {"from_attributes": True}


class TransportRuleCreate(BaseModel):
    domain_pattern: str
    transport_name: str
    concurrency_limit: int = 5
    rate_delay_seconds: int = 1
    is_active: bool = True
    description: str | None = None

    @field_validator("domain_pattern")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Domain-Pattern darf nicht leer sein")
        return v

    @field_validator("transport_name")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("Transport-Name darf nur Kleinbuchstaben, Ziffern und Unterstriche enthalten")
        return v


class TransportRuleUpdate(BaseModel):
    domain_pattern: str | None = None
    transport_name: str | None = None
    concurrency_limit: int | None = None
    rate_delay_seconds: int | None = None
    is_active: bool | None = None
    description: str | None = None


class WarmupPhaseOut(BaseModel):
    id: int
    phase_number: int
    name: str
    duration_days: int
    max_per_hour: int
    max_per_day: int
    burst_limit: int

    model_config = {"from_attributes": True}


class WarmupPhaseUpdate(BaseModel):
    name: str | None = None
    duration_days: int | None = None
    max_per_hour: int | None = None
    max_per_day: int | None = None
    burst_limit: int | None = None


class WarmupLimits(BaseModel):
    max_per_hour: int
    max_per_day: int
    burst_limit: int


class WarmupStatus(BaseModel):
    current_phase: int
    phase_name: str
    days_elapsed: int
    days_remaining: int
    percent_complete: float
    limits: WarmupLimits
    is_established: bool


class ThrottleMetrics(BaseModel):
    sent_today: int = 0
    sent_this_hour: int = 0
    held_count: int = 0
    limits: WarmupLimits | None = None


# --- IP Bans ---

class IpBanCreate(BaseModel):
    ip_address: str
    reason: str = "manual"
    notes: str = ""

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        ipaddress.ip_address(v)
        return v


class IpBanOut(BaseModel):
    id: int
    ip_address: str
    reason: str
    ban_count: int
    fail_count: int
    banned_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime | None = None
    notes: str = ""

    model_config = {"from_attributes": True}


class IpBanUpdate(BaseModel):
    notes: str


class IpBanSettings(BaseModel):
    max_attempts: int = 5
    time_window_minutes: int = 10
    ban_durations: list[int] = [30, 360, 1440, 10080]


# --- Abuse Page ---

class AbuseSettings(BaseModel):
    abuse_email: str = ""
    postmaster_email: str = ""
    abuse_responsible: str = ""
    abuse_phone: str = ""
    abuse_imprint_url: str = ""
    abuse_data_retention: str = ""
    abuse_spam_filtering: str = ""
    abuse_rfc2142: str = ""
    abuse_data_retention_en: str = ""
    abuse_spam_filtering_en: str = ""
    abuse_rfc2142_en: str = ""
    hostname: str = ""
    domain: str = ""


class AbuseSettingsUpdate(BaseModel):
    abuse_email: str | None = None
    postmaster_email: str | None = None
    abuse_responsible: str | None = None
    abuse_phone: str | None = None
    abuse_imprint_url: str | None = None
    abuse_data_retention: str | None = None
    abuse_spam_filtering: str | None = None
    abuse_rfc2142: str | None = None
    abuse_data_retention_en: str | None = None
    abuse_spam_filtering_en: str | None = None
    abuse_rfc2142_en: str | None = None


# --- RBL Checker ---

class RblSettings(BaseModel):
    rbl_enabled: str = "false"
    rbl_servers: str = "[]"
    rbl_check_interval_hours: str = "6"
    rbl_mail_to: str = ""
    rbl_mail_from: str = ""
    rbl_alert_on_change_only: str = "false"
    rbl_dns_timeout: str = "5"
    rbl_last_results: str = "{}"
    rbl_last_check_time: str = ""


class RblSettingsUpdate(BaseModel):
    rbl_enabled: str | None = None
    rbl_servers: str | None = None
    rbl_check_interval_hours: str | None = None
    rbl_mail_to: str | None = None
    rbl_mail_from: str | None = None
    rbl_alert_on_change_only: str | None = None
    rbl_dns_timeout: str | None = None


class RblCheckResult(BaseModel):
    results: list = []
    state: dict = {}
    check_time: str = ""


class RblServerInfo(BaseModel):
    name: str = ""
    ip: str = ""


class RblStatus(BaseModel):
    enabled: bool = False
    last_check_time: str = ""
    total_listings: int = 0
    all_clean: bool = False


# --- DNS Record Checker ---

class DnsCheckRecord(BaseModel):
    type: str = ""
    status: str = ""
    record: str | None = None
    details: str = ""
    suggested_record: str | None = None
    lookup_domain: str = ""


class DnsCheckResult(BaseModel):
    hostname: str = ""
    ip: str = ""
    domain: str = ""
    dkim_selector: str = ""
    spf: DnsCheckRecord | None = None
    dmarc: DnsCheckRecord | None = None
    dkim: DnsCheckRecord | None = None
    overall_status: str = ""
    check_time: str = ""


class DnsCheckSettings(BaseModel):
    dkim_selector: str = "default"
    last_results: DnsCheckResult | None = None
    last_check_time: str = ""


class DnsCheckStatus(BaseModel):
    checked: bool = False
    spf_ok: bool = False
    dmarc_ok: bool = False
    dkim_ok: bool = False
    all_ok: bool = False
    last_check_time: str = ""
    issues: int = 0


# --- Packages / Billing ---

class PackageCreate(BaseModel):
    name: str
    category: str
    monthly_limit: int
    description: str | None = None


class PackageOut(BaseModel):
    id: int
    name: str
    category: str
    monthly_limit: int
    description: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PackageUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    monthly_limit: int | None = None
    description: str | None = None
    is_active: bool | None = None


class BillingOverviewItem(BaseModel):
    smtp_user_id: int
    username: str
    company: str | None = None
    package_name: str | None = None
    package_limit: int | None = None
    sent_count: int = 0
    overage_count: int = 0
    overage_emails: int = 0


class BillingOverview(BaseModel):
    year_month: str
    items: list[BillingOverviewItem]
    total_sent: int = 0
    total_overage_units: int = 0


class BillingSettings(BaseModel):
    billing_report_email: str = ""
    billing_report_from: str = ""
    usage_report_enabled: bool = True
    usage_report_day: str = "monday"


class BillingSettingsUpdate(BaseModel):
    billing_report_email: str | None = None
    billing_report_from: str | None = None
    usage_report_enabled: bool | None = None
    usage_report_day: str | None = None
