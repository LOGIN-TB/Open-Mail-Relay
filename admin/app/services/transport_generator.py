"""Transport map and master.cf generator for throttled delivery."""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import TransportRule
from app.services.docker_service import exec_in_container, reload_postfix

logger = logging.getLogger(__name__)

POSTFIX_CONFIG_DIR = Path("/etc/postfix-config")
TRANSPORT_FILE = POSTFIX_CONFIG_DIR / "transport"
THROTTLE_MARKER = POSTFIX_CONFIG_DIR / "throttle_enabled"
MASTER_CF_FILE = POSTFIX_CONFIG_DIR / "master.cf"

MARKER_START = "# --- THROTTLED TRANSPORTS START ---"
MARKER_END = "# --- THROTTLED TRANSPORTS END ---"


def generate_transport_map(db: Session) -> tuple[bool, str]:
    """Write transport map from active TransportRules and install into Postfix."""
    rules = (
        db.query(TransportRule)
        .filter(TransportRule.is_active == True)
        .order_by(TransportRule.domain_pattern)
        .all()
    )

    lines = ["# Auto-generated transport map — do not edit manually"]
    default_line = None
    for rule in rules:
        if rule.domain_pattern == "*":
            default_line = f"*    {rule.transport_name}:"
        else:
            lines.append(f"{rule.domain_pattern}    {rule.transport_name}:")

    # Default (*) always last
    if default_line:
        lines.append(default_line)

    lines.append("")  # trailing newline

    try:
        POSTFIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TRANSPORT_FILE.write_text("\n".join(lines))

        # Copy into Postfix container and postmap
        exit_code, output = exec_in_container(
            "sh -c 'cp /etc/postfix-config/transport /etc/postfix/transport && postmap /etc/postfix/transport'"
        )
        if exit_code != 0:
            logger.error(f"Failed to install transport map: {output}")
            return False, output

        return True, "Transport map updated"
    except Exception as e:
        logger.error(f"Error generating transport map: {e}")
        return False, str(e)


def generate_master_cf_transports(db: Session) -> tuple[bool, str]:
    """Update master.cf with throttled transport definitions between markers."""
    rules = (
        db.query(TransportRule)
        .filter(TransportRule.is_active == True)
        .all()
    )

    # Collect unique transport names
    seen = set()
    transports = []
    for rule in rules:
        if rule.transport_name not in seen:
            seen.add(rule.transport_name)
            transports.append(rule)

    # Build transport service definitions
    transport_lines = [MARKER_START]
    for rule in transports:
        transport_lines.append(
            f"{rule.transport_name}    unix  -       -       n       -       {rule.concurrency_limit}       smtp"
        )
        transport_lines.append(
            f"  -o syslog_name=postfix/{rule.transport_name}"
        )
        transport_lines.append(
            f"  -o smtp_destination_concurrency_limit={rule.concurrency_limit}"
        )
        if rule.rate_delay_seconds > 0:
            transport_lines.append(
                f"  -o smtp_destination_rate_delay={rule.rate_delay_seconds}s"
            )
    transport_lines.append(MARKER_END)

    try:
        if not MASTER_CF_FILE.exists():
            logger.error("master.cf not found")
            return False, "master.cf not found"

        content = MASTER_CF_FILE.read_text()

        # Remove existing marker block
        if MARKER_START in content:
            before = content[:content.index(MARKER_START)]
            after_marker = content[content.index(MARKER_END) + len(MARKER_END):]
            content = before.rstrip("\n") + "\n" + after_marker.lstrip("\n")

        # Append new block
        content = content.rstrip("\n") + "\n" + "\n".join(transport_lines) + "\n"

        MASTER_CF_FILE.write_text(content)

        # Copy into container
        exit_code, output = exec_in_container(
            "sh -c 'cp /etc/postfix-config/master.cf /etc/postfix/master.cf'"
        )
        if exit_code != 0:
            logger.error(f"Failed to copy master.cf: {output}")
            return False, output

        return True, "master.cf transports updated"
    except Exception as e:
        logger.error(f"Error updating master.cf transports: {e}")
        return False, str(e)


def create_throttle_marker() -> None:
    """Create marker file to signal entrypoint.sh that throttling is enabled."""
    POSTFIX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    THROTTLE_MARKER.write_text("enabled\n")


def remove_throttle_marker() -> None:
    """Remove throttle marker file."""
    try:
        THROTTLE_MARKER.unlink(missing_ok=True)
    except Exception:
        pass


def apply_throttle_config(db: Session, enabled: bool) -> list[dict]:
    """Apply or remove throttle configuration and reload Postfix."""
    steps = []

    if enabled:
        # Generate transport map
        ok, msg = generate_transport_map(db)
        steps.append({"step": "Transport-Map generieren", "success": ok, "detail": msg})

        # Generate master.cf transports
        ok, msg = generate_master_cf_transports(db)
        steps.append({"step": "Master.cf aktualisieren", "success": ok, "detail": msg})

        # Create marker
        create_throttle_marker()
        steps.append({"step": "Drosselung aktivieren", "success": True, "detail": "Marker erstellt"})

        # Apply postconf for policy service
        exit_code, output = exec_in_container(
            "sh -c '"
            'postconf -e "transport_maps = hash:/etc/postfix/transport" && '
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
        # Remove marker
        remove_throttle_marker()
        steps.append({"step": "Drosselung deaktivieren", "success": True, "detail": "Marker entfernt"})

        # Remove policy and transport config
        exit_code, output = exec_in_container(
            "sh -c '"
            'postconf -# smtpd_end_of_data_restrictions 2>/dev/null; '
            'postconf -# transport_maps 2>/dev/null; '
            'true'
            "'"
        )
        steps.append({
            "step": "Postfix-Policy entfernen",
            "success": True,
            "detail": "Konfiguration bereinigt",
        })

        # Release all held mail
        exit_code, output = exec_in_container(
            "sh -c 'postsuper -H ALL 2>/dev/null; postqueue -f 2>/dev/null; true'"
        )
        steps.append({
            "step": "Gehaltene Mails freigeben",
            "success": True,
            "detail": "Alle HOLD-Mails freigegeben",
        })

    # Reload Postfix
    ok, msg = reload_postfix()
    steps.append({"step": "Postfix neu laden", "success": ok, "detail": msg})

    return steps
