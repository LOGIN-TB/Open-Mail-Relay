"""IP Ban Service — core logic for automatic and manual IP blocking.

Tracks failed authentication attempts, activates progressive bans,
generates Postfix client_access CIDR map and handles expiry.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import IpBan, Network, SystemSetting
from app.services.docker_service import reload_postfix

logger = logging.getLogger(__name__)

CLIENT_ACCESS_FILE = settings.POSTFIX_CONFIG_PATH / "client_access"

# Defaults
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_TIME_WINDOW_MINUTES = 10
DEFAULT_BAN_DURATIONS = [30, 360, 1440, 10080]  # minutes


def _get_setting(db: Session, key: str, default: str) -> str:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else default


def get_ban_settings(db: Session) -> dict:
    max_attempts = int(_get_setting(db, "ban_max_attempts", str(DEFAULT_MAX_ATTEMPTS)))
    time_window = int(_get_setting(db, "ban_time_window_minutes", str(DEFAULT_TIME_WINDOW_MINUTES)))
    try:
        durations = json.loads(_get_setting(db, "ban_durations", json.dumps(DEFAULT_BAN_DURATIONS)))
    except (json.JSONDecodeError, ValueError):
        durations = DEFAULT_BAN_DURATIONS
    return {
        "max_attempts": max_attempts,
        "time_window_minutes": time_window,
        "ban_durations": durations,
    }


def update_ban_settings(db: Session, max_attempts: int, time_window_minutes: int, ban_durations: list[int]):
    for key, value in [
        ("ban_max_attempts", str(max_attempts)),
        ("ban_time_window_minutes", str(time_window_minutes)),
        ("ban_durations", json.dumps(ban_durations)),
    ]:
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
    db.commit()


def _is_whitelisted(db: Session, ip_address: str) -> bool:
    """Check if IP is in any whitelisted network (mynetworks)."""
    import ipaddress
    try:
        ip = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    networks = db.query(Network).all()
    for net in networks:
        try:
            if ip in ipaddress.ip_network(net.cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def record_failure(db: Session, ip_address: str, reason: str):
    """Record a failed attempt. Auto-ban if threshold is reached."""
    if _is_whitelisted(db, ip_address):
        return

    now = datetime.now()
    cfg = get_ban_settings(db)
    max_attempts = cfg["max_attempts"]
    time_window = cfg["time_window_minutes"]

    ban = db.query(IpBan).filter(IpBan.ip_address == ip_address).first()

    if ban and ban.is_active:
        # Already banned — just increment fail_count
        ban.fail_count += 1
        db.commit()
        return

    if not ban:
        ban = IpBan(
            ip_address=ip_address,
            reason=reason,
            ban_count=0,
            fail_count=1,
            first_fail_at=now,
            is_active=False,
        )
        db.add(ban)
        db.commit()
        db.refresh(ban)
        return

    # Rolling window: decrement count proportionally when window expires,
    # but keep tracking so persistent attackers eventually get banned
    if ban.first_fail_at and (now - ban.first_fail_at) > timedelta(minutes=time_window):
        # Halve the fail count instead of resetting — persistent attackers accumulate
        ban.fail_count = max(1, ban.fail_count // 2 + 1)
        ban.first_fail_at = now
        ban.reason = reason
    else:
        # Within window — increment fail count
        ban.fail_count += 1
        if not ban.first_fail_at:
            ban.first_fail_at = now
        ban.reason = reason

    db.commit()

    # Check threshold
    if ban.fail_count >= max_attempts:
        activate_ban(db, ip_address)


def activate_ban(db: Session, ip_address: str):
    """Activate a ban with progressive duration based on ban_count."""
    now = datetime.now()
    cfg = get_ban_settings(db)
    durations = cfg["ban_durations"]

    ban = db.query(IpBan).filter(IpBan.ip_address == ip_address).first()
    if not ban:
        return

    ban.ban_count += 1
    ban.is_active = True
    ban.banned_at = now

    # Progressive duration
    idx = min(ban.ban_count - 1, len(durations) - 1)
    duration_minutes = durations[idx]
    ban.expires_at = now + timedelta(minutes=duration_minutes)

    db.commit()
    logger.info(f"IP {ip_address} banned (count={ban.ban_count}, duration={duration_minutes}min)")

    generate_client_access_file(db)


def manual_ban(db: Session, ip_address: str, reason: str = "manual", notes: str = ""):
    """Manually ban an IP (permanent, no expiry)."""
    now = datetime.now()

    ban = db.query(IpBan).filter(IpBan.ip_address == ip_address).first()
    if ban:
        ban.is_active = True
        ban.banned_at = now
        ban.expires_at = None  # Permanent
        ban.reason = reason
        ban.notes = notes
        ban.ban_count += 1
    else:
        ban = IpBan(
            ip_address=ip_address,
            reason=reason,
            ban_count=1,
            fail_count=0,
            banned_at=now,
            expires_at=None,  # Permanent
            is_active=True,
            notes=notes,
        )
        db.add(ban)

    db.commit()
    logger.info(f"IP {ip_address} manually banned (permanent)")
    generate_client_access_file(db)


def unban_ip(db: Session, ban_id: int):
    """Remove a ban and regenerate the access map."""
    ban = db.query(IpBan).filter(IpBan.id == ban_id).first()
    if not ban:
        return
    ban.is_active = False
    ban.fail_count = 0
    ban.first_fail_at = None
    db.commit()
    logger.info(f"IP {ban.ip_address} unbanned")
    generate_client_access_file(db)


def generate_client_access_file(db: Session):
    """Generate Postfix client_access CIDR map from active bans and reload."""
    active_bans = db.query(IpBan).filter(IpBan.is_active == True).all()

    lines = ["# Auto-generated by Open Mail Relay — do not edit manually"]
    for ban in active_bans:
        lines.append(f"{ban.ip_address}    REJECT IP gesperrt: {ban.reason}")

    CLIENT_ACCESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CLIENT_ACCESS_FILE.write_text("\n".join(lines) + "\n")

    success, output = reload_postfix()
    if not success:
        logger.error(f"Postfix reload failed after client_access update: {output}")


def check_expired_bans(db: Session):
    """Deactivate expired bans and regenerate the access map if anything changed."""
    now = datetime.now()
    expired = db.query(IpBan).filter(
        IpBan.is_active == True,
        IpBan.expires_at != None,
        IpBan.expires_at <= now,
    ).all()

    if not expired:
        return

    for ban in expired:
        ban.is_active = False
        ban.fail_count = 0
        ban.first_fail_at = None
        logger.info(f"Ban expired for IP {ban.ip_address}")

    db.commit()
    generate_client_access_file(db)
