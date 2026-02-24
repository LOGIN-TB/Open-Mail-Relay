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


def get_container_status() -> dict:
    container = get_mail_container()
    if container is None:
        return {"status": "not_found", "running": False}
    return {
        "status": container.status,
        "running": container.status == "running",
        "started_at": container.attrs.get("State", {}).get("StartedAt"),
    }
