"""DNS Record Checker — validates SPF, DMARC and DKIM records for the mail server."""

import ipaddress
import json
import logging
import re
import socket
from datetime import datetime, timezone
from pathlib import Path

import dns.resolver

from sqlalchemy.orm import Session

from app.models import SystemSetting

logger = logging.getLogger(__name__)

DNS_TIMEOUT = 5
DKIM_DIR = Path("/etc/postfix-config/dkim")

DEFAULTS: dict[str, str] = {
    "dns_check_dkim_selector": "default",
    "dns_check_last_results": "{}",
    "dns_check_last_check_time": "",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))


def _get_setting(db: Session, key: str) -> str:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row else DEFAULTS.get(key, "")


def _resolve_txt(domain: str) -> list[str]:
    """Resolve TXT records for *domain*, returning concatenated strings."""
    try:
        answers = dns.resolver.resolve(domain, "TXT", lifetime=DNS_TIMEOUT)
        results = []
        for rdata in answers:
            # TXT records may be split into multiple strings — concatenate
            txt = b"".join(rdata.strings).decode("utf-8", errors="replace")
            results.append(txt)
        return results
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return []
    except dns.resolver.LifetimeTimeout:
        raise
    except Exception as exc:
        logger.warning("DNS TXT query for %s failed: %s", domain, exc)
        return []


def _extract_domain(hostname: str) -> str:
    """Extract registerable domain from hostname (remove first label if >2 labels)."""
    parts = hostname.rstrip(".").split(".")
    if len(parts) > 2:
        return ".".join(parts[1:])
    return ".".join(parts)


# ---------------------------------------------------------------------------
# Server info
# ---------------------------------------------------------------------------

def get_server_info() -> dict[str, str]:
    """Read hostname from Postfix config, resolve IP, extract domain."""
    from app.services.postfix_service import read_main_cf

    cf = read_main_cf()
    hostname = cf.get("myhostname", "localhost")
    ip = ""
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        if results:
            ip = results[0][4][0]
    except (socket.gaierror, OSError) as exc:
        logger.warning("Could not resolve hostname %s: %s", hostname, exc)

    domain = _extract_domain(hostname)
    return {"hostname": hostname, "ip": ip, "domain": domain}


def _default_dkim_selector() -> str:
    """Derive DKIM selector from hostname (first label, e.g. relay2.spamgo.de -> relay2)."""
    info = get_server_info()
    hostname = info.get("hostname", "")
    if hostname and "." in hostname:
        return hostname.split(".")[0]
    return "default"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def get_dkim_selector() -> str:
    """Always derive DKIM selector from hostname — not user-configurable."""
    return _default_dkim_selector()


def get_dns_check_settings(db: Session) -> dict:
    dkim_selector = get_dkim_selector()
    last_check_time = _get_setting(db, "dns_check_last_check_time")
    last_results = None
    raw = _get_setting(db, "dns_check_last_results")
    if raw and raw != "{}":
        try:
            last_results = json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {
        "dkim_selector": dkim_selector,
        "last_results": last_results,
        "last_check_time": last_check_time,
    }


# ---------------------------------------------------------------------------
# SPF check
# ---------------------------------------------------------------------------

def _ip_in_network(ip_str: str, network_str: str) -> bool:
    """Check if *ip_str* is within *network_str* (single IP or CIDR)."""
    try:
        addr = ipaddress.ip_address(ip_str)
        net = ipaddress.ip_network(network_str, strict=False)
        return addr in net
    except ValueError:
        return False


def _check_spf_record(spf_record: str, server_ip: str, spf_domain: str,
                       depth: int = 0, max_depth: int = 5) -> tuple[bool, str]:
    """Parse an SPF record and check if server_ip is authorised.

    Returns (ip_found, via_description).
    *via_description* names the include chain that matched (e.g. "include:spf.example.com").
    Recursion is capped at *max_depth* to stay within RFC 7208 limits.
    """
    if depth > max_depth:
        return False, ""

    parts = spf_record.split()
    for part in parts:
        p = part.lstrip("+-~?")

        if p.startswith("ip4:") or p.startswith("ip6:"):
            network = p.split(":", 1)[1]
            if server_ip and _ip_in_network(server_ip, network):
                return True, p

        elif p == "a" or p.startswith("a:"):
            a_domain = p.split(":", 1)[1] if ":" in p else spf_domain
            try:
                for rdata in dns.resolver.resolve(a_domain, "A", lifetime=DNS_TIMEOUT):
                    if str(rdata) == server_ip:
                        return True, f"a:{a_domain}" if ":" in p else "a"
            except Exception:
                pass

        elif p == "mx" or p.startswith("mx:"):
            mx_domain = p.split(":", 1)[1] if ":" in p else spf_domain
            try:
                for mx in dns.resolver.resolve(mx_domain, "MX", lifetime=DNS_TIMEOUT):
                    try:
                        for rdata in dns.resolver.resolve(str(mx.exchange), "A", lifetime=DNS_TIMEOUT):
                            if str(rdata) == server_ip:
                                return True, f"mx:{mx_domain}" if ":" in p else "mx"
                    except Exception:
                        pass
            except Exception:
                pass

        elif p.startswith("include:"):
            include_domain = p.split(":", 1)[1]
            try:
                inc_txts = _resolve_txt(include_domain)
                for inc_txt in inc_txts:
                    if inc_txt.strip().startswith("v=spf1"):
                        found, via = _check_spf_record(
                            inc_txt.strip(), server_ip, include_domain,
                            depth + 1, max_depth,
                        )
                        if found:
                            chain = f"include:{include_domain}"
                            if via:
                                chain += f" -> {via}"
                            return True, chain
                        break
            except Exception:
                pass

    return False, ""


