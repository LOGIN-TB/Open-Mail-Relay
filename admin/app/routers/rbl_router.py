"""RBL Checker API — settings, manual check trigger, server info, test email."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AuditLog
from app.schemas import RblSettings, RblSettingsUpdate, RblCheckResult, RblServerInfo, RblStatus
from app.services.rbl_service import (
    get_rbl_settings, update_rbl_settings, run_rbl_check,
    get_server_info, send_test_email, get_rbl_status,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=RblSettings)
def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_rbl_settings(db)


@router.put("", response_model=RblSettings)
def update_settings(
    body: RblSettingsUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_rbl_settings(db, body.model_dump(exclude_none=True))
    db.add(AuditLog(
        user_id=user.id,
        action="rbl_settings_updated",
        details="RBL-Pruefung Einstellungen aktualisiert",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return result


@router.post("/check", response_model=RblCheckResult)
def trigger_check(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = run_rbl_check(db)
    db.add(AuditLog(
        user_id=user.id,
        action="rbl_check_triggered",
        details="Manuelle RBL-Pruefung ausgeloest",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return result


@router.get("/server-info", response_model=RblServerInfo)
def server_info(
    user: User = Depends(get_current_user),
):
    return get_server_info()


@router.get("/status", response_model=RblStatus)
def rbl_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_rbl_status(db)


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
            action="rbl_test_email",
            details="RBL Test-Mail gesendet",
            ip_address=request.client.host if request.client else None,
        ))
        db.commit()
    return {"success": success}
