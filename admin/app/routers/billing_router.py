"""Billing router — package management, monthly billing overview, report endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User, SmtpUser
from app.schemas import (
    PackageCreate, PackageOut, PackageUpdate,
    BillingOverview, BillingSettings, BillingSettingsUpdate,
)
from app.services.billing_service import (
    get_all_packages, create_package, update_package, delete_package,
    get_billing_overview, refresh_monthly_usage,
    generate_billing_report, send_billing_report,
    get_billing_settings, update_billing_settings,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Packages ---

@router.get("/packages", response_model=list[PackageOut])
def list_packages(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return get_all_packages(db)


@router.post("/packages", response_model=PackageOut, status_code=201)
def create_pkg(
    body: PackageCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return create_package(db, body.name, body.category, body.monthly_limit, body.description)


@router.put("/packages/{package_id}", response_model=PackageOut)
def update_pkg(
    package_id: int,
    body: PackageUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    pkg = update_package(db, package_id, **body.model_dump(exclude_unset=True))
    if not pkg:
        raise HTTPException(status_code=404, detail="Paket nicht gefunden")
    return pkg


@router.delete("/packages/{package_id}", status_code=204)
def delete_pkg(
    package_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    success = delete_package(db, package_id)
    if not success:
        assigned = db.query(SmtpUser).filter(SmtpUser.package_id == package_id).count()
        if assigned > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Paket ist noch {assigned} Benutzer(n) zugewiesen",
            )
        raise HTTPException(status_code=404, detail="Paket nicht gefunden")


# --- Billing Overview ---

@router.get("/overview", response_model=BillingOverview)
def billing_overview(
    year_month: str = Query(default=None, description="Format: YYYY-MM"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if year_month is None:
        year_month = datetime.now().strftime("%Y-%m")
    return get_billing_overview(db, year_month)


@router.post("/overview/refresh")
def refresh_overview(
    year_month: str = Query(default=None, description="Format: YYYY-MM"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if year_month is None:
        year_month = datetime.now().strftime("%Y-%m")
    refresh_monthly_usage(db, year_month)
    return {"status": "ok", "year_month": year_month}


# --- Reports ---

@router.get("/report/{year_month}")
def get_report(
    year_month: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    refresh_monthly_usage(db, year_month)
    return get_billing_overview(db, year_month)


@router.post("/report/{year_month}/send")
def send_report(
    year_month: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    success = send_billing_report(db, year_month)
    if not success:
        raise HTTPException(status_code=500, detail="Bericht konnte nicht gesendet werden. E-Mail-Einstellungen pruefen.")
    return {"status": "ok", "year_month": year_month}


# --- Settings ---

def _settings_to_response(raw: dict) -> dict:
    """Convert raw string settings to typed response."""
    result = dict(raw)
    result["usage_report_enabled"] = result.get("usage_report_enabled", "true") == "true"
    return result


@router.get("/settings", response_model=BillingSettings)
def get_settings(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _settings_to_response(get_billing_settings(db))


@router.put("/settings", response_model=BillingSettings)
def save_settings(
    body: BillingSettingsUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    # Convert bool to string for storage
    if "usage_report_enabled" in data and data["usage_report_enabled"] is not None:
        data["usage_report_enabled"] = "true" if data["usage_report_enabled"] else "false"
    return _settings_to_response(update_billing_settings(db, **data))
