"""Throttle service — core logic for rate limiting and warmup tracking."""
import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ThrottleConfig, TransportRule, WarmupPhase, StatsHourly, MailEvent
from app.services.docker_service import exec_in_container

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def get_config(db: Session, key: str, default: str = "") -> str:
    row = db.query(ThrottleConfig).filter(ThrottleConfig.key == key).first()
    return row.value if row else default


def set_config(db: Session, key: str, value: str) -> None:
    row = db.query(ThrottleConfig).filter(ThrottleConfig.key == key).first()
    if row:
        row.value = value
    else:
        db.add(ThrottleConfig(key=key, value=value))
    db.commit()


def get_all_config(db: Session) -> dict[str, str]:
    rows = db.query(ThrottleConfig).all()
    return {r.key: r.value for r in rows}


def get_throttle_enabled(db: Session) -> bool:
    return get_config(db, "enabled", "false").lower() == "true"


def set_throttle_enabled(db: Session, enabled: bool) -> None:
    set_config(db, "enabled", str(enabled).lower())


# ---------------------------------------------------------------------------
# Warmup phase calculation
# ---------------------------------------------------------------------------

def get_current_warmup_phase(db: Session) -> WarmupPhase:
    """Determine the current warmup phase based on start date and phase durations."""
    override = get_config(db, "warmup_phase_override", "")
    if override:
        phase = db.query(WarmupPhase).filter(WarmupPhase.phase_number == int(override)).first()
        if phase:
            return phase

    start_str = get_config(db, "warmup_start_date", str(date.today()))
    try:
        start_date = date.fromisoformat(start_str)
    except ValueError:
        start_date = date.today()

    days_elapsed = (date.today() - start_date).days
    if days_elapsed < 0:
        days_elapsed = 0

    phases = db.query(WarmupPhase).order_by(WarmupPhase.phase_number).all()
    if not phases:
        # Fallback: return a permissive default
        return WarmupPhase(
            phase_number=4, name="Etabliert", duration_days=0,
            max_per_hour=500, max_per_day=50000, burst_limit=200,
        )

    cumulative = 0
    for phase in phases:
        if phase.duration_days == 0:
            # Infinite / final phase
            return phase
        if days_elapsed < cumulative + phase.duration_days:
            return phase
        cumulative += phase.duration_days

    # Past all phases → return last one
    return phases[-1]


def get_warmup_status(db: Session) -> dict:
    """Build the WarmupStatus response dict."""
    start_str = get_config(db, "warmup_start_date", str(date.today()))
    try:
        start_date = date.fromisoformat(start_str)
    except ValueError:
        start_date = date.today()

    days_elapsed = max(0, (date.today() - start_date).days)

    phase = get_current_warmup_phase(db)
    phases = db.query(WarmupPhase).order_by(WarmupPhase.phase_number).all()

    # Compute total warmup duration (excluding final infinite phase)
    total_days = sum(p.duration_days for p in phases if p.duration_days > 0)
    is_established = phase.duration_days == 0

    if is_established:
        percent = 100.0
        days_remaining = 0
    else:
        # Days into current phase
        cumulative_before = sum(
            p.duration_days for p in phases
            if p.phase_number < phase.phase_number and p.duration_days > 0
        )
        days_in_phase = days_elapsed - cumulative_before
        days_remaining_phase = max(0, phase.duration_days - days_in_phase)
        days_remaining = days_remaining_phase + sum(
            p.duration_days for p in phases
            if p.phase_number > phase.phase_number and p.duration_days > 0
        )
        percent = min(100.0, (days_elapsed / total_days * 100) if total_days > 0 else 100.0)

    return {
        "current_phase": phase.phase_number,
        "phase_name": phase.name,
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "percent_complete": round(percent, 1),
        "limits": {
            "max_per_hour": phase.max_per_hour,
            "max_per_day": phase.max_per_day,
            "burst_limit": phase.burst_limit,
        },
        "is_established": is_established,
    }


# ---------------------------------------------------------------------------
# Metrics: sent counts from DB
# ---------------------------------------------------------------------------

def get_sent_today(db: Session) -> int:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(StatsHourly).filter(StatsHourly.hour_start >= today_start).all()
    return sum(r.sent_count for r in rows)


def get_sent_this_hour(db: Session) -> int:
    hour_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    row = db.query(StatsHourly).filter(StatsHourly.hour_start == hour_start).first()
    return row.sent_count if row else 0


