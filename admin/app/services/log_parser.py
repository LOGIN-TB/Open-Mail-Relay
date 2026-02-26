import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ParsedMailEvent:
    timestamp: datetime
    queue_id: str | None = None
    sender: str | None = None
    recipient: str | None = None
    status: str | None = None  # sent, deferred, bounced, rejected
    relay: str | None = None
    delay: float | None = None
    dsn: str | None = None
    size: int | None = None
    message: str | None = None
    client_ip: str | None = None
    sasl_username: str | None = None


# Postfix log patterns
# Status line: to=<recipient>, relay=..., delay=..., delays=..., dsn=..., status=sent/deferred/bounced
STATUS_RE = re.compile(
    r"(?P<queue_id>[A-F0-9]+): "
    r"to=<(?P<recipient>[^>]*)>.*?"
    r"(?:relay=(?P<relay>[^,]+))?,?\s*"
    r"(?:delay=(?P<delay>[\d.]+))?,?\s*"
    r".*?"
    r"(?:dsn=(?P<dsn>[\d.]+))?,?\s*"
    r"status=(?P<status>\w+)"
    r"(?:\s+\((?P<message>[^)]*)\))?"
)

# From line: from=<sender>, size=..., nrcpt=...
FROM_RE = re.compile(
    r"(?P<queue_id>[A-F0-9]+): "
    r"from=<(?P<sender>[^>]*)>.*?"
    r"(?:size=(?P<size>\d+))?"
)

# Client line: QUEUE_ID: client=hostname[IP], sasl_method=..., sasl_username=...
CLIENT_RE = re.compile(
    r"(?P<queue_id>[A-F0-9]+): "
    r"client=[^\[]*\[(?P<client_ip>[^\]]+)\]"
    r"(?:.*?sasl_username=(?P<sasl_username>\S+))?"
)

# Reject line: NOQUEUE: reject: ... from hostname[IP] ...
REJECT_RE = re.compile(
    r"NOQUEUE: reject:.*?"
    r"from\s+[^\[]*\[(?P<client_ip>[^\]]+)\].*?"
    r"from=<(?P<sender>[^>]*)>.*?to=<(?P<recipient>[^>]*)>"
)

# Timestamp pattern for docker logs (ISO format prefix)
DOCKER_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")

# Postfix syslog-style timestamp: "Mon DD HH:MM:SS"
SYSLOG_TS_RE = re.compile(r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")


def parse_timestamp(line: str) -> datetime | None:
    # Try Docker timestamp first
    m = DOCKER_TS_RE.match(line)
    if m:
        try:
            return datetime.fromisoformat(m.group(1))
        except ValueError:
            pass

    # Try syslog timestamp
    m = SYSLOG_TS_RE.match(line)
    if m:
        try:
            ts = datetime.strptime(m.group(1), "%b %d %H:%M:%S")
            return ts.replace(year=datetime.now().year)
        except ValueError:
            pass

    return None


def parse_log_line(line: str) -> ParsedMailEvent | None:
    ts = parse_timestamp(line) or datetime.now()

    # Check for reject
    m = REJECT_RE.search(line)
    if m:
        return ParsedMailEvent(
            timestamp=ts,
            sender=m.group("sender"),
            recipient=m.group("recipient"),
            status="rejected",
            client_ip=m.group("client_ip"),
            message=line.strip(),
        )

    # Check for status line (sent/deferred/bounced)
    m = STATUS_RE.search(line)
    if m:
        status = m.group("status")
        if status not in ("sent", "deferred", "bounced"):
            return None
        return ParsedMailEvent(
            timestamp=ts,
            queue_id=m.group("queue_id"),
            recipient=m.group("recipient"),
            status=status,
            relay=m.group("relay"),
            delay=float(m.group("delay")) if m.group("delay") else None,
            dsn=m.group("dsn"),
            message=m.group("message"),
        )

    return None


# Store from= information keyed by queue_id for later enrichment
_from_cache: dict[str, dict] = {}

# Store client= information keyed by queue_id for later enrichment
_client_cache: dict[str, dict] = {}


def _trim_cache(cache: dict, max_size: int = 10000):
    if len(cache) > max_size:
        oldest = list(cache.keys())[:max_size // 2]
        for k in oldest:
            del cache[k]


def parse_and_enrich(line: str) -> ParsedMailEvent | None:
    # Capture from= lines for enrichment
    m = FROM_RE.search(line)
    if m:
        qid = m.group("queue_id")
        _from_cache[qid] = {
            "sender": m.group("sender"),
            "size": int(m.group("size")) if m.group("size") else None,
        }
        _trim_cache(_from_cache)

    # Capture client= lines for enrichment (IP + optional SASL username)
    m = CLIENT_RE.search(line)
    if m:
        qid = m.group("queue_id")
        _client_cache[qid] = {
            "client_ip": m.group("client_ip"),
            "sasl_username": m.group("sasl_username"),
        }
        _trim_cache(_client_cache)

    event = parse_log_line(line)
    if event and event.queue_id:
        # Enrich from from= cache
        if event.queue_id in _from_cache:
            cached = _from_cache[event.queue_id]
            if not event.sender:
                event.sender = cached.get("sender")
            if not event.size:
                event.size = cached.get("size")

        # Enrich from client= cache
        if event.queue_id in _client_cache:
            cached = _client_cache[event.queue_id]
            if not event.client_ip:
                event.client_ip = cached.get("client_ip")
            if not event.sasl_username:
                event.sasl_username = cached.get("sasl_username")

    return event
