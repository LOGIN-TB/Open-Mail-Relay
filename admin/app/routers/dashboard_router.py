from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, MailEvent, StatsHourly
from app.schemas import DashboardStats, QueueEntry, MailEventOut, ChartData
from app.services.postfix_service import get_queue, get_queue_size

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    counts = (
        db.query(MailEvent.status, func.count(MailEvent.id))
        .filter(MailEvent.timestamp >= today_start)
        .group_by(MailEvent.status)
        .all()
    )

    stats = {status: count for status, count in counts}
    sent = stats.get("sent", 0)
    total = sum(stats.values())

    return DashboardStats(
        sent_today=sent,
        deferred_today=stats.get("deferred", 0),
        bounced_today=stats.get("bounced", 0),
        rejected_today=stats.get("rejected", 0),
        auth_failed_today=stats.get("auth_failed", 0),
        queue_size=get_queue_size(),
        success_rate=round((sent / total * 100) if total > 0 else 0, 1),
    )


@router.get("/queue", response_model=list[QueueEntry])
def get_queue_entries(user: User = Depends(get_current_user)):
    return get_queue()


@router.get("/activity", response_model=list[MailEventOut])
def get_activity(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    offset = (page - 1) * per_page
    events = (
        db.query(MailEvent)
        .order_by(MailEvent.timestamp.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )
    return events


@router.get("/chart", response_model=ChartData)
def get_chart_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    stats = (
        db.query(StatsHourly)
        .filter(StatsHourly.hour_start >= since)
        .order_by(StatsHourly.hour_start)
        .all()
    )

    labels = []
    sent = []
    deferred = []
    bounced = []
    rejected = []
    auth_failed = []

    for s in stats:
        labels.append(s.hour_start.strftime("%H:%M"))
        sent.append(s.sent_count)
        deferred.append(s.deferred_count)
        bounced.append(s.bounced_count)
        rejected.append(s.rejected_count)
        auth_failed.append(s.auth_failed_count or 0)

    return ChartData(
        labels=labels,
        sent=sent,
        deferred=deferred,
        bounced=bounced,
        rejected=rejected,
        auth_failed=auth_failed,
    )
