"""Portal API — readonly endpoints for external customer portal (my.spamgo.de).

All endpoints require IP-whitelist + API-key authentication via middleware.
The only write endpoint is password reset.
Settings (API key, allowed IPs) are managed via the admin UI and stored in SystemSetting.
"""

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db, SessionLocal
from app.dependencies import require_admin
from app.models import SmtpUser, MailEvent, Package, SystemSetting, AuditLog, User
from app.services.crypto_service import generate_smtp_password, encrypt_password, decrypt_password
from app.services.dns_check_service import (
    check_spf, check_dmarc, check_dkim, get_dkim_selector,
    get_server_info as dns_get_server_info,
)
from app.services.pdf_service import generate_config_pdf
from app.services.postfix_service import read_main_cf
from app.services.rbl_service import (
    get_rbl_status as rbl_get_status,
    get_server_info as rbl_get_server_info,
    get_rbl_settings,
)
from app.services.sasl_service import sync_dovecot_users
from app.services.spf_check_service import check_customer_spf
from app.services.abuse_service import get_abuse_settings

logger = logging.getLogger(__name__)

VERSION = "2.1.0"

PORTAL_DEFAULTS = {
    "portal_api_key": "",
    "portal_allowed_ips": "",
}


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


# ---------------------------------------------------------------------------
# Auth middleware (reads from DB on each request)
# ---------------------------------------------------------------------------

async def portal_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/portal"):
        # Skip auth for the admin settings endpoints
        if request.url.path.startswith("/api/portal-settings"):
            return await call_next(request)

        try:
            db = SessionLocal()
            try:
                api_key_db = _get_portal_setting(db, "portal_api_key")
                allowed_ips_raw = _get_portal_setting(db, "portal_allowed_ips")
            finally:
                db.close()
        except Exception:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        allowed_ips = set(
            ip.strip() for ip in allowed_ips_raw.split(",") if ip.strip()
        )

        client_ip = request.client.host
        # Caddy reverse proxy sends X-Forwarded-For
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        api_key = request.headers.get("X-Portal-API-Key", "")

        if not allowed_ips or client_ip not in allowed_ips:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        if not api_key_db or api_key != api_key_db:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    return await call_next(request)


# ---------------------------------------------------------------------------
# Portal API Router (external portal endpoints)
# ---------------------------------------------------------------------------

router = APIRouter()


def _get_hostname() -> str:
    """Read myhostname from Postfix config."""
    cf = read_main_cf()
    return cf.get("myhostname", "unknown")


# ---------------------------------------------------------------------------
# 1. Health Check
# ---------------------------------------------------------------------------

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "server": _get_hostname(),
        "version": VERSION,
    }


# ---------------------------------------------------------------------------
# 2. Lookup (customer search by contact_email)
# ---------------------------------------------------------------------------

@router.get("/lookup")
def lookup(
    email: str = Query(..., description="Contact email to search for"),
    db: Session = Depends(get_db),
):
    users = (
        db.query(SmtpUser)
        .filter(func.lower(SmtpUser.contact_email) == email.lower())
        .order_by(SmtpUser.id)
        .all()
    )
    return {
        "server": _get_hostname(),
        "matches": [
            {
                "smtp_user_id": u.id,
                "username": u.username,
                "company": u.company,
                "service": u.service,
                "mail_domain": u.mail_domain,
                "is_active": u.is_active,
            }
            for u in users
        ],
    }


# ---------------------------------------------------------------------------
# 3. Stats per SMTP user
# ---------------------------------------------------------------------------

def _count_status(rows, status: str) -> int:
    return sum(1 for r in rows if r.status == status)


