"""Provider-Block API — settings, manual scan, block list, delisting actions, test email."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AuditLog, ProviderBlock
from app.schemas import (
    ProviderBlockSettings, ProviderBlockSettingsUpdate, ProviderBlockOut,
    ProviderBlockScanResult, ProviderBlockStatus, ProviderBlockDelisting,
)
from app.services.provider_block_service import (
    get_settings, update_settings, run_scan, list_blocks, get_status,
    send_test_email, delisting_for,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_out(b: ProviderBlock) -> ProviderBlockOut:
    out = ProviderBlockOut.model_validate(b)
    d = delisting_for(
        b.provider, b.blocked_ip, b.relay_host or "",
        b.block_code or "", b.sample_response or "",
    )
    out.delisting = ProviderBlockDelisting(**d)
    return out


@router.get("", response_model=ProviderBlockSettings)
def get_settings_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_settings(db)


@router.put("", response_model=ProviderBlockSettings)
def update_settings_endpoint(
    body: ProviderBlockSettingsUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_settings(db, body.model_dump(exclude_none=True))
    db.add(AuditLog(
        user_id=user.id,
        action="provider_block_settings_updated",
        details="Provider-Sperren Einstellungen aktualisiert",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return result


@router.get("/status", response_model=ProviderBlockStatus)
def status_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_status(db)


@router.get("/blocks", response_model=list[ProviderBlockOut])
def list_blocks_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [_to_out(b) for b in list_blocks(db)]


@router.post("/scan", response_model=ProviderBlockScanResult)
def scan_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = run_scan(db)
    db.add(AuditLog(
        user_id=user.id,
        action="provider_block_scan_triggered",
        details=f"Manueller Provider-Block-Scan: {result['new_blocks']} neu, {result['active_count']} aktiv",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return result


@router.post("/blocks/{block_id}/submitted", response_model=ProviderBlockOut)
def mark_submitted(
    block_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(ProviderBlock).filter(ProviderBlock.id == block_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sperre nicht gefunden")
    row.delisting_submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AuditLog(
        user_id=user.id,
        action="provider_block_delisting_submitted",
        details=f"Delisting beantragt: {row.provider_label} / {row.blocked_ip}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/blocks/{block_id}/resolve", response_model=ProviderBlockOut)
def mark_resolved(
    block_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(ProviderBlock).filter(ProviderBlock.id == block_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sperre nicht gefunden")
    row.status = "resolved"
    row.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AuditLog(
        user_id=user.id,
        action="provider_block_resolved",
        details=f"Sperre manuell als aufgehoben markiert: {row.provider_label} / {row.blocked_ip}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/test-email")
def test_email(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success = send_test_email(db)
    if success:
        db.add(AuditLog(
            user_id=user.id,
            action="provider_block_test_email",
            details="Provider-Sperren Test-Mail gesendet",
            ip_address=request.client.host if request.client else None,
        ))
        db.commit()
    return {"success": success}
