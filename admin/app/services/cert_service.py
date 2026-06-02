import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.schemas import CertInfo, TlsStatus

logger = logging.getLogger(__name__)

# Caddy stores certificates in this path structure inside caddy-data volume
CADDY_CERT_BASE = Path("/etc/caddy-data/caddy/certificates")

# Schwellwert (Tage) ab dem ein Zertifikat als "laeuft bald ab" gilt.
# Entspricht dem Caddy-Erneuerungsfenster (~1/3 der 90-Tage-Laufzeit).
EXPIRING_THRESHOLD_DAYS = 30


def _all_cert_files(hostname: str) -> list[Path]:
    """Alle .crt-Dateien fuer einen Hostnamen ueber ALLE Aussteller-Verzeichnisse."""
    if not CADDY_CERT_BASE.exists():
        return []
    found: list[Path] = []
    # Pro ACME-Aussteller (Let's Encrypt, ZeroSSL, ...) ein Unterverzeichnis
    for acme_dir in CADDY_CERT_BASE.iterdir():
        if not acme_dir.is_dir():
            continue
        cert_file = acme_dir / hostname / f"{hostname}.crt"
        if cert_file.exists():
            found.append(cert_file)
    # Fallback: rekursiv suchen, falls die Struktur abweicht
    if not found:
        for p in CADDY_CERT_BASE.rglob(f"{hostname}.crt"):
            found.append(p)
    return found


def _find_best_cert(hostname: str) -> Path | None:
    """Waehlt das Zertifikat mit dem spaetesten Ablaufdatum (neuestes gueltiges).

    Caddy nutzt standardmaessig mehrere Aussteller (Let's Encrypt + ZeroSSL).
    Bei einem fehlgeschlagenen Renew kann ein abgelaufenes Cert eines Ausstellers
    neben einem gueltigen eines anderen liegen — daher nie einfach das erste,
    sondern das mit dem spaetesten notAfter nehmen.
    """
    candidates = _all_cert_files(hostname)
    if not candidates:
        return None

    best: Path | None = None
    best_expiry: datetime | None = None
    for cert_file in candidates:
        info = _read_cert_info(cert_file)
        expiry = info.get("expiry")
        if expiry is None:
            continue
        if best_expiry is None or expiry > best_expiry:
            best_expiry = expiry
            best = cert_file
    # Falls keines parsebar war, irgendeines zurueckgeben (besser als nichts)
    return best or candidates[0]


