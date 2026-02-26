"""IP Bans CRUD router.

Manages automatic and manual IP blocking. All endpoints require admin privileges.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import IpBan, AuditLog, User
from app.schemas import IpBanCreate, IpBanOut, IpBanUpdate, IpBanSettings
from app.services.ban_service import (
    manual_ban,
    unban_ip,
    get_ban_settings,
    update_ban_settings,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _audit(db: Session, admin: User, action: str, details: str, request: Request):
    db.add(AuditLog(
        user_id=admin.id,
        action=action,
        details=details,
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()


@router.get("", response_model=list[IpBanOut])
def list_ip_bans(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all IP bans, active first."""
    return (
        db.query(IpBan)
        .order_by(IpBan.is_active.desc(), IpBan.banned_at.desc(), IpBan.created_at.desc())
        .all()
    )


@router.post("", response_model=IpBanOut, status_code=201)
def create_ip_ban(
    body: IpBanCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually ban an IP address (permanent)."""
    existing = db.query(IpBan).filter(IpBan.ip_address == body.ip_address).first()
    if existing and existing.is_active:
        raise HTTPException(status_code=400, detail="IP ist bereits gesperrt")

    manual_ban(db, body.ip_address, body.reason, body.notes)
    _audit(db, admin, "ip_banned", f"Manually banned IP {body.ip_address}: {body.reason}", request)

    ban = db.query(IpBan).filter(IpBan.ip_address == body.ip_address).first()
    return ban


# Settings routes MUST come before /{ban_id} to avoid path parameter conflicts
@router.get("/settings", response_model=IpBanSettings)
def get_settings(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get current ban threshold settings."""
    cfg = get_ban_settings(db)
    return IpBanSettings(**cfg)


@router.put("/settings", response_model=IpBanSettings)
def update_settings(
    body: IpBanSettings,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update ban threshold settings."""
    update_ban_settings(db, body.max_attempts, body.time_window_minutes, body.ban_durations)
    _audit(db, admin, "ip_ban_settings_updated",
           f"Ban settings: max={body.max_attempts}, window={body.time_window_minutes}min", request)
    return body


@router.put("/{ban_id}", response_model=IpBanOut)
def update_ip_ban(
    ban_id: int,
    body: IpBanUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update notes on an IP ban."""
    ban = db.query(IpBan).filter(IpBan.id == ban_id).first()
    if not ban:
        raise HTTPException(status_code=404, detail="IP-Sperre nicht gefunden")

    ban.notes = body.notes
    db.commit()
    db.refresh(ban)
    _audit(db, admin, "ip_ban_updated", f"Updated notes for IP {ban.ip_address}", request)
    return ban


@router.delete("/{ban_id}", status_code=204)
def delete_ip_ban(
    ban_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unban an active IP or delete an inactive ban record entirely."""
    ban = db.query(IpBan).filter(IpBan.id == ban_id).first()
    if not ban:
        raise HTTPException(status_code=404, detail="IP-Sperre nicht gefunden")

    ip = ban.ip_address
    if ban.is_active:
        unban_ip(db, ban_id)
        _audit(db, admin, "ip_unbanned", f"Unbanned IP {ip}", request)
    else:
        db.delete(ban)
        db.commit()
        _audit(db, admin, "ip_ban_deleted", f"Deleted ban record for IP {ip}", request)
