"""Portal API — admin settings endpoints (auth-protected, for admin UI).

Settings (API key, allowed IPs) are stored in SystemSetting and consumed by
the portal auth middleware in portal_common.
"""

import secrets

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.dependencies import require_admin
from app.models import AuditLog, User
from app.services.sender_maps_service import apply_sender_maps_config, get_sender_maps_enabled
from app.routers.portal_common import (
    _get_hostname,
    _get_portal_setting,
    _set_portal_setting,
)

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
    provisioning_enabled = _get_portal_setting(db, "portal_provisioning_enabled") == "1"
    sender_maps_enabled = get_sender_maps_enabled(db)

    # Build copyable config block
    admin_hostname = app_settings.ADMIN_HOSTNAME
    relay_hostname = _get_hostname()
    api_url = f"https://{admin_hostname}/api/portal" if admin_hostname else ""

    return {
        "api_key": api_key,
        "allowed_ips": allowed_ips,
        "api_url": api_url,
        "server_hostname": relay_hostname,
        "provisioning_enabled": provisioning_enabled,
        "sender_maps_enabled": sender_maps_enabled,
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

    # Kill switch for the v1 provisioning API (bool → "1"/"" in SystemSetting).
    if "provisioning_enabled" in body:
        _set_portal_setting(db, "portal_provisioning_enabled", "1" if body["provisioning_enabled"] else "")

    # Domain binding (sender_login_maps): toggling applies the full Postfix
    # config (marker + postconf + reload) — like the throttle switch.
    if "sender_maps_enabled" in body and bool(body["sender_maps_enabled"]) != get_sender_maps_enabled(db):
        steps = apply_sender_maps_config(db, bool(body["sender_maps_enabled"]))
        db.add(AuditLog(
            user_id=admin.id,
            action="sender_maps_toggled",
            details=f"Domain-Bindung {'aktiviert' if body['sender_maps_enabled'] else 'deaktiviert'}: "
                    + "; ".join(f"{st['step']}={'OK' if st['success'] else st['detail']}" for st in steps),
            ip_address=request.client.host if request.client else None,
        ))
        db.commit()

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