def _read_cert_info(cert_file: Path) -> dict:
    """Read expiry, subject and issuer from a PEM certificate file."""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_file), "-noout", "-enddate", "-subject", "-issuer"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return {}

        info = {}
        for line in result.stdout.splitlines():
            if line.startswith("notAfter="):
                date_str = line.split("=", 1)[1]
                try:
                    info["expiry"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            if line.startswith("subject="):
                info["subject"] = line.split("=", 1)[1].strip()
            if line.startswith("issuer="):
                info["issuer"] = line.split("=", 1)[1].strip()
        return info
    except Exception as e:
        logger.error(f"Error reading certificate: {e}")
        return {}


def _status_for(expiry: datetime | None) -> tuple[str, int | None]:
    """Liefert (status, days_remaining) fuer ein Ablaufdatum."""
    if expiry is None:
        return "missing", None
    now = datetime.now(timezone.utc)
    days = (expiry - now).days
    if expiry <= now:
        return "expired", days
    if days < EXPIRING_THRESHOLD_DAYS:
        return "expiring", days
    return "valid", days


def _check_postfix_has_cert() -> bool:
    """Check if Postfix in the open-mail-relay container currently has a TLS cert configured."""
    from app.services.docker_service import exec_in_container
    exit_code, output = exec_in_container("postconf smtpd_tls_cert_file")
    if exit_code != 0:
        return False
    # postconf returns: smtpd_tls_cert_file = /path/to/cert
    parts = output.strip().split("=", 1)
    if len(parts) < 2:
        return False
    cert_path = parts[1].strip()
    if not cert_path or cert_path == "":
        return False
    # Check if the file actually exists in the container
    exit_code2, _ = exec_in_container(f"test -f {cert_path}")
    return exit_code2 == 0


def _get_mail_hostname() -> str:
    """Liest den Mail-Hostname aus postfix/main.cf (Single Source of Truth)."""
    from app.services.postfix_service import read_main_cf
    cf = read_main_cf()
    return cf.get("myhostname", "localhost")


def _build_cert_info(hostname: str, role: str, postfix_has_cert: bool) -> CertInfo:
    """Baut einen CertInfo-Eintrag fuer einen Hostnamen."""
    cert_file = _find_best_cert(hostname)
    if cert_file is None:
        return CertInfo(name=hostname, role=role, exists=False, status="missing")

    info = _read_cert_info(cert_file)
    expiry = info.get("expiry")
    status, days = _status_for(expiry)
    return CertInfo(
        name=hostname,
        role=role,
        exists=True,
        subject=info.get("subject"),
        issuer=info.get("issuer"),
        expiry=expiry,
        days_remaining=days,
        status=status,
        is_postfix_cert=(role == "mail" and postfix_has_cert),
    )


def get_all_certs() -> list[CertInfo]:
    """Alle von Caddy verwalteten Relay-Zertifikate (Admin- + Mail-Hostname)."""
    mail_host = _get_mail_hostname()
    admin_host = settings.ADMIN_HOSTNAME
    postfix_has_cert = _check_postfix_has_cert()

    certs: list[CertInfo] = []
    seen: set[str] = set()

    # Mail-Hostname zuerst (primaeres Zertifikat fuer den Mailverkehr)
    if mail_host and mail_host != "localhost":
        certs.append(_build_cert_info(mail_host, "mail", postfix_has_cert))
        seen.add(mail_host)

    # Admin-Hostname, falls abweichend
    if admin_host and admin_host not in seen and admin_host != "admin.example.com":
        certs.append(_build_cert_info(admin_host, "admin", postfix_has_cert))
        seen.add(admin_host)

    return certs


def get_tls_status() -> TlsStatus:
    # Mail-Zertifikat (Single-Cert-Felder fuer Rueckwaertskompatibilitaet, z.B. ConnectionInfo)
    cert_file = _find_best_cert(_get_mail_hostname())
    postfix_has_cert = _check_postfix_has_cert()
    certs = get_all_certs()

    if cert_file is None:
        return TlsStatus(
            enabled=False,
            cert_exists=False,
            postfix_has_cert=postfix_has_cert,
            certs=certs,
        )

    info = _read_cert_info(cert_file)
    return TlsStatus(
        enabled=True,
        cert_exists=True,
        cert_expiry=info.get("expiry"),
        cert_subject=info.get("subject"),
        postfix_has_cert=postfix_has_cert,
        certs=certs,
    )


def wait_for_cert(hostname: str, timeout: int = 30) -> bool:
    """Poll every 2s until Caddy has a cert for the given hostname (max timeout seconds)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _find_best_cert(hostname) is not None:
            return True
        time.sleep(2)
    return False


def sync_certs_to_postfix() -> tuple[bool, str]:
    """Trigger certificate sync from Caddy to Postfix via docker exec."""
    from app.services.docker_service import exec_in_container

    hostname = _get_mail_hostname()

    # Find cert for mail hostname only (never fall back to admin cert)
    cert_file = _find_best_cert(hostname)
    source_host = hostname

    if cert_file is None:
        return False, "Kein Zertifikat in Caddy gefunden. Caddy muss zuerst ein Zertifikat beschaffen."

    # The cert and key are in the same directory
    key_file = cert_file.parent / f"{source_host}.key"
    if not key_file.exists():
        return False, f"Zertifikats-Key nicht gefunden: {key_file}"

    # Copy certs into the open-mail-relay container
    # The caddy-data volume is mounted at /etc/caddy-data in open-mail-relay
    caddy_cert_rel = str(cert_file)
    caddy_key_rel = str(key_file)

    commands = [
        "mkdir -p /etc/postfix/tls",
        f"cp {caddy_cert_rel} /etc/postfix/tls/cert.pem",
        f"cp {caddy_key_rel} /etc/postfix/tls/key.pem",
        "chmod 600 /etc/postfix/tls/key.pem",
        "chmod 644 /etc/postfix/tls/cert.pem",
        "postconf -e 'smtpd_tls_cert_file = /etc/postfix/tls/cert.pem'",
        "postconf -e 'smtpd_tls_key_file = /etc/postfix/tls/key.pem'",
        "postfix reload",
    ]

    script = " && ".join(commands)
    exit_code, output = exec_in_container(f"sh -c {repr(script)}")

    if exit_code == 0:
        return True, f"Zertifikat von '{source_host}' nach Postfix synchronisiert und Postfix neu geladen."
    else:
        return False, f"Fehler bei Zertifikats-Sync: {output}"


def renew_certs() -> tuple[bool, str]:
    """Erzwingt eine Zertifikats-Erneuerung: Caddy graceful neu laden, auf Cert warten, nach Postfix syncen.

    Es wird BEWUSST ein graceful 'caddy reload' (Zero-Downtime) statt eines
    Container-Neustarts verwendet: Das Admin-Panel laeuft selbst durch Caddy
    (reverse_proxy), ein Neustart wuerde die HTTP-Verbindung des Auslosers kappen
    und das Frontend wuerde faelschlich einen Fehler melden (obwohl die Erneuerung
    serverseitig laeuft). Der Reload stoesst eine erneute Caddy-Zertifikatsverwaltung
    an (Renew faelliger/abgelaufener Certs); fuer gueltige Certs ist es ein No-op
    (kein Let's-Encrypt-Rate-Limit-Risiko). Die Cert-Dateien werden NICHT geloescht.
    """
    from app.services.docker_service import reload_caddy

    hostname = _get_mail_hostname()

    caddy_ok, caddy_msg = reload_caddy(hostname)
    if not caddy_ok:
        return False, f"Caddy-Reload fehlgeschlagen: {caddy_msg}"

    # Caddy braucht nach dem Reload einen Moment, bis ein evtl. neues Cert bereit ist
    if not wait_for_cert(hostname, timeout=60):
        return False, "Caddy neu geladen, aber Zertifikat war nicht innerhalb von 60s bereit."

    sync_ok, sync_msg = sync_certs_to_postfix()
    if not sync_ok:
        return False, f"Caddy neu geladen, aber Postfix-Sync fehlgeschlagen: {sync_msg}"

    return True, f"Zertifikate erneuert (Caddy neu geladen) und nach Postfix synchronisiert. {sync_msg}"
