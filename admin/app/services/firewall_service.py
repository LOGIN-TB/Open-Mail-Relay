"""Firewall Service — manages iptables/ipset rules via Docker exec in firewall sidecar.

Uses an ipset (omr-banned) + a single iptables rule in the DOCKER-USER chain
to drop packets from banned IPs before they reach the mail container.
"""
import logging

from docker.errors import APIError, NotFound

from app.config import settings
from app.services.docker_service import get_docker_client

logger = logging.getLogger(__name__)


def _get_firewall_container():
    client = get_docker_client()
    try:
        return client.containers.get(settings.FIREWALL_CONTAINER)
    except NotFound:
        return None


def _exec_firewall(command: str) -> tuple[int, str]:
    container = _get_firewall_container()
    if container is None:
        return 1, "Firewall container not found"
    try:
        result = container.exec_run(["sh", "-c", command], demux=True)
        stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""
        return result.exit_code, stdout + stderr
    except APIError as e:
        logger.error(f"Firewall exec error: {e}")
        return 1, str(e)


def block_ip(ip_address: str) -> bool:
    """Add an IP to the firewall blocklist (ipset)."""
    code, output = _exec_firewall(f"ipset add omr-banned {ip_address} -exist")
    if code == 0:
        logger.info(f"Firewall: blocked {ip_address}")
        return True
    logger.error(f"Firewall: failed to block {ip_address}: {output}")
    return False


def unblock_ip(ip_address: str) -> bool:
    """Remove an IP from the firewall blocklist (ipset)."""
    code, output = _exec_firewall(f"ipset del omr-banned {ip_address} -exist")
    if code == 0:
        logger.info(f"Firewall: unblocked {ip_address}")
        return True
    logger.error(f"Firewall: failed to unblock {ip_address}: {output}")
    return False


def sync_bans(ip_addresses: list[str]) -> bool:
    """Full sync: flush ipset and re-add all banned IPs."""
    code, output = _exec_firewall("ipset flush omr-banned")
    if code != 0:
        logger.error(f"Firewall: failed to flush ipset: {output}")
        return False

    for ip in ip_addresses:
        _exec_firewall(f"ipset add omr-banned {ip} -exist")

    logger.info(f"Firewall: synced {len(ip_addresses)} banned IPs")
    return True
