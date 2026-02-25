"""Throttle & warmup API router.

All endpoints require admin privileges. Mutations log audit entries.
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import AuditLog, User, TransportRule, WarmupPhase
from app.schemas import (
    ThrottleConfigOut,
    ThrottleConfigUpdate,
    ThrottleMetrics,
    TransportRuleCreate,
    TransportRuleOut,
    TransportRuleUpdate,
    WarmupPhaseOut,
    WarmupPhaseUpdate,
    WarmupStatus,
)
from app.services.throttle_service import (
    get_all_config,
    get_throttle_enabled,
    set_throttle_enabled,
    set_config,
    get_warmup_status,
    get_current_warmup_phase,
    get_sent_today,
    get_sent_this_hour,
    get_held_count,
)
from app.services.transport_generator import (
    apply_throttle_config,
    generate_transport_map,
    generate_master_cf_transports,
)
from app.services.docker_service import reload_postfix

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


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@router.get("/config", response_model=ThrottleConfigOut)
def get_config_endpoint(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cfg = get_all_config(db)
    return ThrottleConfigOut(
        enabled=cfg.get("enabled", "false").lower() == "true",
        warmup_start_date=cfg.get("warmup_start_date", ""),
        batch_interval_minutes=int(cfg.get("batch_interval_minutes", "10")),
    )


@router.put("/config")
def update_config_endpoint(
    body: ThrottleConfigUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    steps = []

    if body.batch_interval_minutes is not None:
        set_config(db, "batch_interval_minutes", str(body.batch_interval_minutes))

    if body.enabled is not None:
        was_enabled = get_throttle_enabled(db)
        set_throttle_enabled(db, body.enabled)

        if body.enabled != was_enabled:
            steps = apply_throttle_config(db, body.enabled)
            action = "throttle_enabled" if body.enabled else "throttle_disabled"
            _audit(db, admin, action, f"Drosselung {'aktiviert' if body.enabled else 'deaktiviert'}", request)

    return {"message": "Konfiguration aktualisiert", "steps": steps}


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------

@router.get("/warmup", response_model=WarmupStatus)
def get_warmup_endpoint(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return get_warmup_status(db)


@router.put("/warmup/phase")
def set_warmup_phase(
    request: Request,
    phase_number: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phase = db.query(WarmupPhase).filter(WarmupPhase.phase_number == phase_number).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase nicht gefunden")

    set_config(db, "warmup_phase_override", str(phase_number))
    _audit(db, admin, "warmup_phase_set", f"Phase manuell auf {phase.name} gesetzt", request)
    return {"message": f"Phase auf '{phase.name}' gesetzt"}


@router.put("/warmup/reset")
def reset_warmup(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    set_config(db, "warmup_start_date", str(date.today()))
    # Remove manual override
    set_config(db, "warmup_phase_override", "")
    _audit(db, admin, "warmup_reset", "Warmup zurueckgesetzt", request)
    return {"message": "Warmup zurueckgesetzt"}


@router.get("/warmup/phases", response_model=list[WarmupPhaseOut])
def list_warmup_phases(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(WarmupPhase).order_by(WarmupPhase.phase_number).all()


@router.put("/warmup/phases/{phase_id}", response_model=WarmupPhaseOut)
def update_warmup_phase(
    phase_id: int,
    body: WarmupPhaseUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phase = db.query(WarmupPhase).filter(WarmupPhase.id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase nicht gefunden")

    if body.name is not None:
        phase.name = body.name
    if body.duration_days is not None:
        phase.duration_days = body.duration_days
    if body.max_per_hour is not None:
        phase.max_per_hour = body.max_per_hour
    if body.max_per_day is not None:
        phase.max_per_day = body.max_per_day
    if body.burst_limit is not None:
        phase.burst_limit = body.burst_limit

    db.commit()
    db.refresh(phase)
    _audit(db, admin, "warmup_phase_updated", f"Phase '{phase.name}' aktualisiert", request)
    return phase


# ---------------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------------

@router.get("/transports", response_model=list[TransportRuleOut])
def list_transports(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(TransportRule).order_by(TransportRule.id).all()


@router.post("/transports", response_model=TransportRuleOut, status_code=201)
def create_transport(
    body: TransportRuleCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(TransportRule).filter(
        TransportRule.domain_pattern == body.domain_pattern
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain-Pattern existiert bereits")

    rule = TransportRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)

    _audit(db, admin, "transport_created", f"Transport '{body.domain_pattern}' erstellt", request)

    # Regenerate maps if throttling is active
    if get_throttle_enabled(db):
        generate_transport_map(db)
        generate_master_cf_transports(db)
        reload_postfix()

    return rule


@router.put("/transports/{rule_id}", response_model=TransportRuleOut)
def update_transport(
    rule_id: int,
    body: TransportRuleUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rule = db.query(TransportRule).filter(TransportRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Transport-Regel nicht gefunden")

    if body.domain_pattern is not None:
        rule.domain_pattern = body.domain_pattern
    if body.transport_name is not None:
        rule.transport_name = body.transport_name
    if body.concurrency_limit is not None:
        rule.concurrency_limit = body.concurrency_limit
    if body.rate_delay_seconds is not None:
        rule.rate_delay_seconds = body.rate_delay_seconds
    if body.is_active is not None:
        rule.is_active = body.is_active
    if body.description is not None:
        rule.description = body.description

    db.commit()
    db.refresh(rule)
    _audit(db, admin, "transport_updated", f"Transport '{rule.domain_pattern}' aktualisiert", request)

    if get_throttle_enabled(db):
        generate_transport_map(db)
        generate_master_cf_transports(db)
        reload_postfix()

    return rule


@router.delete("/transports/{rule_id}", status_code=204)
def delete_transport(
    rule_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rule = db.query(TransportRule).filter(TransportRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Transport-Regel nicht gefunden")

    domain = rule.domain_pattern
    db.delete(rule)
    db.commit()
    _audit(db, admin, "transport_deleted", f"Transport '{domain}' geloescht", request)

    if get_throttle_enabled(db):
        generate_transport_map(db)
        generate_master_cf_transports(db)
        reload_postfix()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@router.get("/metrics", response_model=ThrottleMetrics)
def get_metrics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phase = get_current_warmup_phase(db)
    return ThrottleMetrics(
        sent_today=get_sent_today(db),
        sent_this_hour=get_sent_this_hour(db),
        held_count=get_held_count(),
        limits={
            "max_per_hour": phase.max_per_hour,
            "max_per_day": phase.max_per_day,
            "burst_limit": phase.burst_limit,
        },
    )