def check_spf(domain: str, server_ip: str, hostname: str) -> dict:
    result = {
        "type": "spf",
        "status": "missing",
        "record": None,
        "details": "",
        "suggested_record": f"v=spf1 ip4:{server_ip} a mx ~all" if server_ip else "v=spf1 a mx ~all",
        "lookup_domain": domain,
    }

    try:
        txt_records = _resolve_txt(domain)
    except dns.resolver.LifetimeTimeout:
        result["status"] = "error"
        result["details"] = f"DNS-Timeout bei Abfrage von {domain}"
        return result

    spf_record = None
    for txt in txt_records:
        if txt.strip().startswith("v=spf1"):
            spf_record = txt.strip()
            break

    if not spf_record:
        result["details"] = f"Kein SPF-Record fuer {domain} gefunden."
        return result

    result["record"] = spf_record

    # Check if server IP is covered (including recursive include: resolution)
    ip_found, via = _check_spf_record(spf_record, server_ip, domain)

    if ip_found:
        result["status"] = "pass"
        if via and via.startswith("include:"):
            result["details"] = (
                f"Server-IP {server_ip} ist im SPF-Record autorisiert "
                f"(ueber {via})."
            )
        else:
            result["details"] = f"Server-IP {server_ip} ist im SPF-Record autorisiert."
        result["suggested_record"] = None
    else:
        result["status"] = "fail"
        result["details"] = (
            f"SPF-Record vorhanden, aber Server-IP {server_ip} ist nicht autorisiert. "
            f"Bitte den SPF-Record aktualisieren."
        )

    return result


# ---------------------------------------------------------------------------
# DMARC check
# ---------------------------------------------------------------------------

def check_dmarc(domain: str) -> dict:
    lookup = f"_dmarc.{domain}"
    result = {
        "type": "dmarc",
        "status": "missing",
        "record": None,
        "details": "",
        "suggested_record": f"v=DMARC1; p=quarantine; rua=mailto:postmaster@{domain}",
        "lookup_domain": lookup,
    }

    try:
        txt_records = _resolve_txt(lookup)
    except dns.resolver.LifetimeTimeout:
        result["status"] = "error"
        result["details"] = f"DNS-Timeout bei Abfrage von {lookup}"
        return result

    dmarc_record = None
    for txt in txt_records:
        if txt.strip().startswith("v=DMARC1"):
            dmarc_record = txt.strip()
            break

    if not dmarc_record:
        result["details"] = f"Kein DMARC-Record fuer {lookup} gefunden."
        return result

    result["record"] = dmarc_record

    # Parse policy
    policy = None
    for part in dmarc_record.replace(";", " ").split():
        if part.startswith("p="):
            policy = part.split("=", 1)[1]
            break

    if policy:
        result["status"] = "pass"
        result["details"] = f"DMARC-Record gefunden mit Policy: {policy}"
        result["suggested_record"] = None
    else:
        result["status"] = "warn"
        result["details"] = "DMARC-Record gefunden, aber keine Policy (p=) definiert."

    return result


# ---------------------------------------------------------------------------
# DKIM key reading
# ---------------------------------------------------------------------------

def get_dkim_public_key(selector: str = "default") -> dict:
    """Read the DKIM public key from the generated key file."""
    txt_file = DKIM_DIR / f"{selector}.txt"
    if not txt_file.exists():
        return {"exists": False, "selector": selector, "dns_record": "", "dns_name": ""}

    raw = txt_file.read_text()

    # opendkim-genkey produces a file like:
    # default._domainkey	IN	TXT	( "v=DKIM1; h=sha256; k=rsa; "
    #     "p=MIIBIjANBg..." )  ; ----- DKIM key default for domain
    # Extract the record name and the quoted strings
    name_match = re.match(r'^(\S+)', raw)
    dns_name = name_match.group(1) if name_match else f"{selector}._domainkey"

    # Extract all quoted strings and concatenate
    parts = re.findall(r'"([^"]*)"', raw)
    dns_value = "".join(parts)

    return {
        "exists": True,
        "selector": selector,
        "dns_record": dns_value,
        "dns_name": dns_name,
        "raw_file": raw,
    }


