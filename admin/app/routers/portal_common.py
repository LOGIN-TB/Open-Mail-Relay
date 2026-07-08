"""Portal API — shared helpers, settings access and auth middleware.

All portal endpoints require IP-whitelist + API-key authentication via middleware.
Settings (API key, allowed IPs) are managed via the admin UI and stored in SystemSetting.
"""

import ipaddress
import logging
import secrets
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import SystemSetting
from app.services.postfix_service import read_main_cf

logger = logging.getLogger(__name__)

PORTAL_DEFAULTS = {
    "portal_api_key": "",
    "portal_allowed_ips": "",
    # Kill switch for the v1 provisioning API: all writes return 403 until
    # this is deliberately enabled per relay ("1") in the admin UI.
    "portal_provisioning_enabled": "",
}


def provisioning_enabled(db: Session) -> bool:
    return _get_portal_setting(db, "portal_provisioning_enabled") == "1"


# ---------------------------------------------------------------------------
# Settings helpers (SystemSetting-backed)
# ---------------------------------------------------------------------------

def _get_portal_setting(db: Session, key: str) -> str:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else PORTAL_DEFAULTS.get(key, "")


def _set_portal_setting(db: Session, key: str, value: str) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    _invalidate_portal_settings_cache()


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

# Settings cache: avoid a DB session + two queries on every portal request.
_PORTAL_SETTINGS_CACHE_TTL = 30  # seconds
_portal_settings_cache: tuple[float, str, str] | None = None  # (expires, key, ips)

# Brute-force guard: failed auth attempts per client IP (sliding window)
_PORTAL_FAIL_WINDOW = 60  # seconds
_PORTAL_FAIL_LIMIT = 30
_portal_failed_auth: dict[str, list[float]] = {}


def _invalidate_portal_settings_cache() -> None:
    global _portal_settings_cache
    _portal_settings_cache = None


def _get_cached_portal_auth() -> tuple[str, str]:
    """Return (api_key, allowed_ips_raw), cached with a short TTL."""
    global _portal_settings_cache
    now = time.monotonic()
    if _portal_settings_cache and _portal_settings_cache[0] > now:
        return _portal_settings_cache[1], _portal_settings_cache[2]
    db = SessionLocal()
    try:
        api_key = _get_portal_setting(db, "portal_api_key")
        allowed_ips = _get_portal_setting(db, "portal_allowed_ips")
    finally:
        db.close()
    _portal_settings_cache = (now + _PORTAL_SETTINGS_CACHE_TTL, api_key, allowed_ips)
    return api_key, allowed_ips


def _portal_client_ip(request: Request) -> str:
    """Determine the real client IP.

    Only trust X-Forwarded-For when the direct peer is a private address
    (i.e. the Caddy reverse proxy on the Docker network) — otherwise a
    direct caller could spoof a whitelisted IP via the header.
    """
    peer_ip = request.client.host if request.client else ""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        try:
            if ipaddress.ip_address(peer_ip).is_private:
                return forwarded_for.split(",")[0].strip()
        except ValueError:
            pass
    return peer_ip


def _portal_too_many_failures(client_ip: str) -> bool:
    now = time.monotonic()
    attempts = [t for t in _portal_failed_auth.get(client_ip, []) if now - t < _PORTAL_FAIL_WINDOW]
    _portal_failed_auth[client_ip] = attempts
    return len(attempts) >= _PORTAL_FAIL_LIMIT


def _portal_record_failure(client_ip: str) -> None:
    _portal_failed_auth.setdefault(client_ip, []).append(time.monotonic())


async def portal_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/portal"):
        # Skip auth for the admin settings endpoints
        if request.url.path.startswith("/api/portal-settings"):
            return await call_next(request)

        try:
            api_key_db, allowed_ips_raw = _get_cached_portal_auth()
        except Exception:
            logger.exception("Portal auth: failed to load settings")
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        allowed_ips = set(
            ip.strip() for ip in allowed_ips_raw.split(",") if ip.strip()
        )

        client_ip = _portal_client_ip(request)
        if _portal_too_many_failures(client_ip):
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})

        api_key = request.headers.get("X-Portal-API-Key", "")

        ip_ok = bool(allowed_ips) and client_ip in allowed_ips
        key_ok = bool(api_key_db) and secrets.compare_digest(api_key, api_key_db)
        if not (ip_ok and key_ok):
            _portal_record_failure(client_ip)
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    return await call_next(request)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_hostname() -> str:
    """Read myhostname from Postfix config."""
    cf = read_main_cf()
    return cf.get("myhostname", "unknown")
