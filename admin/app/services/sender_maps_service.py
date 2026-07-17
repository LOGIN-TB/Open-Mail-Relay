"""Sender-login-map service — per-domain sender binding (domain binding).

Generates a Postfix hash map `@domain user1,user2` from the enforced_domains
of active SMTP users. Together with
`smtpd_sender_restrictions = reject_known_sender_login_mismatch` Postfix then
rejects MAIL FROM addresses of a MAPPED domain when the authenticated user is
not listed for it — domains NOT in the map (monitor mode) stay unrestricted.

Controlled by SystemSetting `sender_maps_enabled` + marker file (default
off). An empty map is a no-op even when enabled, so turning the feature on
before any domain is enforced changes nothing.

Strict sender binding (R5, portal ADR 0009) builds on top: with
`strict_sender_enabled` the restriction flips to
`check_sasl_access hash:sender_policy_exempt, reject_sender_login_mismatch` —
an authenticated user may then ONLY send from domains mapped to them. Users
with sender_policy 'unrestricted' stand in the exempt map, which resolves to
the restriction class `soft_sender_policy` = today's soft rule (any domain
except ones enforced for someone else). The exempt map is the safety net of
the rollout: at cutover EVERY existing user is 'unrestricted', so flipping
the switch changes nothing until the portal migrates accesses to 'strict'.
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

SENDER_EXEMPT_FILE = settings.POSTFIX_CONFIG_PATH / "sender_policy_exempt"
STRICT_MARKER = settings.POSTFIX_CONFIG_PATH / "strict_sender_enabled"
STRICT_SETTING_KEY = "strict_sender_enabled"
# Restriction class the exempt map resolves to (defined via postconf when the
# strict switch is applied): soft_sender_policy = reject_known_sender_login_mismatch, permit.
# The trailing 'permit' is essential: without it a DUNNO (sender domain not
# mapped at all) falls through to the OUTER list and hits
# reject_sender_login_mismatch — every exempt user would still be strict.
EXEMPT_CLASS = "soft_sender_policy"


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


def get_strict_sender_enabled(db: Session) -> bool:
    row = db.query(SystemSetting).filter(SystemSetting.key == STRICT_SETTING_KEY).first()
    return bool(row and row.value == "1")


def set_strict_sender_enabled(db: Session, enabled: bool) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == STRICT_SETTING_KEY).first()
    if row:
        row.value = "1" if enabled else ""
    else:
        db.add(SystemSetting(key=STRICT_SETTING_KEY, value="1" if enabled else ""))
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


def build_sender_exempt_lines(db: Session) -> list[str]:
    """Exempt map: one line per active NON-strict user → restriction class."""
    users = db.query(SmtpUser).filter(SmtpUser.is_active == True).all()  # noqa: E712
    return [
        f"{user.username} {EXEMPT_CLASS}"
        for user in sorted(users, key=lambda u: u.username)
        if user.sender_policy != "strict"
    ]


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


def generate_sender_exempt_map(db: Session) -> tuple[bool, str]:
    """Write the exempt map, install it in the mail container, postmap + reload."""
    try:
        lines = build_sender_exempt_lines(db)
        SENDER_EXEMPT_FILE.write_text("\n".join(lines) + "\n" if lines else "")

        exit_code, output = exec_in_container(
            "sh -c 'cp /etc/postfix-config/sender_policy_exempt /etc/postfix/sender_policy_exempt"
            " && postmap /etc/postfix/sender_policy_exempt'"
        )
        if exit_code != 0:
            return False, f"postmap fehlgeschlagen: {output}"

        ok, msg = reload_postfix()
        if not ok:
            return False, f"Postfix-Reload fehlgeschlagen: {msg}"

        logger.info(f"Sender policy exempt map: {len(lines)} unrestricted user(s) written")
        return True, f"{len(lines)} Ausnahme(n)"
    except Exception as e:
        logger.error(f"Failed to generate sender exempt map: {e}")
        return False, str(e)


def sync_sender_maps(db: Session) -> None:
    """Regenerate after user mutations — cheap no-op while the features are off."""
    if get_sender_maps_enabled(db):
        ok, msg = generate_sender_login_maps(db)
        if not ok:
            logger.warning(f"Sender-map sync failed: {msg}")
    if get_strict_sender_enabled(db):
        ok, msg = generate_sender_exempt_map(db)
        if not ok:
            logger.warning(f"Sender-exempt-map sync failed: {msg}")


def apply_sender_maps_config(db: Session, enabled: bool) -> list[dict]:
    """Enable/disable the whole mechanism (marker + postconf), like throttling."""
    steps: list[dict] = []

    # Strict mode depends on the login maps — without them
    # reject_sender_login_mismatch would block ALL authenticated senders.
    # Disabling domain binding therefore takes strict mode down with it.
    if not enabled and get_strict_sender_enabled(db):
        steps.extend(apply_strict_sender_config(db, False))

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


def apply_strict_sender_config(db: Session, enabled: bool) -> list[dict]:
    """Strict sender binding switch (R5, portal ADR 0009).

    On: exempt map + restriction class + reject_sender_login_mismatch —
    harmless at cutover because every pre-existing user is 'unrestricted'.
    Off: back to the plain domain-binding restriction (soft rule for all).
    """
    steps: list[dict] = []

    if enabled and not get_sender_maps_enabled(db):
        # Guard, not a toggle-order nicety: with the login maps absent the
        # strict restriction would reject every authenticated MAIL FROM.
        steps.append({
            "step": "Strikte Absenderbindung aktivieren",
            "success": False,
            "detail": "Domain-Bindung muss zuerst aktiv sein (sender_maps_enabled)",
        })
        return steps

    set_strict_sender_enabled(db, enabled)

    if enabled:
        ok, msg = generate_sender_exempt_map(db)
        steps.append({"step": "Ausnahme-Map generieren", "success": ok, "detail": msg})

        STRICT_MARKER.write_text("")
        steps.append({"step": "Strikte Absenderbindung aktivieren", "success": True, "detail": "Marker erstellt"})

        exit_code, output = exec_in_container(
            "sh -c '"
            f'postconf -e "smtpd_restriction_classes = {EXEMPT_CLASS}" && '
            f'postconf -e "{EXEMPT_CLASS} = reject_known_sender_login_mismatch, permit" && '
            'postconf -e "smtpd_sender_restrictions = check_sasl_access hash:/etc/postfix/sender_policy_exempt, reject_sender_login_mismatch"'
            "'"
        )
        steps.append({
            "step": "Postfix konfigurieren",
            "success": exit_code == 0,
            "detail": output if exit_code != 0 else "OK",
        })
    else:
        STRICT_MARKER.unlink(missing_ok=True)
        steps.append({"step": "Strikte Absenderbindung deaktivieren", "success": True, "detail": "Marker entfernt"})

        # Back to the soft rule — domain binding itself stays on.
        exit_code, output = exec_in_container(
            "sh -c '"
            'postconf -e "smtpd_sender_restrictions = reject_known_sender_login_mismatch"; '
            f"postconf -# smtpd_restriction_classes 2>/dev/null; "
            f"postconf -# {EXEMPT_CLASS} 2>/dev/null; "
            "true"
            "'"
        )
        steps.append({
            "step": "Postfix-Konfiguration zurücksetzen",
            "success": exit_code == 0,
            "detail": output if exit_code != 0 else "OK",
        })

    ok, msg = reload_postfix()
    steps.append({"step": "Postfix neu laden", "success": ok, "detail": msg if not ok else "OK"})
    return steps
