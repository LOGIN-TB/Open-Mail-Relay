import asyncio
import csv
import io
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import MailEvent, SystemSetting, User
from app.schemas import PaginatedMailEvents, MailEventOut, RetentionSettings, RetentionUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_event_query(db: Session, status: str | None, search: str | None,
                       date_from: datetime | None, date_to: datetime | None):
    query = db.query(MailEvent)
    if status:
        query = query.filter(MailEvent.status == status)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (MailEvent.sender.ilike(like)) | (MailEvent.recipient.ilike(like))
        )
    if date_from:
        query = query.filter(MailEvent.timestamp >= date_from)
    if date_to:
        query = query.filter(MailEvent.timestamp <= date_to)
    return query


@router.get("/events", response_model=PaginatedMailEvents)
def get_events(
    status: str | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _build_event_query(db, status, search, date_from, date_to)
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    items = (
        query.order_by(MailEvent.timestamp.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return PaginatedMailEvents(
        items=[MailEventOut.model_validate(e) for e in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/events/export")
def export_events(
    status: str | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _build_event_query(db, status, search, date_from, date_to)
    events = query.order_by(MailEvent.timestamp.desc()).limit(10000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Zeitpunkt", "Status", "Queue-ID", "Absender", "Empfaenger",
                     "Relay", "Delay", "DSN", "Groesse", "Nachricht"])
    for e in events:
        writer.writerow([
            e.timestamp.isoformat() if e.timestamp else "",
            e.status, e.queue_id or "", e.sender or "", e.recipient or "",
            e.relay or "", e.delay or "", e.dsn or "", e.size or "", e.message or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mail_events.csv"},
    )


@router.get("/retention", response_model=RetentionSettings)
def get_retention(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    retention_days = settings.LOG_RETENTION_DAYS
    stats_retention_days = settings.STATS_RETENTION_DAYS

    row = db.query(SystemSetting).filter(SystemSetting.key == "retention_days").first()
    if row:
        retention_days = int(row.value)
    row = db.query(SystemSetting).filter(SystemSetting.key == "stats_retention_days").first()
    if row:
        stats_retention_days = int(row.value)

    return RetentionSettings(retention_days=retention_days, stats_retention_days=stats_retention_days)


@router.put("/retention", response_model=RetentionSettings)
def update_retention(
    body: RetentionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    for key, val in [("retention_days", body.retention_days), ("stats_retention_days", body.stats_retention_days)]:
        if val is not None:
            row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if row:
                row.value = str(val)
            else:
                db.add(SystemSetting(key=key, value=str(val)))
    db.commit()

    return get_retention(db=db, user=user)


@router.websocket("/stream")
async def log_stream(websocket: WebSocket, token: str = Query(...)):
    # Authenticate via query parameter (WebSocket can't use headers easily)
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()

    from app.services.log_broadcaster import broadcaster

    queue = broadcaster.subscribe()
    try:
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(line)
            except asyncio.TimeoutError:
                # No log lines for 30s — send WebSocket ping to detect dead connections
                try:
                    await websocket.send_bytes(b"")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        broadcaster.unsubscribe(queue)
