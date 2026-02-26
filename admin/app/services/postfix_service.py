import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.services.docker_service import exec_in_container, reload_postfix

logger = logging.getLogger(__name__)

MYNETWORKS_FILE = settings.POSTFIX_CONFIG_PATH / "mynetworks"
MAIN_CF_FILE = settings.POSTFIX_CONFIG_PATH / "main.cf"


def generate_mynetworks_file(db: Session) -> tuple[bool, str]:
    """Generate mynetworks file from DB and reload Postfix."""
    from app.models import Network

    networks = db.query(Network).order_by(Network.cidr).all()
    cidrs = [n.cidr for n in networks]

    MYNETWORKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    MYNETWORKS_FILE.write_text("\n".join(cidrs) + "\n")

    success, output = reload_postfix()
    if not success:
        logger.error(f"Postfix reload failed after mynetworks update: {output}")
        return False, output
    return True, "mynetworks updated"


def get_networks_count(db: Session) -> int:
    """Return count of networks from DB."""
    from app.models import Network

    return db.query(Network).count()


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