@router.get("/stats/{smtp_user_id}")
def get_stats(smtp_user_id: int, db: Session = Depends(get_db)):
    user = db.query(SmtpUser).filter(SmtpUser.id == smtp_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP user not found")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # --- Today ---
    today_events = (
        db.query(MailEvent)
        .filter(
            MailEvent.sasl_username == user.username,
            MailEvent.timestamp >= today_start,
            MailEvent.status.in_(["sent", "deferred", "bounced", "rejected"]),
        )
        .all()
    )
    sent_today = _count_status(today_events, "sent")
    deferred_today = _count_status(today_events, "deferred")
    bounced_today = _count_status(today_events, "bounced")
    rejected_today = _count_status(today_events, "rejected")
    total_today = len(today_events)
    success_rate = round(sent_today / total_today * 100, 1) if total_today > 0 else 100.0

    # --- History 24h (hourly) ---
    h24_start = now - timedelta(hours=24)
    h24_events = (
        db.query(MailEvent)
        .filter(
            MailEvent.sasl_username == user.username,
            MailEvent.timestamp >= h24_start,
            MailEvent.status.in_(["sent", "deferred", "bounced", "rejected"]),
        )
        .all()
    )
    hourly: dict[str, dict] = {}
    for ev in h24_events:
        hour_key = ev.timestamp.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        if hour_key not in hourly:
            hourly[hour_key] = {"hour": hour_key, "sent": 0, "deferred": 0, "bounced": 0, "rejected": 0}
        hourly[hour_key][ev.status] = hourly[hour_key].get(ev.status, 0) + 1
    history_24h = sorted(hourly.values(), key=lambda x: x["hour"])

    # --- History 30d (daily) ---
    d30_start = now - timedelta(days=30)
    d30_events = (
        db.query(MailEvent)
        .filter(
            MailEvent.sasl_username == user.username,
            MailEvent.timestamp >= d30_start,
            MailEvent.status.in_(["sent", "deferred", "bounced", "rejected"]),
        )
        .all()
    )
    daily: dict[str, dict] = {}
    for ev in d30_events:
        day_key = ev.timestamp.strftime("%Y-%m-%d")
        if day_key not in daily:
            daily[day_key] = {"date": day_key, "sent": 0, "deferred": 0, "bounced": 0, "rejected": 0}
        daily[day_key][ev.status] = daily[day_key].get(ev.status, 0) + 1
    history_30d = sorted(daily.values(), key=lambda x: x["date"])

    return {
        "smtp_user_id": user.id,
        "username": user.username,
        "today": {
            "sent": sent_today,
            "deferred": deferred_today,
            "bounced": bounced_today,
            "rejected": rejected_today,
            "success_rate": success_rate,
        },
        "history_24h": history_24h,
        "history_30d": history_30d,
        "quota": None,
    }


# ---------------------------------------------------------------------------
# 4. DNS Check for SMTP user's mail_domain
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    "pass": "ok",
    "fail": "error",
    "missing": "missing",
    "warn": "warning",
    "error": "error",
}


