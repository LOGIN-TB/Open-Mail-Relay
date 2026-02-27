"""Public abuse page + admin settings API."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AuditLog
from app.schemas import AbuseSettings, AbuseSettingsUpdate
from app.services.abuse_service import get_abuse_settings, update_abuse_settings, render_abuse_html

# Public router — no auth, served at /public/abuse
public_router = APIRouter()

# Admin router — auth required, mounted under /api/abuse-settings
admin_router = APIRouter()


@public_router.get("/public/abuse", response_class=HTMLResponse)
def serve_abuse_page(db: Session = Depends(get_db)):
    html = render_abuse_html(db)
    return HTMLResponse(content=html)


@admin_router.get("", response_model=AbuseSettings)
def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_abuse_settings(db)


@admin_router.put("", response_model=AbuseSettings)
def update_settings(
    body: AbuseSettingsUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_abuse_settings(db, body.model_dump(exclude_none=True))
    db.add(AuditLog(
        user_id=user.id,
        action="abuse_settings_updated",
        details="Abuse-Seite Einstellungen aktualisiert",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return result
