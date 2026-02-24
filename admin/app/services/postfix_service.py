import logging
import re
from pathlib import Path

from app.config import settings
from app.services.docker_service import exec_in_container, reload_postfix

logger = logging.getLogger(__name__)

MYNETWORKS_FILE = settings.POSTFIX_CONFIG_PATH / "mynetworks"
MAIN_CF_FILE = settings.POSTFIX_CONFIG_PATH / "main.cf"

# Protected networks that cannot be removed
PROTECTED_NETWORKS = {"127.0.0.0/8", "172.16.0.0/12"}


def read_mynetworks() -> list[str]:
    try:
        content = MYNETWORKS_FILE.read_text().strip()
        return [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
    except FileNotFoundError:
        return list(PROTECTED_NETWORKS)


def write_mynetworks(networks: list[str]) -> None:
    # Always ensure protected networks are present
    network_set = set(networks)
    for net in PROTECTED_NETWORKS:
        network_set.add(net)
    MYNETWORKS_FILE.write_text("\n".join(sorted(network_set)) + "\n")


def add_network(cidr: str) -> tuple[bool, str]:
    networks = read_mynetworks()
    if cidr in networks:
        return False, f"Network {cidr} already exists"
    networks.append(cidr)
    write_mynetworks(networks)
    success, output = reload_postfix()
    if not success:
        return False, f"Network added but Postfix reload failed: {output}"
    return True, f"Network {cidr} added successfully"


def remove_network(cidr: str) -> tuple[bool, str]:
    if cidr in PROTECTED_NETWORKS:
        return False, f"Cannot remove protected network {cidr}"
    networks = read_mynetworks()
    if cidr not in networks:
        return False, f"Network {cidr} not found"
    networks.remove(cidr)
    write_mynetworks(networks)
    success, output = reload_postfix()
    if not success:
        return False, f"Network removed but Postfix reload failed: {output}"
    return True, f"Network {cidr} removed successfully"


def get_queue() -> list[dict]:
    exit_code, output = exec_in_container("mailq")
    if exit_code != 0 or "Mail queue is empty" in output:
        return []

    entries = []
    current: dict | None = None

    for line in output.splitlines():
        # Queue entry header: queue_id* size day_of_week month day time sender
        match = re.match(
            r"^([A-F0-9]+[*!]?)\s+(\d+)\s+(\w+ \w+ +\d+ \d+:\d+:\d+)\s+(.+)$",
            line,
        )
        if match:
            if current:
                entries.append(current)
            current = {
                "queue_id": match.group(1).rstrip("*!"),
                "size": match.group(2),
                "arrival_time": match.group(3),
                "sender": match.group(4),
                "recipients": [],
            }
        elif current and line.strip() and not line.startswith("-") and not line.startswith("--"):
            recipient = line.strip()
            if recipient and "(" not in recipient[:1]:
                current["recipients"].append(recipient.split(" ")[0])

    if current:
        entries.append(current)

    return entries


def get_queue_size() -> int:
    exit_code, output = exec_in_container("mailq")
    if exit_code != 0:
        return 0
    if "Mail queue is empty" in output:
        return 0
    # Last line typically: "-- N Kbytes in M Requests."
    match = re.search(r"(\d+) Request", output)
    return int(match.group(1)) if match else 0


def read_main_cf() -> dict[str, str]:
    config = {}
    try:
        for line in MAIN_CF_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return config


def update_main_cf(key: str, value: str) -> None:
    lines = MAIN_CF_FILE.read_text().splitlines()
    updated = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key} =") or stripped.startswith(f"{key}="):
            lines[i] = f"{key} = {value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key} = {value}")
    MAIN_CF_FILE.write_text("\n".join(lines) + "\n")
