"""Portal Provisioning API v1 — write endpoints for the central portal.

The portal (control plane) provisions SMTP users on this relay (data plane):
idempotent upsert, adoption of existing local users, credential rotation and
soft-disable. Read inventory supports the portal's reconciliation loop.

Auth: same middleware as the legacy portal API (IP whitelist + API key, see
app.routers.portal_common). Additionally ALL write endpoints require the
per-relay kill switch `portal_provisioning_enabled` (SystemSetting, default
off) — a deploy of this code is inert until the switch is enabled in the
admin UI. Every write is recorded in the audit log (actor "portal").

Credentials are hash-only here: the portal sends a Dovecot-ready
{SHA512-CRYPT} hash, never a plaintext password, and no endpoint ever
returns password material.
"""

import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Package, SmtpUser
from app.routers.portal_common import _get_hostname, _portal_client_ip, provisioning_enabled
from app.schemas import (
    PortalAdoptRequest,
    PortalCredentialsRequest,
    PortalUpsertRequest,
)
from app.services.crypto_service import decrypt_password, hash_smtp_password
from app.services.sasl_service import sync_dovecot_users
from app.services.quota_service import quota_checker
from app.services.sender_maps_service import sync_sender_maps

logger = logging.getLogger(__name__)

API_VERSION = 1
FEATURES = ["hash_auth", "adopt", "domain_binding", "monthly_report_flag", "limit_override", "quota_enforcement", "load_metric"]

USERNAME_RE = re.compile(r"^[a-z0-9_-]{4,16}$")

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audit(db: Session, request: Request, action: str, details: str) -> None:
    db.add(AuditLog(
        user_id=None,  # actor is the portal, not an admin-panel operator
        action=action,
        details=f"[portal] {details}",
        ip_address=_portal_client_ip(request),
    ))
    db.commit()


def _require_provisioning(db: Session) -> None:
    if not provisioning_enabled(db):
        raise HTTPException(
            status_code=403,
            detail="Provisioning ist auf diesem Relay deaktiviert (portal_provisioning_enabled)",
        )


def _resolve_package(db: Session, package_name: str | None) -> Package | None:
    if not package_name:
        return None
    pkg = db.query(Package).filter(Package.name == package_name).first()
    if not pkg:
        raise HTTPException(status_code=400, detail=f"Unbekanntes Paket: {package_name}")
    return pkg


