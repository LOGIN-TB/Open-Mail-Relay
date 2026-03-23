"""RBL Blacklist Checker — checks mail-server IPs against DNS-based blacklists."""

import json
import logging
import smtplib
import socket
import concurrent.futures
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.models import SystemSetting

logger = logging.getLogger(__name__)

# Hard-coded RBL server list (not user-configurable)
RBL_SERVERS = [
    {"name": "Spamhaus ZEN", "zone": "zen.spamhaus.org"},
    {"name": "Spamhaus SBL", "zone": "sbl.spamhaus.org"},
    {"name": "Spamhaus XBL", "zone": "xbl.spamhaus.org"},
    {"name": "Spamhaus PBL", "zone": "pbl.spamhaus.org"},
    {"name": "Barracuda", "zone": "b.barracudacentral.org"},
    {"name": "SpamCop", "zone": "bl.spamcop.net"},
    {"name": "SORBS DNSBL", "zone": "dnsbl.sorbs.net"},
    {"name": "SORBS Spam", "zone": "spam.dnsbl.sorbs.net"},
    {"name": "UCEPROTECT Level 1", "zone": "dnsbl-1.uceprotect.net"},
    {"name": "UCEPROTECT Level 2", "zone": "dnsbl-2.uceprotect.net"},
    {"name": "UCEPROTECT Level 3", "zone": "dnsbl-3.uceprotect.net"},
    {"name": "Abuseat CBL", "zone": "cbl.abuseat.org"},
    {"name": "PSBL", "zone": "psbl.surriel.com"},
    {"name": "Mailspike BL", "zone": "bl.mailspike.net"},
    {"name": "SpamRATS DYNA", "zone": "dyna.spamrats.com"},
    {"name": "SpamRATS NoPtr", "zone": "noptr.spamrats.com"},
    {"name": "SpamRATS Spam", "zone": "spam.spamrats.com"},
    {"name": "JustSpam", "zone": "dnsbl.justspam.org"},
    {"name": "Truncate", "zone": "truncate.gbudb.net"},
    {"name": "Woody Spam", "zone": "db.wpbl.info"},
    {"name": "Invaluement", "zone": "dnsbl.invaluement.com"},
    {"name": "0Spam DNSBL", "zone": "0spam.fusionzero.com"},
]

ALLOWED_KEYS = {
    "rbl_enabled",
    "rbl_servers",
    "rbl_check_interval_hours",
    "rbl_mail_to",
    "rbl_mail_from",
    "rbl_alert_on_change_only",
    "rbl_dns_timeout",
    "rbl_last_results",
    "rbl_last_check_time",
}

DEFAULTS: dict[str, str] = {
    "rbl_enabled": "false",
    "rbl_servers": "[]",
    "rbl_check_interval_hours": "6",
    "rbl_mail_to": "",
    "rbl_mail_from": "",
    "rbl_alert_on_change_only": "false",
    "rbl_dns_timeout": "5",
    "rbl_last_results": "{}",
    "rbl_last_check_time": "",
}


def get_server_info() -> dict[str, str]:
    """Read hostname from Postfix config and resolve its IP."""
    from app.services.postfix_service import read_main_cf

    cf = read_main_cf()
    hostname = cf.get("myhostname", "localhost")
    ip = ""
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        if results:
            ip = results[0][4][0]
    except (socket.gaierror, OSError) as e:
        logger.warning("Could not resolve hostname %s: %s", hostname, e)
    return {"name": hostname, "ip": ip}


def get_rbl_settings(db: Session) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, default in DEFAULTS.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        result[key] = row.value if row else default
    return result


def update_rbl_settings(db: Session, data: dict[str, str]) -> dict[str, str]:
    for key, value in data.items():
        if key not in ALLOWED_KEYS or value is None:
            continue
        # Don't allow direct writes to computed fields
        if key in ("rbl_last_results", "rbl_last_check_time"):
            continue
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
    db.commit()
    return get_rbl_settings(db)


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))


def reverse_ip(ip: str) -> str:
    return ".".join(reversed(ip.split(".")))


# Spamhaus (and some others) return these special IPs when queried via
# public/open DNS resolvers — they are NOT real listings.
_FALSE_POSITIVE_ANSWERS = {
    "127.255.255.252",  # typing error in DNSBL name
    "127.255.255.254",  # query via public/open resolver
    "127.255.255.255",  # excessive queries / rate limited
}


