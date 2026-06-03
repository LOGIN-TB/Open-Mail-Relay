"""MX-based provider detection for automatic transport routing.

Postfix transport maps route by *recipient domain*, but large mailbox
providers (Microsoft 365, Google Workspace, Yahoo) enforce throttling per
*shared backend* — e.g. Microsoft counts concurrent connections "per resource
forest" across all tenants on the same `*.mail.protection.outlook.com` pod.

A relay therefore needs to route every domain that is *hosted* on such a
provider through the matching throttled transport — not just the provider's
own consumer domains (outlook.com, gmail.com, …). This module discovers the
recipient domains the relay actually serves (from `mail_events`), determines
their provider by the MX record, and hands the result to the transport
generator so those domains are routed to the right `*_throttled` transport
automatically.

Lookups are cached on disk (positive + negative TTL) so regenerating the
transport map does not hammer DNS.
"""
import json
import logging
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import MailEvent, TransportRule

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------
# A provider is identified by the suffix of its MX hostnames. Order matters
# only for readability; suffixes are disjoint in practice.
PROVIDER_MX_SUFFIXES: dict[str, tuple[str, ...]] = {
    "microsoft": (".mail.protection.outlook.com", ".olc.protection.outlook.com"),
    "google": (".google.com", ".googlemail.com"),
    "yahoo": (".yahoodns.net",),
}

# Consumer "seed" domains per provider. If an admin has a manual TransportRule
# for one of these, we reuse *that* rule's transport name for auto-detected
# domains of the same provider — so auto-routing honors the admin's naming and
# throttle settings instead of guessing.
PROVIDER_SEED_DOMAINS: dict[str, frozenset[str]] = {
    "microsoft": frozenset({
        "outlook.com", "hotmail.com", "live.com", "msn.com",
        "outlook.de", "hotmail.de", "live.de", "office365.com",
    }),
    "google": frozenset({"gmail.com", "googlemail.com"}),
    "yahoo": frozenset({"yahoo.com", "yahoo.de", "ymail.com", "rocketmail.com"}),
}

# Fallback transport name per provider, used only when no seed-domain rule
# exists but a transport with this exact name is defined elsewhere.
PROVIDER_DEFAULT_TRANSPORT: dict[str, str] = {
    "microsoft": "outlook_throttled",
    "google": "gmail_throttled",
    "yahoo": "yahoo_throttled",
}

CACHE_FILE = Path("/etc/postfix-config/mx_cache.json")
CACHE_TTL_POSITIVE = 14 * 24 * 3600  # 14 days for a resolved provider
CACHE_TTL_NEGATIVE = 2 * 24 * 3600   # 2 days for "no known provider" / lookup fail
DEFAULT_LOOKBACK_DAYS = 30
MAX_LOOKUPS_PER_RUN = 750  # safety bound; logged if exceeded
DNS_TIMEOUT = 4.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_domain(address: str | None) -> str | None:
    """Return the lowercased domain part of an email address, or None."""
    if not address or "@" not in address:
        return None
    domain = address.rsplit("@", 1)[1].strip().lower().rstrip(".")
    return domain or None


def extract_relay_host(relay: str | None) -> str | None:
    """Extract the hostname from a Postfix relay field like 'host[ip]:25'."""
    if not relay:
        return None
    host = relay.split("[", 1)[0].strip().lower().rstrip(".")
    if not host or host in ("none", "local", "127.0.0.1"):
        return None
    return host


def classify_mx_hosts(hosts: list[str]) -> str | None:
    """Return the provider key for a set of MX hostnames, or None."""
    for host in hosts:
        host = host.lower().rstrip(".")
        for provider, suffixes in PROVIDER_MX_SUFFIXES.items():
            if any(host == s.lstrip(".") or host.endswith(s) for s in suffixes):
                return provider
    return None


def _lookup_mx(domain: str) -> list[str] | None:
    """Resolve MX records for a domain. Returns hostnames, [] (no MX), or None (failure)."""
    try:
        import dns.resolver  # lazy import; dnspython is a declared dependency
    except ImportError:
        logger.warning("dnspython not available — MX detection falls back to observed relays")
        return None

    resolver = dns.resolver.Resolver()
    resolver.timeout = DNS_TIMEOUT
    resolver.lifetime = DNS_TIMEOUT
    try:
        answers = resolver.resolve(domain, "MX")
        return sorted(str(r.exchange).rstrip(".").lower() for r in answers)
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return []  # domain exists but has no usable MX → not our provider
    except Exception as e:  # NoNameservers, Timeout, LifetimeTimeout, …
        logger.debug(f"MX lookup failed for {domain}: {e}")
        return None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text())
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache))
    except OSError as e:
        logger.warning(f"Could not persist MX cache: {e}")