@router.get("/dns-check/{smtp_user_id}")
def dns_check(smtp_user_id: int, db: Session = Depends(get_db)):
    user = db.query(SmtpUser).filter(SmtpUser.id == smtp_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP user not found")
    if not user.mail_domain:
        raise HTTPException(status_code=400, detail="No mail_domain configured for this user")

    info = dns_get_server_info()
    server_ip = info["ip"]
    hostname = info["hostname"]
    selector = get_dkim_selector()

    spf = check_spf(user.mail_domain, server_ip, hostname)
    dmarc = check_dmarc(user.mail_domain)
    dkim = check_dkim(user.mail_domain, selector)

    return {
        "domain": user.mail_domain,
        "spf": {
            "status": _STATUS_MAP.get(spf["status"], spf["status"]),
            "record": spf["record"],
            "server_authorized": spf["status"] == "pass",
            "suggestion": spf["suggested_record"],
        },
        "dkim": {
            "status": _STATUS_MAP.get(dkim["status"], dkim["status"]),
            "selector": selector,
            "record_found": dkim["status"] == "pass",
            "suggestion": dkim["suggested_record"],
        },
        "dmarc": {
            "status": _STATUS_MAP.get(dmarc["status"], dmarc["status"]),
            "record": dmarc["record"],
            "policy": _extract_dmarc_policy(dmarc["record"]),
            "suggestion": dmarc["suggested_record"],
        },
    }


def _extract_dmarc_policy(record: str | None) -> str | None:
    if not record:
        return None
    for part in record.replace(";", " ").split():
        if part.startswith("p="):
            return part.split("=", 1)[1]
    return None


# ---------------------------------------------------------------------------
# 5. Password Reset
# ---------------------------------------------------------------------------

@router.post("/reset-password/{smtp_user_id}")
def reset_password(smtp_user_id: int, db: Session = Depends(get_db)):
    user = db.query(SmtpUser).filter(SmtpUser.id == smtp_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP user not found")

    password = generate_smtp_password()
    user.password_encrypted = encrypt_password(password)
    db.commit()
    db.refresh(user)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning("Dovecot sync failed after portal password reset: %s", msg)

    return {
        "smtp_user_id": user.id,
        "username": user.username,
        "new_password": password,
    }


# ---------------------------------------------------------------------------
# 6. Config PDF
# ---------------------------------------------------------------------------

@router.get("/config-pdf/{smtp_user_id}")
def get_config_pdf(smtp_user_id: int, db: Session = Depends(get_db)):
    user = db.query(SmtpUser).filter(SmtpUser.id == smtp_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP user not found")

    try:
        password = decrypt_password(user.password_encrypted)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not decrypt password")

    smtp_host = _get_hostname()

    # SPF check for customer domain
    spf_info = None
    if user.mail_domain:
        parts = smtp_host.split(".")
        relay_domain = ".".join(parts[1:]) if len(parts) > 2 else smtp_host
        try:
            spf_info = check_customer_spf(user.mail_domain, relay_domain)
        except Exception as e:
            logger.warning("SPF check failed for %s: %s", user.mail_domain, e)

    # Operator info
    operator_info = None
    try:
        abuse = get_abuse_settings(db)
        responsible = abuse.get("abuse_responsible", "")
        email = abuse.get("postmaster_email", "")
        phone = abuse.get("abuse_phone", "")
        if responsible or email or phone:
            operator_info = {"responsible": responsible, "email": email, "phone": phone}
    except Exception as e:
        logger.warning("Failed to load operator info: %s", e)

    # Package name
    pkg_name = None
    if user.package_id:
        pkg = db.query(Package).filter(Package.id == user.package_id).first()
        pkg_name = pkg.name if pkg else None

    pdf_bytes = generate_config_pdf(
        user.username, password, smtp_host,
        company=user.company, service=user.service,
        mail_domain=user.mail_domain, contact_email=user.contact_email,
        package_name=pkg_name,
        spf_info=spf_info, operator_info=operator_info,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="smtp-config-{user.username}.pdf"',
        },
    )


# ---------------------------------------------------------------------------
# 7. RBL Status
# ---------------------------------------------------------------------------

@router.get("/rbl-status")
def rbl_status(db: Session = Depends(get_db)):
    info = rbl_get_server_info()
    status = rbl_get_status(db)
    settings = get_rbl_settings(db)

    # Parse cached listings
    listings = []
    try:
        result_data = json.loads(settings.get("rbl_last_results", "{}"))
        for r in result_data.get("results", []):
            for listing in r.get("listings", []):
                listings.append({
                    "rbl_name": listing.get("rbl_name", ""),
                    "rbl_zone": listing.get("rbl_zone", ""),
                })
    except (json.JSONDecodeError, AttributeError):
        pass

    return {
        "server_ip": info.get("ip", ""),
        "status": "clean" if status.get("all_clean") else "listed",
        "last_checked": settings.get("rbl_last_check_time", ""),
        "listings": listings,
    }


# ---------------------------------------------------------------------------
# Admin Settings Router (auth-protected, for admin UI)
# ---------------------------------------------------------------------------

settings_router = APIRouter()


@settings_router.get("")
def get_portal_settings(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    api_key = _get_portal_setting(db, "portal_api_key")
    allowed_ips = _get_portal_setting(db, "portal_allowed_ips")

    # Build copyable config block
    admin_hostname = app_settings.ADMIN_HOSTNAME
    relay_hostname = _get_hostname()
    api_url = f"https://{admin_hostname}/api/portal" if admin_hostname else ""

    return {
        "api_key": api_key,
        "allowed_ips": allowed_ips,
        "api_url": api_url,
        "server_hostname": relay_hostname,
    }


@settings_router.put("")
def update_portal_settings(
    request: Request,
    body: dict,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    allowed_keys = {"portal_allowed_ips"}
    for key, value in body.items():
        if key in allowed_keys:
            _set_portal_setting(db, key, str(value))

    db.add(AuditLog(
        user_id=admin.id,
        action="portal_settings_updated",
        details="Portal-API Einstellungen aktualisiert",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return get_portal_settings(admin=admin, db=db)


@settings_router.post("/generate-key")
def generate_portal_key(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    new_key = secrets.token_hex(32)
    _set_portal_setting(db, "portal_api_key", new_key)

    db.add(AuditLog(
        user_id=admin.id,
        action="portal_api_key_generated",
        details="Neuer Portal-API-Schluessel generiert",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return get_portal_settings(admin=admin, db=db)