def _user_out(user: SmtpUser, pkg_map: dict[int, Package]) -> dict:
    pkg = pkg_map.get(user.package_id) if user.package_id else None
    return {
        "username": user.username,
        "is_active": bool(user.is_active),
        "origin": user.origin,
        "portal_managed": bool(user.portal_managed),
        "portal_access_id": user.portal_access_id,
        "package": {
            "id": pkg.id,
            "name": pkg.name,
            "category": pkg.category,
            "monthly_limit": pkg.monthly_limit,
        } if pkg else None,
        "contact_email": user.contact_email,
        "company": user.company,
        "service": user.service,
        "mail_domain": user.mail_domain,
        "allowed_domains": json.loads(user.allowed_domains) if user.allowed_domains else None,
        "enforced_domains": json.loads(user.enforced_domains) if user.enforced_domains else None,
        "enforcement_mode": user.enforcement_mode,
        "monthly_limit_override": user.monthly_limit_override,
        "monthly_report_enabled": bool(user.monthly_report_enabled),
        "has_plaintext": user.password_encrypted is not None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _sync_dovecot_or_500(db: Session) -> None:
    success, msg = sync_dovecot_users(db)
    if not success:
        # The DB row is committed; the reconciler / next mutation will retry
        # the file sync. Surface the failure so the portal marks the access.
        logger.error(f"Dovecot sync failed after portal provisioning: {msg}")
        raise HTTPException(status_code=502, detail=f"Dovecot-Sync fehlgeschlagen: {msg}")
    # Domain binding: enforced_domains / is_active feed the sender map.
    # No-op while the feature switch is off; failures only logged (the map
    # regenerates on the next mutation or toggle).
    sync_sender_maps(db)


# ---------------------------------------------------------------------------
# 1. Capabilities (version discovery — legacy relays return 404 here)
# ---------------------------------------------------------------------------

@router.get("/capabilities")
def capabilities(db: Session = Depends(get_db)):
    return {
        "api_version": API_VERSION,
        "provisioning": True,
        "features": FEATURES,
        "provisioning_enabled": provisioning_enabled(db),
        "server": _get_hostname(),
    }


# ---------------------------------------------------------------------------
# 2. Inventory (reconciliation source; never returns password material)
# ---------------------------------------------------------------------------

@router.get("/smtp-users")
def list_smtp_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1, le=500),
    updated_since: str | None = Query(None, description="ISO timestamp; only users mutated after this"),
    db: Session = Depends(get_db),
):
    query = db.query(SmtpUser)
    if updated_since:
        try:
            since = datetime.fromisoformat(updated_since)
        except ValueError:
            raise HTTPException(status_code=400, detail="updated_since ist kein gueltiger ISO-Zeitstempel")
        if since.tzinfo is not None:
            # DB timestamps are naive UTC (SQLite CURRENT_TIMESTAMP).
            since = since.astimezone(timezone.utc).replace(tzinfo=None)
        query = query.filter(SmtpUser.updated_at > since)

    total = query.count()
    users = (
        query.order_by(SmtpUser.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    pkg_ids = {u.package_id for u in users if u.package_id}
    pkg_map: dict[int, Package] = {}
    if pkg_ids:
        pkg_map = {p.id: p for p in db.query(Package).filter(Package.id.in_(pkg_ids)).all()}

    return {
        "server": _get_hostname(),
        "page": page,
        "per_page": per_page,
        "total": total,
        "items": [_user_out(u, pkg_map) for u in users],
    }


# ---------------------------------------------------------------------------
# 3. Packages (read-only mirror source; package CRUD stays admin-only)
# ---------------------------------------------------------------------------

@router.get("/packages")
def list_packages(db: Session = Depends(get_db)):
    packages = db.query(Package).order_by(Package.id).all()
    return {
        "server": _get_hostname(),
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "monthly_limit": p.monthly_limit,
                "is_active": bool(p.is_active),
            }
            for p in packages
        ],
    }


# ---------------------------------------------------------------------------
# 4. Upsert (idempotent; the portal's primary push path)
# ---------------------------------------------------------------------------