def _cache_fresh(entry: dict, now: float) -> bool:
    ttl = CACHE_TTL_POSITIVE if entry.get("provider") else CACHE_TTL_NEGATIVE
    return (now - entry.get("ts", 0)) < ttl


# ---------------------------------------------------------------------------
# Provider → transport name mapping (derived from admin's existing rules)
# ---------------------------------------------------------------------------

def provider_transport_map(rules: list[TransportRule]) -> dict[str, str]:
    """Map each provider to the transport name it should use.

    Prefers the transport configured for one of the provider's seed domains;
    falls back to the provider's default transport name only if a rule with
    that exact transport name already exists (so we never route to an
    undefined transport).
    """
    active = [r for r in rules if r.is_active]
    by_pattern = {r.domain_pattern: r.transport_name for r in active}
    defined_transports = {r.transport_name for r in active}

    mapping: dict[str, str] = {}
    for provider, seeds in PROVIDER_SEED_DOMAINS.items():
        # 1) seed-domain rule wins
        for seed in seeds:
            if seed in by_pattern:
                mapping[provider] = by_pattern[seed]
                break
        # 2) otherwise default transport name, if it is actually defined
        if provider not in mapping:
            default = PROVIDER_DEFAULT_TRANSPORT.get(provider)
            if default and default in defined_transports:
                mapping[provider] = default
    return mapping


# ---------------------------------------------------------------------------
# Domain discovery + classification
# ---------------------------------------------------------------------------

def discover_recipient_domains(db: Session, lookback_days: int) -> dict[str, str | None]:
    """Distinct recipient domains seen in mail_events, with a representative
    observed relay host per domain (used as a DNS-free fallback signal)."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    # Dedupe per recipient at the DB level (one representative relay each) so we
    # don't transfer every individual event row.
    rows = (
        db.query(MailEvent.recipient, func.max(MailEvent.relay))
        .filter(MailEvent.timestamp >= cutoff)
        .filter(MailEvent.recipient.isnot(None))
        .group_by(MailEvent.recipient)
        .all()
    )

    domains: dict[str, str | None] = {}
    for recipient, relay in rows:
        domain = extract_domain(recipient)
        if not domain:
            continue
        if domains.get(domain):
            continue  # already have a relay host for this domain
        domains[domain] = extract_relay_host(relay)
    return domains


def detect_provider_domains(
    db: Session,
    explicit_patterns: set[str] | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[dict]:
    """Detect recipient domains hosted on a throttled provider.

    Returns a list of {domain, provider, transport_name, source} dicts for
    domains that (a) are not already covered by an explicit transport rule and
    (b) map to a provider whose transport is defined.
    """
    explicit_patterns = explicit_patterns or set()
    rules = db.query(TransportRule).all()
    prov_transport = provider_transport_map(rules)
    if not prov_transport:
        return []  # no throttled provider transports defined → nothing to route

    candidates = discover_recipient_domains(db, lookback_days)
    cache = _load_cache()
    now = time.time()
    lookups = 0
    cache_dirty = False
    results: list[dict] = []

    for domain in sorted(candidates):
        if domain in explicit_patterns or domain == "*":
            continue

        observed = candidates[domain]
        entry = cache.get(domain)
        if entry and _cache_fresh(entry, now):
            provider, source = entry.get("provider"), "cache"
        else:
            provider, source = None, None
            if lookups < MAX_LOOKUPS_PER_RUN:
                hosts = _lookup_mx(domain)
                lookups += 1
                if hosts:
                    provider, source = classify_mx_hosts(hosts), "mx"
                elif hosts is None and observed:
                    # DNS failed → classify by the MX Postfix actually used
                    provider, source = classify_mx_hosts([observed]), "relay"
                cache[domain] = {"provider": provider, "ts": now}
                cache_dirty = True
            elif observed:
                # over the per-run lookup budget: use observed relay only
                provider, source = classify_mx_hosts([observed]), "relay"

        if provider and provider in prov_transport:
            results.append({
                "domain": domain,
                "provider": provider,
                "transport_name": prov_transport[provider],
                "source": source,
            })

    if lookups >= MAX_LOOKUPS_PER_RUN:
        logger.warning(
            f"MX detection hit the per-run lookup cap ({MAX_LOOKUPS_PER_RUN}); "
            f"remaining domains classified by observed relay only this run"
        )
    if cache_dirty:
        _save_cache(cache)

    return results


def is_autodetect_enabled(db: Session) -> bool:
    """Read the mx_autodetect toggle from ThrottleConfig (default: enabled)."""
    from app.services.throttle_service import get_config

    return get_config(db, "mx_autodetect", "true").lower() == "true"
