from datetime import datetime

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

class NetworkEntry(BaseModel):
    cidr: str
    description: str = ""

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        ipaddress.ip_network(v, strict=False)
        return str(ipaddress.ip_network(v, strict=False))


class NetworkList(BaseModel):
    networks: list[str]


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

    model_config = {"from_attributes": True}


class ChartData(BaseModel):
    labels: list[str]
    sent: list[int]
    deferred: list[int]
    bounced: list[int]
    rejected: list[int]


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


# --- Audit ---

class AuditLogOut(BaseModel):
    id: int
    timestamp: datetime
    user_id: int | None
    action: str
    details: str | None
    ip_address: str | None

    model_config = {"from_attributes": True}
