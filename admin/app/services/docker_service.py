import logging

import docker
from docker.errors import APIError, NotFound

from app.config import settings

logger = logging.getLogger(__name__)

_client: docker.DockerClient | None = None


def get_docker_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
    return _client


def get_mail_container():
    client = get_docker_client()
    try:
        return client.containers.get(settings.MAIL_RELAY_CONTAINER)
    except NotFound:
        logger.error(f"Container '{settings.MAIL_RELAY_CONTAINER}' not found")
        return None


def exec_in_container(command: str) -> tuple[int, str]:
    container = get_mail_container()
    if container is None:
        return 1, "Open Mail Relay container not found"
    try:
        result = container.exec_run(command, demux=True)
        stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""
        return result.exit_code, stdout + stderr
    except APIError as e:
        logger.error(f"Docker exec error: {e}")
        return 1, str(e)


def reload_postfix() -> tuple[bool, str]:
    exit_code, output = exec_in_container("postfix reload")
    return exit_code == 0, output


def get_container_logs(tail: int = 100) -> str:
    container = get_mail_container()
    if container is None:
        return ""
    try:
        return container.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
    except APIError as e:
        logger.error(f"Error getting logs: {e}")
        return ""


def get_caddy_container():
    client = get_docker_client()
    try:
        return client.containers.get(settings.CADDY_CONTAINER)
    except NotFound:
        logger.error(f"Container '{settings.CADDY_CONTAINER}' not found")
        return None


def restart_caddy() -> tuple[bool, str]:
    container = get_caddy_container()
    if container is None:
        return False, "Caddy container not found"
    try:
        container.restart(timeout=10)
        return True, "Caddy container restarted"
    except APIError as e:
        logger.error(f"Caddy restart error: {e}")
        return False, str(e)


def reload_caddy(mail_hostname: str = "") -> tuple[bool, str]:
    """Graceful Caddy-Reload (Zero-Downtime) statt Container-Neustart.

    Wichtig: Das Admin-Panel wird durch Caddy geproxyt. Ein Container-Neustart
    (restart_caddy) kappt die laufende HTTP-Verbindung des Browsers mitten im
    Request -> der ausloesende Aufruf erhaelt nie seine Antwort und das Frontend
    meldet faelschlich einen Fehler. 'caddy reload' laedt die Konfiguration ueber
    die Admin-API (localhost:2019) neu, ohne bestehende Verbindungen zu trennen,
    und stoesst dabei eine erneute Zertifikats-Verwaltung (Renew faelliger Certs) an.

    Das Caddyfile nutzt {$MAIL_HOSTNAME}. Diese Variable wird NICHT ueber Compose
    gesetzt, sondern erst im Caddy-Entrypoint aus main.cf abgeleitet (caddy/entrypoint.sh)
    und ist daher in einem 'docker exec'-Kontext leer. Ohne sie scheitert das Adaptieren
    des Caddyfiles ("server block without any key ..."). Wir injizieren MAIL_HOSTNAME
    daher explizit; ADMIN_HOSTNAME/LETSENCRYPT_EMAIL kommen aus der Container-Umgebung.
    """
    container = get_caddy_container()
    if container is None:
        return False, "Caddy container not found"

    env = {"MAIL_HOSTNAME": mail_hostname} if mail_hostname else None
    try:
        result = container.exec_run(
            "caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile",
            environment=env,
        )
        output = result.output.decode("utf-8", errors="replace") if result.output else ""
        if result.exit_code == 0:
            return True, "Caddy konfiguration neu geladen (graceful)"
        return False, f"Caddy reload fehlgeschlagen: {output.strip()}"
    except APIError as e:
        logger.error(f"Caddy reload error: {e}")
        return False, str(e)


def get_container_status() -> dict:
    container = get_mail_container()
    if container is None:
        return {"status": "not_found", "running": False}
    return {
        "status": container.status,
        "running": container.status == "running",
        "started_at": container.attrs.get("State", {}).get("StartedAt"),
    }


# ---------------------------------------------------------------------------
# Generic container management
# ---------------------------------------------------------------------------

# Allowed containers (name -> config key)
CONTAINER_NAMES = {
    "open-mail-relay": settings.MAIL_RELAY_CONTAINER,
    "caddy": settings.CADDY_CONTAINER,
    "firewall": settings.FIREWALL_CONTAINER,
}


def list_containers() -> list[dict]:
    """Return status of all managed containers."""
    client = get_docker_client()
    result = []
    for label, name in CONTAINER_NAMES.items():
        try:
            c = client.containers.get(name)
            state = c.attrs.get("State", {})
            result.append({
                "name": name,
                "label": label,
                "status": c.status,
                "running": c.status == "running",
                "started_at": state.get("StartedAt", ""),
                "image": c.image.tags[0] if c.image.tags else "",
            })
        except NotFound:
            result.append({
                "name": name,
                "label": label,
                "status": "not_found",
                "running": False,
                "started_at": "",
                "image": "",
            })
    return result


def restart_container(name: str) -> tuple[bool, str]:
    """Restart a managed container by name."""
    # Validate: only allow known containers
    allowed = set(CONTAINER_NAMES.values())
    if name not in allowed:
        return False, f"Container '{name}' ist nicht verwaltbar"

    client = get_docker_client()
    try:
        container = client.containers.get(name)
        container.restart(timeout=15)
        logger.info("Container '%s' restarted", name)
        return True, f"Container '{name}' wurde neu gestartet"
    except NotFound:
        return False, f"Container '{name}' nicht gefunden"
    except APIError as e:
        logger.error("Container restart error for '%s': %s", name, e)
        return False, str(e)
