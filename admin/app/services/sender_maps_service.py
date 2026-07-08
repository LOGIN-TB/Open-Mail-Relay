"""Sender-login-map service — per-domain sender binding (domain binding).

Generates a Postfix hash map `@domain user1,user2` from the enforced_domains
of active SMTP users. Together with
`smtpd_sender_restrictions = reject_known_sender_login_mismatch` Postfix then
rejects MAIL FROM addresses of a MAPPED domain when the authenticated user is
not listed for it — domains NOT in the map (monitor mode) stay unrestricted.

Controlled by SystemSetting `sender_maps_enabled` + marker file (default
off). An empty map is a no-op even when enabled, so turning the feature on
before any domain is enforced changes nothing.
"""
import json
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import SmtpUser, SystemSetting
from app.services.docker_service import exec_in_container, reload_postfix

logger = logging.getLogger(__name__)

SENDER_MAPS_FILE = settings.POSTFIX_CONFIG_PATH / "sender_login_maps"
SENDER_MAPS_MARKER = settings.POSTFIX_CONFIG_PATH / "sender_maps_enabled"
SETTING_KEY = "sender_maps_enabled"


def get_sender_maps_enabled(db: Session) -> bool:
    row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    return bool(row and row.value == "1")


def set_sender_maps_enabled(db: Session, enabled: bool) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_KEY).first()
    if row:
        row.value = "1" if enabled else ""
    else:
        db.add(SystemSetting(key=SETTING_KEY, value="1" if enabled else ""))
    db.commit()


def build_sender_map_lines(db: Session) -> list[str]:
    """Pure map content: one line per enforced domain, users aggregated."""
    users = db.query(SmtpUser).filter(SmtpUser.is_active == True).all()  # noqa: E712
    domain_users: dict[str, set[str]] = {}
    for user in users:
        if not user.enforced_domains:
            continue
        try:
            domains = json.loads(user.enforced_domains)
        except ValueError:
            logger.error(f"Invalid enforced_domains JSON for user {user.username} — skipped")
            continue
        for domain in domains:
            domain_users.setdefault(domain.strip().lower(), set()).add(user.username)
    return [f"@{domain} {','.join(sorted(users))}" for domain, users in sorted(domain_users.items())]


def generate_sender_login_maps(db: Session) -> tuple[bool, str]:
    """Write the map, install it in the mail container, postmap + reload."""
    try:
        lines = build_sender_map_lines(db)
        SENDER_MAPS_FILE.write_text("\n".join(lines) + "\n" if lines else "")

        exit_code, output = exec_in_container(
            "sh -c 'cp /etc/postfix-config/sender_login_maps /etc/postfix/sender_login_maps"
            " && postmap /etc/postfix/sender_login_maps'"
        )
        if exit_code != 0:
            return False, f"postmap fehlgeschlagen: {output}"

        ok, msg = reload_postfix()
        if not ok:
            return False, f"Postfix-Reload fehlgeschlagen: {msg}"

        logger.info(f"Sender login maps: {len(lines)} enforced domain(s) written")
        return True, f"{len(lines)} erzwungene Domain(s)"
    except Exception as e:
        logger.error(f"Failed to generate sender login maps: {e}")
        return False, str(e)


def sync_sender_maps(db: Session) -> None:
    """Regenerate after user mutations — cheap no-op while the feature is off."""
    if not get_sender_maps_enabled(db):
        return
    ok, msg = generate_sender_login_maps(db)
    if not ok:
        logger.warning(f"Sender-map sync failed: {msg}")


def apply_sender_maps_config(db: Session, enabled: bool) -> list[dict]:
    """Enable/disable the whole mechanism (marker + postconf), like throttling."""
    steps: list[dict] = []
    set_sender_maps_enabled(db, enabled)

    if enabled:
        ok, msg = generate_sender_login_maps(db)
        steps.append({"step": "Sender-Map generieren", "success": ok, "detail": msg})

        SENDER_MAPS_MARKER.write_text("")
        steps.append({"step": "Domain-Bindung aktivieren", "success": True, "detail": "Marker erstellt"})

        exit_code, output = exec_in_container(
            "sh -c '"
            'postconf -e "smtpd_sender_login_maps = hash:/etc/postfix/sender_login_maps" && '
            'postconf -e "smtpd_sender_restrictions = reject_known_sender_login_mismatch"'
            "'"
        )
        steps.append({
            "step": "Postfix konfigurieren",
            "success": exit_code == 0,
            "detail": output if exit_code != 0 else "OK",
        })
    else:
        SENDER_MAPS_MARKER.unlink(missing_ok=True)
        steps.append({"step": "Domain-Bindung deaktivieren", "success": True, "detail": "Marker entfernt"})

        exit_code, output = exec_in_container(
            "sh -c '"
            "postconf -# smtpd_sender_login_maps 2>/dev/null; "
            "postconf -# smtpd_sender_restrictions 2>/dev/null; "
            "true"
            "'"
        )
        steps.append({
            "step": "Postfix-Konfiguration entfernen",
            "success": exit_code == 0,
            "detail": output if exit_code != 0 else "OK",
        })

    ok, msg = reload_postfix()
    steps.append({"step": "Postfix neu laden", "success": ok, "detail": msg if not ok else "OK"})
    return steps