def check_rbl(ip: str, rbl_zone: str, timeout: int = 5) -> tuple[bool, str | None]:
    query = f"{reverse_ip(ip)}.{rbl_zone}"
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        results = socket.getaddrinfo(query, None)
        answer_ip = results[0][4][0] if results else None
        if answer_ip in _FALSE_POSITIVE_ANSWERS:
            return (False, None)
        return (True, answer_ip)
    except socket.gaierror:
        return (False, None)
    except socket.timeout:
        return (False, None)
    except OSError:
        return (False, None)
    finally:
        socket.setdefaulttimeout(old_timeout)


def check_server(server: dict, rbl_list: list[dict], timeout: int = 5) -> dict:
    ip = server["ip"]
    name = server["name"]
    listings = []

    def _check_one(rbl: dict) -> tuple[dict, bool, str | None]:
        listed, answer = check_rbl(ip, rbl["zone"], timeout)
        return (rbl, listed, answer)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_check_one, rbl): rbl for rbl in rbl_list}
        for future in concurrent.futures.as_completed(futures):
            rbl, listed, answer = future.result()
            if listed:
                listings.append({
                    "rbl_name": rbl["name"],
                    "rbl_zone": rbl["zone"],
                    "answer": answer,
                })

    return {
        "name": name,
        "ip": ip,
        "listings": listings,
        "checked": len(rbl_list),
        "listed_count": len(listings),
    }


def _detect_changes(old_state: dict, new_state: dict) -> dict:
    changes = {}
    all_ips = set(old_state.keys()) | set(new_state.keys())
    for ip in all_ips:
        old_zones = {e["rbl_zone"] for e in old_state.get(ip, [])}
        old_by_zone = {e["rbl_zone"]: e for e in old_state.get(ip, [])}
        new_zones = {e["rbl_zone"] for e in new_state.get(ip, [])}
        new_by_zone = {e["rbl_zone"]: e for e in new_state.get(ip, [])}

        added = new_zones - old_zones
        removed = old_zones - new_zones

        if added or removed:
            changes[ip] = {
                "new_listings": [new_by_zone[z] for z in added],
                "removed_listings": [old_by_zone[z] for z in removed],
            }
    return changes


def format_alert_email(results: list[dict], changes: dict | None = None) -> tuple[str, str]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    listed_servers = [r for r in results if r["listed_count"] > 0]

    if listed_servers:
        if len(listed_servers) == 1:
            s = listed_servers[0]
            subject = f"[RBL ALARM] {s['name']} ({s['ip']}) auf {s['listed_count']} Blacklist(s) gelistet"
        else:
            total = sum(s["listed_count"] for s in listed_servers)
            subject = f"[RBL ALARM] {len(listed_servers)} Server auf insgesamt {total} Blacklist(s) gelistet"
    else:
        subject = "[RBL OK] Alle Server clean"

    lines = [
        f"RBL Blacklist Check — {now}",
        "=" * 60,
        "",
        "UEBERSICHT",
        "-" * 40,
    ]
    for r in results:
        status = f"{r['listed_count']} LISTINGS" if r["listed_count"] > 0 else "CLEAN"
        lines.append(f"  {r['name']:20s} {r['ip']:15s} -> {status}")
    lines.append("")

    if listed_servers:
        lines.append("DETAILS")
        lines.append("-" * 40)
        for r in listed_servers:
            lines.append(f"\n  {r['name']} ({r['ip']}):")
            ip_changes = changes.get(r["ip"], {}) if changes else {}
            new_zones = {e["rbl_zone"] for e in ip_changes.get("new_listings", [])}
            for listing in r["listings"]:
                tag = " [NEU]" if listing["rbl_zone"] in new_zones else ""
                lines.append(f"    - {listing['rbl_name']:25s} ({listing['rbl_zone']}) — {listing['answer']}{tag}")

    if changes:
        removed_any = False
        for ip, ch in changes.items():
            if ch["removed_listings"]:
                if not removed_any:
                    lines.extend(["", "ENTFERNTE LISTINGS", "-" * 40])
                    removed_any = True
                server_name = ip
                for r in results:
                    if r["ip"] == ip:
                        server_name = f"{r['name']} ({ip})"
                        break
                lines.append(f"\n  {server_name}:")
                for entry in ch["removed_listings"]:
                    lines.append(f"    - {entry['rbl_name']:25s} ({entry['rbl_zone']}) [ENTFERNT]")

    lines.extend([
        "",
        "-" * 60,
        f"Gepruefte RBLs: {results[0]['checked'] if results else 0}",
        f"Gepruefte Server: {len(results)}",
        f"Zeitpunkt: {now}",
    ])

    return subject, "\n".join(lines)


