"""SMTP Users CRUD router.

Manages SMTP authentication users (SASL). All endpoints require admin privileges.
Every mutation syncs the Dovecot passwd-file and logs an audit entry.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import SmtpUser, AuditLog, User
from app.schemas import SmtpUserCreate, SmtpUserOut, SmtpUserWithPassword, SmtpUserUpdate
from app.services.crypto_service import generate_smtp_password, encrypt_password, decrypt_password
from app.services.sasl_service import sync_dovecot_users
from app.services.pdf_service import generate_config_pdf
from app.services.postfix_service import read_main_cf

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_smtp_host() -> str:
    """Read SMTP hostname from postfix config."""
    config = read_main_cf()
    return config.get("myhostname", "relay.example.com")


def _audit(db: Session, admin: User, action: str, details: str, request: Request):
    db.add(AuditLog(
        user_id=admin.id,
        action=action,
        details=details,
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()


@router.get("", response_model=list[SmtpUserOut])
def list_smtp_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(SmtpUser).order_by(SmtpUser.id).all()


@router.post("", response_model=SmtpUserWithPassword, status_code=201)
def create_smtp_user(
    body: SmtpUserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(SmtpUser).filter(SmtpUser.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="SMTP-Benutzername existiert bereits")

    password = generate_smtp_password()

    user = SmtpUser(
        username=body.username,
        password_encrypted=encrypt_password(password),
        is_active=True,
        company=body.company,
        service=body.service,
        created_by=admin.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _audit(db, admin, "smtp_user_created", f"Created SMTP user '{body.username}'", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after creating user: {msg}")

    return SmtpUserWithPassword(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        company=user.company,
        service=user.service,
        created_at=user.created_at,
        created_by=user.created_by,
        password=password,
    )


@router.put("/{user_id}", response_model=SmtpUserOut)
def update_smtp_user(
    user_id: int,
    body: SmtpUserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.company is not None:
        user.company = body.company
    if body.service is not None:
        user.service = body.service

    db.commit()
    db.refresh(user)

    _audit(db, admin, "smtp_user_updated", f"SMTP user '{user.username}' updated", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after updating user: {msg}")

    return user


@router.post("/{user_id}/regenerate-password", response_model=SmtpUserWithPassword)
def regenerate_password(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    password = generate_smtp_password()
    user.password_encrypted = encrypt_password(password)
    db.commit()
    db.refresh(user)

    _audit(db, admin, "smtp_user_password_regenerated",
           f"Regenerated password for SMTP user '{user.username}'", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after password regeneration: {msg}")

    return SmtpUserWithPassword(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        company=user.company,
        service=user.service,
        created_at=user.created_at,
        created_by=user.created_by,
        password=password,
    )


@router.delete("/{user_id}", status_code=204)
def delete_smtp_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    username = user.username
    db.delete(user)
    db.commit()

    _audit(db, admin, "smtp_user_deleted", f"Deleted SMTP user '{username}'", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after deleting user: {msg}")


@router.get("/{user_id}/config-pdf")
def download_config_pdf(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    try:
        password = decrypt_password(user.password_encrypted)
    except Exception:
        raise HTTPException(status_code=500, detail="Passwort konnte nicht entschluesselt werden")

    smtp_host = _get_smtp_host()
    pdf_bytes = generate_config_pdf(
        user.username, password, smtp_host,
        company=user.company, service=user.service,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="smtp-config-{user.username}.pdf"',
        },
    )