def get_held_count() -> int:
    """Parse `mailq` output to count HOLD entries (queue IDs with `!`)."""
    try:
        exit_code, output = exec_in_container("mailq")
        if exit_code != 0:
            return 0
        count = 0
        for line in output.splitlines():
            if line and not line.startswith(" ") and not line.startswith("-") and "!" in line[:20]:
                count += 1
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# In-memory ThrottleCounter for policy server
# ---------------------------------------------------------------------------

class ThrottleCounter:
    """Thread-safe in-memory counter for rate-limiting decisions."""

    def __init__(self):
        self._lock = threading.Lock()
        self._hour_count = 0
        self._day_count = 0
        self._current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self._current_day = date.today()
        self._last_sync = time.time()

    def increment(self) -> None:
        with self._lock:
            self._rotate()
            self._hour_count += 1
            self._day_count += 1

    def get_counts(self) -> tuple[int, int]:
        """Return (hour_count, day_count)."""
        with self._lock:
            self._rotate()
            return self._hour_count, self._day_count

    def _rotate(self) -> None:
        now = datetime.now(timezone.utc)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        current_day = now.date()
        if current_hour != self._current_hour:
            self._hour_count = 0
            self._current_hour = current_hour
        if current_day != self._current_day:
            self._day_count = 0
            self._current_day = current_day

    def sync_from_db(self) -> None:
        """Sync counts from database (called periodically)."""
        try:
            db = SessionLocal()
            try:
                with self._lock:
                    self._rotate()
                    self._hour_count = get_sent_this_hour(db)
                    self._day_count = get_sent_today(db)
                    self._last_sync = time.time()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"ThrottleCounter sync error: {e}")

    def should_sync(self) -> bool:
        return (time.time() - self._last_sync) > 30


# Global counter instance
throttle_counter = ThrottleCounter()


# ---------------------------------------------------------------------------
# Seed default data
# ---------------------------------------------------------------------------

def seed_default_data(db: Session) -> None:
    """Populate default throttle data if tables are empty."""
    # Config
    if db.query(ThrottleConfig).count() == 0:
        logger.info("Seeding default throttle config")
        db.add_all([
            ThrottleConfig(key="enabled", value="false"),
            ThrottleConfig(key="warmup_start_date", value=str(date.today())),
            ThrottleConfig(key="batch_interval_minutes", value="10"),
        ])
        db.commit()

    # Phases
    if db.query(WarmupPhase).count() == 0:
        logger.info("Seeding default warmup phases")
        db.add_all([
            WarmupPhase(phase_number=1, name="Woche 1-2", duration_days=14, max_per_hour=20, max_per_day=500, burst_limit=10),
            WarmupPhase(phase_number=2, name="Woche 3-4", duration_days=14, max_per_hour=50, max_per_day=2000, burst_limit=25),
            WarmupPhase(phase_number=3, name="Woche 5-6", duration_days=14, max_per_hour=100, max_per_day=5000, burst_limit=50),
            WarmupPhase(phase_number=4, name="Etabliert", duration_days=0, max_per_hour=500, max_per_day=50000, burst_limit=200),
        ])
        db.commit()

    # Transport rules
    if db.query(TransportRule).count() == 0:
        logger.info("Seeding default transport rules")
        db.add_all([
            TransportRule(domain_pattern="gmail.com", transport_name="gmail_throttled", concurrency_limit=3, rate_delay_seconds=3, description="Google Mail"),
            TransportRule(domain_pattern="googlemail.com", transport_name="gmail_throttled", concurrency_limit=3, rate_delay_seconds=3, description="Google Mail (alt)"),
            TransportRule(domain_pattern="outlook.com", transport_name="outlook_throttled", concurrency_limit=2, rate_delay_seconds=5, description="Microsoft Outlook"),
            TransportRule(domain_pattern="hotmail.com", transport_name="outlook_throttled", concurrency_limit=2, rate_delay_seconds=5, description="Microsoft Hotmail"),
            TransportRule(domain_pattern="live.com", transport_name="outlook_throttled", concurrency_limit=2, rate_delay_seconds=5, description="Microsoft Live"),
            TransportRule(domain_pattern="yahoo.com", transport_name="yahoo_throttled", concurrency_limit=3, rate_delay_seconds=3, description="Yahoo Mail"),
            TransportRule(domain_pattern="yahoo.de", transport_name="yahoo_throttled", concurrency_limit=3, rate_delay_seconds=3, description="Yahoo Mail DE"),
            TransportRule(domain_pattern="*", transport_name="default_throttled", concurrency_limit=5, rate_delay_seconds=1, description="Standard"),
        ])
        db.commit()