def send_alert(settings: dict[str, str], subject: str, body: str) -> bool:
    mail_from = settings.get("rbl_mail_from", "")
    mail_to = settings.get("rbl_mail_to", "")
    if not mail_from or not mail_to:
        logger.warning("RBL alert: no mail_from or mail_to configured")
        return False

    msg = MIMEMultipart()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("open-mail-relay", 25, timeout=30)
        server.sendmail(mail_from, [mail_to], msg.as_string())
        server.quit()
        logger.info("RBL alert sent: %s", subject)
        return True
    except Exception as e:
        logger.error("RBL alert send failed: %s", e)
        return False


def send_test_email(db: Session) -> bool:
    """Send a test email using current RBL mail settings."""
    settings = get_rbl_settings(db)
    mail_from = settings.get("rbl_mail_from", "")
    mail_to = settings.get("rbl_mail_to", "")
    if not mail_from or not mail_to:
        return False

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "[RBL Test] Test-Mail vom RBL-Checker"
    body = (
        f"Dies ist eine Test-Mail vom RBL-Checker.\n\n"
        f"Absender: {mail_from}\n"
        f"Empfaenger: {mail_to}\n"
        f"Zeitpunkt: {now}\n\n"
        f"Wenn Sie diese Mail erhalten, funktioniert der E-Mail-Versand korrekt."
    )
    return send_alert(settings, subject, body)


def get_rbl_status(db: Session) -> dict:
    """Return a summary status for the dashboard."""
    settings = get_rbl_settings(db)
    enabled = settings.get("rbl_enabled", "false") == "true"
    last_check_time = settings.get("rbl_last_check_time", "")

    total_listings = 0
    try:
        result_data = json.loads(settings.get("rbl_last_results", "{}"))
        for r in result_data.get("results", []):
            total_listings += r.get("listed_count", 0)
    except (json.JSONDecodeError, AttributeError):
        pass

    return {
        "enabled": enabled,
        "last_check_time": last_check_time,
        "total_listings": total_listings,
        "all_clean": total_listings == 0 and bool(last_check_time),
    }


def run_rbl_check(db: Session) -> dict:
    """Main check logic: check all servers, compare state, send alert, save results."""
    settings = get_rbl_settings(db)

    # Always include own server
    own = get_server_info()
    servers = []
    if own["ip"]:
        servers.append(own)

    # Add additional servers from settings
    extra = json.loads(settings.get("rbl_servers", "[]"))
    existing_ips = {s["ip"] for s in servers}
    for s in extra:
        if s.get("ip") and s["ip"] not in existing_ips:
            servers.append(s)
            existing_ips.add(s["ip"])

    if not servers:
        logger.info("RBL check: no servers to check")
        return {"results": [], "check_time": ""}

    dns_timeout = int(settings.get("rbl_dns_timeout", "5"))
    alert_on_change_only = settings.get("rbl_alert_on_change_only", "false") == "true"

    # Run checks
    results = []
    for server in servers:
        try:
            result = check_server(server, RBL_SERVERS, dns_timeout)
            results.append(result)
        except Exception as e:
            logger.error("RBL check error for %s (%s): %s", server.get("name"), server.get("ip"), e)

    # Load previous state
    try:
        old_results = json.loads(settings.get("rbl_last_results", "{}"))
        old_state = old_results.get("state", {})
    except (json.JSONDecodeError, AttributeError):
        old_state = {}

    # Build new state
    new_state: dict[str, list] = {}
    for r in results:
        if r["listings"]:
            new_state[r["ip"]] = r["listings"]

    changes = _detect_changes(old_state, new_state)
    has_listings = any(r["listed_count"] > 0 for r in results)
    has_changes = bool(changes)

    # Send alert email
    should_send = False
    if alert_on_change_only:
        if has_changes:
            should_send = True
    else:
        if has_listings:
            should_send = True

    if should_send and settings.get("rbl_mail_to"):
        subject, body = format_alert_email(results, changes)
        send_alert(settings, subject, body)

    # Save results
    check_time = datetime.now(timezone.utc).isoformat()
    result_data = {
        "results": results,
        "state": new_state,
        "check_time": check_time,
    }
    _set_setting(db, "rbl_last_results", json.dumps(result_data, ensure_ascii=False))
    _set_setting(db, "rbl_last_check_time", check_time)
    db.commit()

    return result_data