def delete_dkim_key(selector: str) -> bool:
    """Delete DKIM key pair. Returns True if files were removed."""
    private_file = DKIM_DIR / f"{selector}.private"
    txt_file = DKIM_DIR / f"{selector}.txt"
    deleted = False
    for f in (private_file, txt_file):
        if f.exists():
            f.unlink()
            deleted = True
    if deleted:
        logger.info("DKIM key pair deleted for selector '%s'", selector)
    return deleted


# ---------------------------------------------------------------------------
# DKIM check
# ---------------------------------------------------------------------------

def check_dkim(domain: str, selector: str) -> dict:
    lookup = f"{selector}._domainkey.{domain}"
    result = {
        "type": "dkim",
        "status": "missing",
        "record": None,
        "details": "",
        "suggested_record": None,
        "lookup_domain": lookup,
    }

    try:
        txt_records = _resolve_txt(lookup)
    except dns.resolver.LifetimeTimeout:
        result["status"] = "error"
        result["details"] = f"DNS-Timeout bei Abfrage von {lookup}"
        return result

    if not txt_records:
        # Check if we have a locally generated key to suggest
        key_info = get_dkim_public_key(selector)
        if key_info["exists"]:
            result["suggested_record"] = key_info["dns_record"]
            result["details"] = (
                f"Kein DKIM-Record fuer {lookup} gefunden. "
                f"Der Server hat bereits einen DKIM-Schluessel generiert. "
                f"Bitte den unten angezeigten TXT-Record beim DNS-Provider hinterlegen."
            )
        else:
            result["details"] = (
                f"Kein DKIM-Record fuer {lookup} gefunden. "
                f"DKIM muss zuerst auf dem Mail-Server konfiguriert werden, "
                f"dann der oeffentliche Schluessel als TXT-Record hinterlegt werden."
            )
        return result

    # Look for DKIM record (v=DKIM1 or contains p=)
    dkim_record = None
    for txt in txt_records:
        if "v=DKIM1" in txt or "p=" in txt:
            dkim_record = txt.strip()
            break

    if not dkim_record:
        # There are TXT records but none look like DKIM
        dkim_record = txt_records[0].strip()
        result["record"] = dkim_record
        result["status"] = "warn"
        result["details"] = (
            f"TXT-Record fuer {lookup} gefunden, aber kein gueltiger DKIM-Record (v=DKIM1) erkannt."
        )
        return result

    result["record"] = dkim_record

    # Check for public key
    has_key = False
    for part in dkim_record.replace(";", " ").split():
        if part.startswith("p=") and len(part) > 2:
            has_key = True
            break

    if has_key:
        result["status"] = "pass"
        result["details"] = f"DKIM-Record mit oeffentlichem Schluessel gefunden fuer Selector '{selector}'."
    else:
        result["status"] = "warn"
        result["details"] = "DKIM-Record gefunden, aber kein oeffentlicher Schluessel (p=) vorhanden."

    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_dns_check(db: Session) -> dict:
    """Run all DNS checks and persist results."""
    info = get_server_info()
    hostname = info["hostname"]
    server_ip = info["ip"]
    domain = info["domain"]
    dkim_selector = get_dkim_selector()

    spf = check_spf(domain, server_ip, hostname)
    dmarc = check_dmarc(domain)
    dkim = check_dkim(domain, dkim_selector)

    # Compute overall status
    statuses = [spf["status"], dmarc["status"], dkim["status"]]
    if all(s == "pass" for s in statuses):
        overall = "pass"
    elif any(s in ("fail", "missing") for s in statuses):
        overall = "fail"
    else:
        overall = "warn"

    check_time = datetime.now(timezone.utc).isoformat()

    result = {
        "hostname": hostname,
        "ip": server_ip,
        "domain": domain,
        "dkim_selector": dkim_selector,
        "spf": spf,
        "dmarc": dmarc,
        "dkim": dkim,
        "overall_status": overall,
        "check_time": check_time,
    }

    # Persist
    _set_setting(db, "dns_check_last_results", json.dumps(result, ensure_ascii=False))
    _set_setting(db, "dns_check_last_check_time", check_time)
    db.commit()

    return result


# ---------------------------------------------------------------------------
# Dashboard status
# ---------------------------------------------------------------------------

def get_dns_check_status(db: Session) -> dict:
    last_check_time = _get_setting(db, "dns_check_last_check_time")
    if not last_check_time:
        return {
            "checked": False,
            "spf_ok": False,
            "dmarc_ok": False,
            "dkim_ok": False,
            "all_ok": False,
            "last_check_time": "",
            "issues": 0,
        }

    raw = _get_setting(db, "dns_check_last_results")
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {}

    spf_ok = data.get("spf", {}).get("status") == "pass"
    dmarc_ok = data.get("dmarc", {}).get("status") == "pass"
    dkim_ok = data.get("dkim", {}).get("status") == "pass"
    issues = sum(1 for ok in [spf_ok, dmarc_ok, dkim_ok] if not ok)

    return {
        "checked": True,
        "spf_ok": spf_ok,
        "dmarc_ok": dmarc_ok,
        "dkim_ok": dkim_ok,
        "all_ok": issues == 0,
        "last_check_time": last_check_time,
        "issues": issues,
    }