@router.put("/smtp-users/{username}")
def upsert_smtp_user(
    username: str,
    body: PortalUpsertRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_provisioning(db)

    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        raise HTTPException(status_code=400, detail="Ungueltiger Benutzername (4-16 Zeichen, a-z 0-9 - _)")

    pkg = _resolve_package(db, body.package_name) if body.package_name is not None else None

    user = db.query(SmtpUser).filter(SmtpUser.username == username).first()
    created = user is None
    if created:
        if not body.password_hash:
            raise HTTPException(status_code=400, detail="password_hash ist beim Anlegen erforderlich")
        user = SmtpUser(username=username, origin="portal")
        db.add(user)

    user.portal_managed = True
    user.portal_access_id = body.portal_access_id
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password_hash is not None:
        user.password_hash = body.password_hash
        user.password_encrypted = None  # hash-only from now on
    if body.package_name is not None:
        user.package_id = pkg.id if pkg else None
    if body.contact_email is not None:
        user.contact_email = body.contact_email or None
    if body.company is not None:
        user.company = body.company or None
    if body.service is not None:
        user.service = body.service or None
    if body.mail_domain is not None:
        user.mail_domain = body.mail_domain or None
    if body.allowed_domains is not None:
        user.allowed_domains = json.dumps(body.allowed_domains) if body.allowed_domains else None
    if body.enforced_domains is not None:
        user.enforced_domains = json.dumps(body.enforced_domains) if body.enforced_domains else None
        user.enforcement_mode = "enforce" if body.enforced_domains else "monitor"
    elif body.enforcement_mode is not None:
        user.enforcement_mode = body.enforcement_mode
    # Omitted = untouched; explicit null clears the override (R1).
    if "monthly_limit_override" in body.model_fields_set:
        user.monthly_limit_override = body.monthly_limit_override
    if body.monthly_report_enabled is not None:
        user.monthly_report_enabled = body.monthly_report_enabled
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    quota_checker.clear()
    _audit(db, request, "portal_smtp_user_upserted",
           f"{'Created' if created else 'Updated'} SMTP user '{username}' (access {body.portal_access_id})")

    _sync_dovecot_or_500(db)

    return {"username": user.username, "created": created,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None}


# ---------------------------------------------------------------------------
# 5. Adopt (migration: mark a local user portal-managed, hash locally)
# ---------------------------------------------------------------------------

@router.post("/smtp-users/{username}/adopt")
def adopt_smtp_user(
    username: str,
    body: PortalAdoptRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_provisioning(db)

    user = db.query(SmtpUser).filter(SmtpUser.username == username.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    # Hash the existing Fernet plaintext LOCALLY — it never leaves the relay
    # and the customer's credentials stay valid (no forced password change).
    # password_encrypted is kept until phase F as legacy fallback (config PDF).
    if not user.password_hash:
        if not user.password_encrypted:
            raise HTTPException(status_code=409, detail="Benutzer hat kein Passwort — Adopt nicht moeglich")
        try:
            plain = decrypt_password(user.password_encrypted)
        except Exception:
            raise HTTPException(status_code=500, detail="Bestandspasswort konnte nicht entschluesselt werden")
        user.password_hash = hash_smtp_password(plain)

    pkg = _resolve_package(db, body.package_name) if body.package_name is not None else None

    user.portal_managed = True
    user.portal_access_id = body.portal_access_id
    if body.package_name is not None:
        user.package_id = pkg.id if pkg else None
    if body.allowed_domains is not None:
        user.allowed_domains = json.dumps(body.allowed_domains) if body.allowed_domains else None
    if body.enforced_domains is not None:
        user.enforced_domains = json.dumps(body.enforced_domains) if body.enforced_domains else None
        user.enforcement_mode = "enforce" if body.enforced_domains else "monitor"
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    _audit(db, request, "portal_smtp_user_adopted",
           f"Adopted SMTP user '{user.username}' (access {body.portal_access_id})")

    _sync_dovecot_or_500(db)

    return {"username": user.username, "portal_managed": True,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None}


# ---------------------------------------------------------------------------
# 6. Credential rotation (portal generated + hashed; never retried)
# ---------------------------------------------------------------------------

@router.post("/smtp-users/{username}/credentials")
def rotate_credentials(
    username: str,
    body: PortalCredentialsRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_provisioning(db)

    user = db.query(SmtpUser).filter(SmtpUser.username == username.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    user.password_hash = body.password_hash
    user.password_encrypted = None  # hash-only from now on
    user.updated_at = datetime.utcnow()

    db.commit()

    _audit(db, request, "portal_smtp_credentials_rotated",
           f"Rotated credentials for SMTP user '{user.username}'")

    _sync_dovecot_or_500(db)

    return {"username": user.username,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None}


# ---------------------------------------------------------------------------
# 7. Disable (soft — mail events / billing history stay intact)
# ---------------------------------------------------------------------------

@router.delete("/smtp-users/{username}")
def disable_smtp_user(
    username: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_provisioning(db)

    user = db.query(SmtpUser).filter(SmtpUser.username == username.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()

    _audit(db, request, "portal_smtp_user_disabled",
           f"Disabled SMTP user '{user.username}'")

    _sync_dovecot_or_500(db)

    return {"username": user.username, "is_active": False,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None}
