import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import TlsStatus

logger = logging.getLogger(__name__)

# Caddy stores certificates in this path structure inside caddy-data volume
CADDY_CERT_BASE = Path("/etc/caddy-data/caddy/certificates")


def _find_cert_file(hostname: str) -> Path | None:
    """Search for cert in all ACME directory structures."""
    if not CADDY_CERT_BASE.exists():
        return None
    # Search in all ACME provider directories
    for acme_dir in CADDY_CERT_BASE.iterdir():
        if not acme_dir.is_dir():
            continue
        cert_dir = acme_dir / hostname
        cert_file = cert_dir / f"{hostname}.crt"
        if cert_file.exists():
            return cert_file
    # Fallback: search recursively
    for p in CADDY_CERT_BASE.rglob("*.crt"):
        if hostname in p.name:
            return p
    return None


def _read_cert_info(cert_file: Path) -> dict:
    """Read expiry and subject from a PEM certificate file."""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_file), "-noout", "-enddate", "-subject"],
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
        return info
    except Exception as e:
        logger.error(f"Error reading certificate: {e}")
        return {}


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


def get_tls_status() -> TlsStatus:
    # Check for mail hostname cert
    cert_file = _find_cert_file(_get_mail_hostname())

    postfix_has_cert = _check_postfix_has_cert()

    if cert_file is None:
        return TlsStatus(
            enabled=False,
            cert_exists=False,
            postfix_has_cert=postfix_has_cert,
        )

    info = _read_cert_info(cert_file)
    return TlsStatus(
        enabled=True,
        cert_exists=True,
        cert_expiry=info.get("expiry"),
        cert_subject=info.get("subject"),
        postfix_has_cert=postfix_has_cert,
    )


def wait_for_cert(hostname: str, timeout: int = 30) -> bool:
    """Poll every 2s until Caddy has a cert for the given hostname (max timeout seconds)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _find_cert_file(hostname) is not None:
            return True
        time.sleep(2)
    return False


def sync_certs_to_postfix() -> tuple[bool, str]:
    """Trigger certificate sync from Caddy to Postfix via docker exec."""
    from app.services.docker_service import exec_in_container

    hostname = _get_mail_hostname()

    # Find cert for mail hostname only (never fall back to admin cert)
    cert_file = _find_cert_file(hostname)
    source_host = hostname

    if cert_file is None:
        return False, "Kein Zertifikat in Caddy gefunden. Caddy muss zuerst ein Zertifikat beschaffen."

    # The cert and key are in the same directory
    key_file = cert_file.parent / f"{source_host}.key"
    if not key_file.exists():
        return False, f"Zertifikats-Key nicht gefunden: {key_file}"

    # Copy certs into the open-mail-relay container
    # The caddy-data volume is mounted at /etc/caddy-data in open-mail-relay
    caddy_cert_rel = str(cert_file).replace("/etc/caddy-data/", "/etc/caddy-data/")
    caddy_key_rel = str(key_file).replace("/etc/caddy-data/", "/etc/caddy-data/")

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
