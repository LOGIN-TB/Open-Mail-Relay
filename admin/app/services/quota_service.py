"""Per-user monthly quota enforcement (R1, Portal-API 2.7.0).

Until now the monthly quota was only COUNTED (billing_service) — this service
ENFORCES it at send time via the existing policy server (port 9998). The
limit source is `smtp_users.monthly_limit_override` when set (pushed by the
portal: trial cap, plan limit, plan + released extra packs), otherwise the
assigned package's monthly_limit.

Rollout mirrors the domain-binding switch: SystemSetting
`quota_enforcement_enabled` (default off) + marker file so the mail
container's entrypoint restores the Postfix policy hook after restarts.
Exceeded quota answers DEFER (4xx) — client queues retry, so mail flows again
automatically as soon as the portal raises the limit.
"""
import logging
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import MailEvent, Package, SmtpUser, SystemSetting
from app.services.docker_service import exec_in_container, reload_postfix

logger = logging.getLogger(__name__)

QUOTA_MARKER = Path("/etc/postfix-config") / "quota_enforcement_enabled"

# Short cache so the policy server does not hit the DB with a count query for
# every single mail. Allowed mails increment the cached counter, so bursts
# inside the TTL are still enforced correctly.
QUOTA_CACHE_TTL = 30.0


def get_quota_enforcement_enabled(db: Session) -> bool:
    row = db.query(SystemSetting).filter(SystemSetting.key == "quota_enforcement_enabled").first()
    return bool(row and row.value == "1")


def set_quota_enforcement_enabled(db: Session, enabled: bool) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == "quota_enforcement_enabled").first()
    if row:
        row.value = "1" if enabled else ""
    else:
        db.add(SystemSetting(key="quota_enforcement_enabled", value="1" if enabled else ""))
    db.commit()


def effective_monthly_limit(db: Session, user: SmtpUser) -> int | None:
    """Portal override wins; fallback package limit; None = unlimited."""
    if user.monthly_limit_override is not None:
        return user.monthly_limit_override
    if user.package_id:
        pkg = db.query(Package).filter(Package.id == user.package_id).first()
        if pkg:
            return pkg.monthly_limit
    return None


def _sent_this_month(db: Session, username: str) -> int:
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    return (
        db.query(func.count(MailEvent.id))
        .filter(
            MailEvent.status == "sent",
            MailEvent.sasl_username == username,
            MailEvent.timestamp >= month_start,
        )
        .scalar()
    ) or 0


class QuotaChecker:
    """TTL-cached quota lookups for the policy server hot path."""

    def __init__(self) -> None:
        # username -> [expires_at, used, limit or None]
        self._cache: dict[str, list] = {}

    def clear(self) -> None:
        self._cache.clear()

    def check(self, db: Session, username: str) -> tuple[bool, int, int] | None:
        """(exceeded, used, limit) — or None when the user has no limit."""
        now = time.monotonic()
        entry = self._cache.get(username)
        if entry is None or entry[0] < now:
            user = db.query(SmtpUser).filter(SmtpUser.username == username).first()
            limit = effective_monthly_limit(db, user) if user else None
            used = _sent_this_month(db, username) if limit is not None else 0
            entry = [now + QUOTA_CACHE_TTL, used, limit]
            self._cache[username] = entry
            if len(self._cache) > 5000:
                self._cache = {k: v for k, v in self._cache.items() if v[0] >= now}
        if entry[2] is None:
            return None
        return entry[1] >= entry[2], entry[1], entry[2]

    def register_sent(self, username: str) -> None:
        entry = self._cache.get(username)
        if entry:
            entry[1] += 1


quota_checker = QuotaChecker()


def apply_quota_config(db: Session, enabled: bool) -> list[dict]:
    """Toggle enforcement: marker + Postfix policy hook (pattern: Drosselung).

    The policy hook (smtpd_end_of_data_restrictions) is SHARED with the
    throttle feature — it is only removed when neither feature needs it.
    """
    from app.services.throttle_service import get_throttle_enabled

    steps: list[dict] = []
    set_quota_enforcement_enabled(db, enabled)
    quota_checker.clear()

    if enabled:
        QUOTA_MARKER.parent.mkdir(parents=True, exist_ok=True)
        QUOTA_MARKER.write_text("enabled\n")
        steps.append({"step": "Kontingent-Durchsetzung aktivieren", "success": True, "detail": "Marker erstellt"})

        exit_code, output = exec_in_container(
            "sh -c '"
            'postconf -e "smtpd_end_of_data_restrictions = check_policy_service inet:admin-panel:9998" && '
            'postconf -e "smtpd_policy_service_default_action = DUNNO" && '
            'postconf -e "smtpd_policy_service_timeout = 5"'
            "'"
        )
        steps.append({
            "step": "Postfix-Policy konfigurieren",
            "success": exit_code == 0,
            "detail": output if exit_code != 0 else "OK",
        })
    else:
        try:
            QUOTA_MARKER.unlink(missing_ok=True)
        except Exception:
            pass
        steps.append({"step": "Kontingent-Durchsetzung deaktivieren", "success": True, "detail": "Marker entfernt"})

        if not get_throttle_enabled(db):
            exec_in_container("sh -c 'postconf -# smtpd_end_of_data_restrictions 2>/dev/null; true'")
            steps.append({"step": "Postfix-Policy entfernen", "success": True, "detail": "Policy-Hook entfernt (Drosselung inaktiv)"})
        else:
            steps.append({"step": "Postfix-Policy behalten", "success": True, "detail": "Drosselung nutzt den Policy-Hook weiter"})

    ok, msg = reload_postfix()
    steps.append({"step": "Postfix neu laden", "success": ok, "detail": msg})
    return steps
