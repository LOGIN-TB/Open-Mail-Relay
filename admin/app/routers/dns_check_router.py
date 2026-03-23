"""DNS Record Checker API — SPF, DMARC, DKIM validation."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AuditLog
from app.schemas import DnsCheckSettings, DnsCheckResult, DnsCheckStatus
from app.services.dns_check_service import (
    get_dns_check_settings, run_dns_check, get_dns_check_status,
    get_dkim_public_key, delete_dkim_key, get_dkim_selector,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=DnsCheckSettings)
def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dns_check_settings(db)


@router.post("/check", response_model=DnsCheckResult)
def trigger_check(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = run_dns_check(db)
    db.add(AuditLog(
        user_id=user.id,
        action="dns_check_triggered",
        details=f"DNS-Pruefung ausgefuehrt: {result.get('overall_status', '')}",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return result


@router.get("/status", response_model=DnsCheckStatus)
def dns_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_dns_check_status(db)


@router.get("/dkim-key")
def dkim_key(
    user: User = Depends(get_current_user),
):
    selector = get_dkim_selector()
    return get_dkim_public_key(selector)


@router.delete("/dkim-key")
def dkim_key_delete(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selector = get_dkim_selector()
    deleted = delete_dkim_key(selector)
    if deleted:
        db.add(AuditLog(
            user_id=user.id,
            action="dkim_key_deleted",
            details=f"DKIM-Schluessel geloescht (Selector: {selector}). Wird beim naechsten Container-Neustart neu generiert.",
            ip_address=request.client.host if request.client else None,
        ))
        db.commit()
    return {"deleted": deleted, "selector": selector}
