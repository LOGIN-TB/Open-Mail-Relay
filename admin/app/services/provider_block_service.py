"""Provider-Block-Monitoring.

Grosse Mailbox-Provider (Microsoft/Outlook, Google, Yahoo, T-Online, …)
sperren ausgehende Sende-IPs *intern* — diese Sperren sind ueber oeffentliche
DNSBLs (siehe rbl_service) NICHT sichtbar. Das einzige Signal ist die
Bounce-/Deferred-Nachricht (NDR), z. B.:

    host hotmail-com.olc.protection.outlook.com[52.101.41.23] said:
    550 5.7.1 Unfortunately, messages from [49.12.162.229] weren't sent.
    ... part of their network is on our block list (S3140 ...)

Dieser Service wertet die ohnehin in `mail_events` gespeicherten Bounces aus,
aggregiert aktive Sperren je (Provider, gesperrte IP) in `provider_blocks`,
alarmiert per E-Mail bei neuen Sperren und liefert dem UI Delisting-Anleitungen.

Anders als rbl_service wird hier NICHT aktiv abgefragt (Microsoft & Co. bieten
keine Status-API) — die Erkennung ist rein passiv.
"""

import logging
import re
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.models import MailEvent, ProviderBlock, SystemSetting
from app.services.mx_detection import extract_relay_host
from app.services.rbl_service import get_server_info

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider catalogue: classification (by remote MX host) + delisting guidance
# ---------------------------------------------------------------------------
# Each provider matches by the suffix of the rejecting relay host. `signatures`
# are provider-specific regex hints that strongly indicate a *block* (not an
# ordinary recipient bounce). Detection also uses the generic keywords below.
#
# A provider may carry "variants": an ORDERED list of block sub-types with
# their own delisting guidance (some providers run several independent block
# systems — e.g. Microsoft EOP vs. Outlook.com consumer — whose delisting
# portals do not cover each other). Variants are classified at READ time from
# the stored block_code/relay_host/sample_response, first match wins. `match`
# has OR semantics over its keys (host/code/text regexes, case-insensitive);
# empty inputs never match, so incomplete rows fall back to the provider
# default delisting.
BLOCK_PROVIDERS: list[dict] = [
    {
        "key": "microsoft",
        "label": "Microsoft / Outlook / Office 365",
        "relay_suffixes": (".protection.outlook.com", ".outlook.com", ".hotmail.com"),
        "signatures": (
            r"\bS\d{3,4}\b",            # S3140, S3150, …
            r"on our block list",
            r"weren['’]?t sent",
            r"5\.7\.6\d\d",             # 5.7.6xx access-denied/banned-IP range
            r"banned sending IP",
            r"blocked using Spamhaus",
        ),
        "code_re": r"\b(S\d{3,4})\b",
        "variants": [
            {
                # Must come first: Spamhaus-driven rejections also match the
                # consumer/EOP host criteria, but neither Microsoft portal
                # helps until the Spamhaus listing is gone.
                "key": "microsoft-spamhaus",
                "label": "Microsoft (Sperre wegen Spamhaus-Listing)",
                "match": {"text": r"blocked using Spamhaus"},
                "note": (
                    "Microsoft blockiert die IP {ip} aufgrund eines Spamhaus-Listings. "
                    "Zuerst das Spamhaus-Delisting durchfuehren — Delisting-Antraege direkt "
                    "bei Microsoft sind erst nach Aufhebung des Spamhaus-Eintrags erfolgreich."
                ),
                "delisting": {
                    "portal": "https://check.spamhaus.org/",
                    "docs": "https://learn.microsoft.com/en-us/exchange/troubleshoot/email-delivery/fix-error-code-5-7-1-through-5-7-999-in-exchange-online",
                    "steps": [
                        "Die IP {ip} unter check.spamhaus.org pruefen (Portal-Link) und das dortige Delisting-Verfahren durchlaufen.",
                        "Ursache des Listings beheben (kompromittierte Konten, offene Relays, Spam-Versand); rDNS/PTR, SPF, DKIM und DMARC fuer {ip} pruefen (siehe DNS-Pruefung).",
                        "Nach Aufhebung des Spamhaus-Eintrags 24-48 Stunden warten — Microsoft uebernimmt die Aenderung in der Regel automatisch.",
                        "Besteht die Sperre danach weiter: bei Microsoft 365/EOP ueber sender.office.com delisten, bei Outlook.com/Hotmail das Microsoft-Support-Formular nutzen.",
                    ],
                },
            },
            {
                "key": "microsoft-consumer",
                "label": "Outlook.com / Hotmail / Live (Consumer-Sperre)",
                "match": {
                    "host": r"\.olc\.protection\.outlook\.com$|(^|\.)hotmail\.com$",
                    "code": r"^S\d{3,4}$",
                    "text": r"weren['’]?t sent|on our block list \(?S\d",
                },
                "note": (
                    "Achtung: Das Office-365-Portal sender.office.com hilft bei dieser Sperre NICHT — "
                    "es meldet 'Die IP-Adresse wird zurzeit nicht blockiert', da es nur Microsoft-365/EOP-Sperren "
                    "abdeckt. Consumer-Sperren (Outlook.com/Hotmail/Live) werden ausschliesslich ueber das "
                    "Microsoft-Support-Formular (Portal-Link) aufgehoben."
                ),
                "delisting": {
                    "portal": "https://support.microsoft.com/de-de/getsupport?oaspworkflow=start_1.0.0.0&wfname=capsub&productkey=edfsmsbl3&locale=de-de",
                    "docs": "https://sendersupport.olc.protection.outlook.com/pm/",
                    "steps": [
                        "Sicherstellen, dass die IP {ip} korrektes rDNS/PTR sowie gueltige SPF-, DKIM- und DMARC-Records hat (siehe DNS-Pruefung).",
                        "Das Microsoft-Support-Formular fuer gesperrte IPs oeffnen (Portal-Link) und ausfuellen — gesperrte IP {ip}, Fehlercode (z. B. S3140) und die vollstaendige Bounce-Meldung angeben ('Angaben kopieren' verwenden).",
                        "Zusaetzlich SNDS (Smart Network Data Services) und JMRP (Junk Mail Reporting Program) unter sendersupport.olc.protection.outlook.com registrieren, um die IP-Reputation zu ueberwachen.",
                        "Antwort von Microsoft abwarten (i. d. R. 1-3 Werktage); Sendevolumen an Outlook.com/Hotmail bis dahin reduziert halten.",
                    ],
                },
            },
            {
                "key": "microsoft-eop",
                "label": "Microsoft 365 / Exchange Online (EOP-Sperre)",
                "match": {
                    "host": r"\.mail\.protection\.outlook\.com$",
                    "code": r"^5\.7\.6\d\d$",
                    "text": r"\b5\.7\.6\d\d\b|banned sending IP",
                },
                "note": "Diese Sperre betrifft Microsoft 365 / Exchange Online (EOP). Das Delisting erfolgt ueber sender.office.com.",
                "delisting": {
                    "portal": "https://sender.office.com/",
                    "docs": "https://learn.microsoft.com/en-us/exchange/troubleshoot/email-delivery/fix-error-code-5-7-1-through-5-7-999-in-exchange-online",
                    "steps": [
                        "Sicherstellen, dass die IP {ip} korrektes rDNS/PTR sowie gueltige SPF-, DKIM- und DMARC-Records hat (siehe DNS-Pruefung).",
                        "Das EOP-Delisting-Portal sender.office.com oeffnen (Portal-Link), die IP {ip} eintragen und den Bestaetigungslink aus der Microsoft-E-Mail anklicken.",
                        "Aufhebung abwarten (i. d. R. innerhalb von 24 Stunden); Sendevolumen bis dahin reduziert halten.",
                    ],
                },
            },
        ],
        # Default when no variant matched (e.g. empty sample/code/host on old
        # rows): explain BOTH Microsoft block systems and how to tell them apart.
        "delisting": {
            "portal": "https://sender.office.com/",
            "docs": "https://learn.microsoft.com/en-us/exchange/troubleshoot/email-delivery/fix-error-code-5-7-1-through-5-7-999-in-exchange-online",
            "steps": [
                "Sicherstellen, dass die IP {ip} korrektes rDNS/PTR sowie gueltige SPF-, DKIM- und DMARC-Records hat (siehe DNS-Pruefung).",
                "Sperr-Typ bestimmen: Remote-Host '*.olc.protection.outlook.com' bzw. Hotmail oder Fehlercodes wie S3140 = Consumer-Sperre (Outlook.com/Hotmail); '*.mail.protection.outlook.com' oder Fehler 5.7.6xx ('banned sending IP') = Microsoft 365/EOP.",
                "Bei Microsoft 365/EOP: Delisting unter sender.office.com (Portal-Link) beantragen.",
                "Bei Outlook.com/Hotmail: das Microsoft-Support-Formular nutzen (https://support.microsoft.com/de-de/getsupport?oaspworkflow=start_1.0.0.0&wfname=capsub&productkey=edfsmsbl3&locale=de-de) — sender.office.com meldet bei Consumer-Sperren faelschlich 'IP wird nicht blockiert'.",
                "Antwort von Microsoft abwarten (i. d. R. 1-3 Werktage); Sendevolumen bis dahin reduziert halten.",
            ],
        },
    },
    {
        "key": "google",
        "label": "Google / Gmail / Google Workspace",
        "relay_suffixes": (".google.com", ".googlemail.com", "gmail-smtp-in"),
        "signatures": (
            r"our system has detected",
            r"this message has been blocked",
            r"unsolicited mail",
            r"\b550[ -]5\.7\.1\b",
            r"not authorized to send",
        ),
        "code_re": None,
        "delisting": {
            "portal": "https://support.google.com/mail/contact/bulk_send_new",
            "docs": "https://support.google.com/mail/answer/81126",
            "steps": [
                "rDNS/PTR, SPF, DKIM und DMARC fuer die IP {ip} pruefen (siehe DNS-Pruefung).",
                "IP/Domain in den Google Postmaster Tools (postmaster.google.com) registrieren und Reputation pruefen.",
                "Beschwerderate senken; danach das Bulk-Sender-Kontaktformular (Portal-Link) zur Pruefung einreichen.",
            ],
        },
    },
    {
        "key": "yahoo",
        "label": "Yahoo / AOL",
        "relay_suffixes": (".yahoodns.net", ".yahoo.com", ".aol.com"),
        "signatures": (
            r"\[TSS\d+\]",
            r"temporarily deferred",
            r"messages from .* deferred",
            r"not accepted for policy reasons",
            r"\b554 5\.7\.9\b",
        ),
        "code_re": r"\[(TSS\d+)\]",
        "delisting": {
            "portal": "https://senders.yahooinc.com/contact-us/",
            "docs": "https://senders.yahooinc.com/",
            "steps": [
                "rDNS/PTR, SPF, DKIM und DMARC fuer die IP {ip} pruefen (siehe DNS-Pruefung).",
                "Am Yahoo Complaint Feedback Loop (CFL) teilnehmen und Reputation pruefen.",
                "Ueber das Yahoo Sender Hub Kontaktformular (Portal-Link) ein Delisting/Whitelisting fuer {ip} beantragen.",
            ],
        },
    },
    {
        "key": "t-online",
        "label": "Deutsche Telekom / T-Online",
        "relay_suffixes": (".t-online.de", ".telekom.de"),
        # Block-specific only — avoid broad 'rejected'/'554' which also appear in
        # ordinary recipient bounces (e.g. 'Recipient address rejected').
        "signatures": (
            r"blocked",
            r"gesperrt",
            r"not in (?:our )?whitelist",
            r"not whitelisted",
            r"bad reputation",
            r"poor reputation",
        ),
        "code_re": None,
        "delisting": {
            "portal": "https://postmaster.t-online.de/",
            "docs": "https://postmaster.t-online.de/",
            "steps": [
                "T-Online akzeptiert nur Mails von bekannten Sende-IPs. rDNS/PTR, SPF, DKIM und DMARC fuer {ip} sicherstellen.",
                "Whitelisting per E-Mail an tobr@rx.t-online.de beantragen — mit IP {ip}, Hostname {host}, Abuse-Kontakt und kurzer Beschreibung des Mailverkehrs.",
                "Auf Bestaetigung der Telekom warten; Postmaster-Seite (Portal-Link) fuer Details beachten.",
            ],
        },
    },
    {
        "key": "united-internet",
        "label": "United Internet (GMX / web.de / 1&1 / mail.com)",
        "relay_suffixes": (".gmx.net", ".web.de", ".kundenserver.de", ".1und1.de", ".mail.com"),
        # Block-specific only (see t-online note above).
        "signatures": (
            r"blocked",
            r"gesperrt",
            r"bad reputation",
            r"poor reputation",
            r"not in (?:our )?whitelist",
        ),
        "code_re": None,
        "delisting": {
            "portal": "https://postmaster.web.de/",
            "docs": "https://postmaster.gmx.net/",
            "steps": [
                "rDNS/PTR, SPF, DKIM und DMARC fuer die IP {ip} pruefen (siehe DNS-Pruefung).",
                "Beim United-Internet-Postmaster (postmaster.web.de bzw. postmaster.gmx.net) registrieren.",
                "Ueber das Postmaster-Kontaktformular (Portal-Link) ein Delisting fuer {ip} (Hostname {host}) beantragen.",
            ],
        },
    },
]

# Provider lookup by key
_PROVIDER_BY_KEY = {p["key"]: p for p in BLOCK_PROVIDERS}

GENERIC_PROVIDER = {
    "key": "other",
    "label": "Anderer Provider",
    "delisting": {
        "portal": "",
        "docs": "",
        "steps": [
            "rDNS/PTR, SPF, DKIM und DMARC fuer die IP {ip} pruefen (siehe DNS-Pruefung).",
            "Postmaster-/Delisting-Seite des Empfaenger-Providers ({host}) suchen.",
            "Delisting fuer die IP {ip} beantragen und Abuse-/Postmaster-Kontakt angeben.",
            "Sendevolumen voruebergehend reduzieren, bis die Sperre aufgehoben ist.",
        ],
    },
}

# Recipient-level rejections that contain block-sounding words but are NOT
# sending-IP blocks. Microsoft Exchange Online answers for non-existent
# mailboxes (Directory-Based Edge Blocking) with
#   '550 5.4.1 Recipient address rejected: Access denied ... aka.ms/EXOSmtpErrors'
# — the recipient does not exist; no delisting portal helps. The same phrase is
# produced by Postfix check_recipient_access rejects on other MTAs. Checked
# BEFORE the block keywords below ('access denied' would otherwise match).
_RECIPIENT_REJECT_RE = re.compile(
    r"recipient address rejected:\s*access denied",
    re.IGNORECASE,
)

# Generic block keywords — strong indicators that an NDR is a *block*, not an
# ordinary recipient error (user unknown, mailbox full, …). Kept deliberately
# block-specific to avoid false positives.
_BLOCK_KEYWORDS_RE = re.compile(
    r"block\s*list|blocklist|blacklist|\bblocked\b|\bbanned\b|"
    r"poor reputation|bad reputation|low reputation|sender reputation|"
    r"listed (?:on|in|by)|on our block|not authoriz|access denied|"
    r"spamhaus|barracuda|uceprotect|abusix|gesperrt|"
    r"part of their network|temporarily deferred",
    re.IGNORECASE,
)

# IPv4 in brackets, and the "messages from [ip]" form (our outbound IP)
_BRACKET_IP_RE = re.compile(r"\[(\d{1,3}(?:\.\d{1,3}){3})\]")
_FROM_IP_RE = re.compile(r"\bfrom\s+\[?(\d{1,3}(?:\.\d{1,3}){3})\]?", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Settings (SystemSetting key/value, mirrors rbl_service)
# ---------------------------------------------------------------------------
ALLOWED_KEYS = {
    "provider_block_enabled",
    "provider_block_scan_interval_hours",
    "provider_block_lookback_hours",
    "provider_block_mail_to",
    "provider_block_mail_from",
    "provider_block_alert_on_change_only",
    "provider_block_last_scan_time",
}

DEFAULTS: dict[str, str] = {
    "provider_block_enabled": "false",
    "provider_block_scan_interval_hours": "6",
    "provider_block_lookback_hours": "24",
    "provider_block_mail_to": "",
    "provider_block_mail_from": "",
    "provider_block_alert_on_change_only": "true",
    "provider_block_last_scan_time": "",
}

_COMPUTED_KEYS = {"provider_block_last_scan_time"}


def get_settings(db: Session) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, default in DEFAULTS.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        result[key] = row.value if row else default
    return result


def update_settings(db: Session, data: dict[str, str]) -> dict[str, str]:
    for key, value in data.items():
        if key not in ALLOWED_KEYS or value is None or key in _COMPUTED_KEYS:
            continue
        _set_setting(db, key, value)
    db.commit()
    return get_settings(db)


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _relay_ip(relay: str | None) -> str | None:
    """Extract the provider's IP from a Postfix relay field 'host[ip]:port'."""
    if not relay:
        return None
    m = _BRACKET_IP_RE.search(relay)
    return m.group(1) if m else None


def classify_provider(relay_host: str | None) -> dict | None:
    """Return the provider catalogue entry for a rejecting relay host, or None."""
    if not relay_host:
        return None
    host = relay_host.lower().rstrip(".")
    for prov in BLOCK_PROVIDERS:
        for suffix in prov["relay_suffixes"]:
            s = suffix.lstrip(".")
            if host == s or host.endswith(suffix) or s in host:
                return prov
    return None


def _extract_code(text: str, prov: dict | None) -> str:
    """Pull a provider-specific block code (S3140, TSS04, …) from the NDR text."""
    if prov and prov.get("code_re"):
        m = re.search(prov["code_re"], text, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def detect_block(text: str, dsn_code: str | None, relay_host: str | None) -> dict | None:
    """Decide whether an NDR text represents a provider sending-block.

    Returns {provider, label, code} or None. The provider is classified by the
    rejecting relay host; an unknown host still counts as a generic ("other")
    block if the text carries a strong block signal.
    """
    if not text:
        return None

    # Per-recipient rejection (mailbox does not exist) — never an IP block,
    # even though the text contains 'Access denied'.
    if _RECIPIENT_REJECT_RE.search(text):
        return None

    prov = classify_provider(relay_host)

    # 1) provider-specific signature?
    sig_match = False
    if prov:
        for sig in prov["signatures"]:
            if re.search(sig, text, re.IGNORECASE):
                sig_match = True
                break

    # 2) generic block keyword?
    generic_match = bool(_BLOCK_KEYWORDS_RE.search(text))

    if not sig_match and not generic_match:
        return None

    if prov is None:
        # Unknown provider — only flag if a strong generic keyword matched.
        if not generic_match:
            return None
        return {
            "provider": GENERIC_PROVIDER["key"],
            "label": GENERIC_PROVIDER["label"],
            "code": "",
        }

    return {
        "provider": prov["key"],
        "label": prov["label"],
        "code": _extract_code(text, prov),
    }


def extract_blocked_ip(text: str, relay_ip: str | None, fallback: str) -> str:
    """Find the blocked outbound IP in the NDR text (e.g. 'messages from [1.2.3.4]')."""
    if text:
        m = _FROM_IP_RE.search(text)
        if m:
            return m.group(1)
        for ip in _BRACKET_IP_RE.findall(text):
            if ip != relay_ip:
                return ip
    return fallback or ""


def _match_variant(prov: dict, host: str, code: str, sample: str) -> dict | None:
    """First variant (in catalogue order) with ANY matching criterion, else None."""
    for var in prov.get("variants", ()):
        m = var.get("match", {})
        if m.get("host") and host and re.search(m["host"], host, re.IGNORECASE):
            return var
        if m.get("code") and code and re.search(m["code"], code, re.IGNORECASE):
            return var
        if m.get("text") and sample and re.search(m["text"], sample, re.IGNORECASE):
            return var
    return None


def delisting_for(provider: str, ip: str = "", host: str = "", code: str = "", sample: str = "") -> dict:
    """Return the delisting guidance for a provider, with {ip}/{host} filled in.

    If the provider defines variants (block sub-types with their own delisting
    path), the stored block code / relay host / NDR text select the matching
    variant; otherwise the provider default applies.
    """
    prov = _PROVIDER_BY_KEY.get(provider, GENERIC_PROVIDER)
    norm_host = (host or "").lower().rstrip(".")
    var = _match_variant(prov, norm_host, (code or "").strip(), sample or "")
    d = (var or prov)["delisting"]
    fmt = {"ip": ip or "der IP", "host": host or "dem Provider"}
    return {
        "portal": d["portal"],
        "docs": d["docs"],
        "steps": [s.format(**fmt) for s in d["steps"]],
        "variant": var["key"] if var else "",
        "variant_label": var["label"] if var else "",
        "note": var.get("note", "").format(**fmt) if var else "",
    }


# ---------------------------------------------------------------------------
# Scan / aggregation
# ---------------------------------------------------------------------------

def _provider_sent_since(db: Session, provider: str, since: datetime) -> int:
    """Count successful sends to a provider after a timestamp (resolution signal)."""
    prov = _PROVIDER_BY_KEY.get(provider)
    if not prov:
        return 0
    q = (
        db.query(MailEvent.relay)
        .filter(MailEvent.status == "sent")
        .filter(MailEvent.timestamp > since)
        .filter(MailEvent.relay.isnot(None))
    )
    # Coarse SQL prefilter, then exact classify in Python.
    count = 0
    for (relay,) in q.limit(5000):
        host = extract_relay_host(relay)
        if classify_provider(host) is prov:
            count += 1
            if count >= 1:
                break
    return count


def run_scan(db: Session) -> dict:
    """Scan recent bounces for provider blocks, upsert state, alert on new blocks."""
    settings = get_settings(db)
    lookback_hours = max(1, int(settings.get("provider_block_lookback_hours", "24")))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=lookback_hours)
    own_ip = get_server_info().get("ip", "")

    rows = (
        db.query(MailEvent)
        .filter(MailEvent.status.in_(("bounced", "deferred")))
        .filter(MailEvent.timestamp >= cutoff.replace(tzinfo=None))
        .all()
    )

    # Aggregate detected blocks per (provider, blocked_ip)
    detected: dict[tuple[str, str], dict] = {}
    scanned = 0
    matched = 0
    for ev in rows:
        scanned += 1
        text = ev.remote_response or ev.message or ""
        relay_host = extract_relay_host(ev.relay)
        match = detect_block(text, ev.dsn_code, relay_host)
        if not match:
            continue
        blocked_ip = extract_blocked_ip(text, _relay_ip(ev.relay), own_ip)
        if not blocked_ip:
            continue
        matched += 1
        ts = ev.timestamp if ev.timestamp.tzinfo else ev.timestamp.replace(tzinfo=timezone.utc)
        key = (match["provider"], blocked_ip)
        agg = detected.get(key)
        if agg is None:
            agg = {
                "provider": match["provider"],
                "label": match["label"],
                "blocked_ip": blocked_ip,
                "relay_host": relay_host or "",
                "code": match["code"],
                "sample": text[:2000],
                "queue_id": ev.queue_id or "",
                "first": ts,
                "last": ts,
                "count": 0,
            }
            detected[key] = agg
        agg["count"] += 1
        if ts < agg["first"]:
            agg["first"] = ts
        if ts >= agg["last"]:
            agg["last"] = ts
            agg["sample"] = text[:2000]  # keep most-recent sample
            agg["queue_id"] = ev.queue_id or agg["queue_id"]
            agg["relay_host"] = relay_host or agg["relay_host"]
            if match["code"]:
                agg["code"] = match["code"]

    # Upsert detected blocks
    new_blocks: list[ProviderBlock] = []
    for (provider, ip), agg in detected.items():
        row = (
            db.query(ProviderBlock)
            .filter(ProviderBlock.provider == provider, ProviderBlock.blocked_ip == ip)
            .first()
        )
        last_naive = agg["last"].replace(tzinfo=None)
        first_naive = agg["first"].replace(tzinfo=None)
        if row is None:
            row = ProviderBlock(
                provider=provider,
                provider_label=agg["label"],
                blocked_ip=ip,
                relay_host=agg["relay_host"],
                block_code=agg["code"],
                sample_response=agg["sample"],
                sample_queue_id=agg["queue_id"],
                first_seen=first_naive,
                last_seen=last_naive,
                hit_count=agg["count"],
                status="active",
            )
            db.add(row)
            new_blocks.append(row)
        else:
            reactivated = row.status != "active"
            row.provider_label = agg["label"]
            row.relay_host = agg["relay_host"] or row.relay_host
            if agg["code"]:
                row.block_code = agg["code"]
            row.sample_response = agg["sample"]
            row.sample_queue_id = agg["queue_id"] or row.sample_queue_id
            row.hit_count = agg["count"]
            row.last_seen = last_naive
            if row.first_seen is None or first_naive < row.first_seen:
                row.first_seen = first_naive
            if reactivated:
                row.status = "active"
                row.resolved_at = None
                new_blocks.append(row)

    # Flush so newly added/reactivated blocks are visible to the queries below
    # (SessionLocal uses autoflush=False).
    db.flush()

    # Auto-resolution: active blocks no longer seen in the window, with evidence
    # of a successful send to that provider since they were last seen.
    resolved = 0
    active_rows = db.query(ProviderBlock).filter(ProviderBlock.status == "active").all()
    detected_keys = set(detected.keys())
    for row in active_rows:
        if (row.provider, row.blocked_ip) in detected_keys:
            continue
        since = row.last_seen or cutoff.replace(tzinfo=None)
        since = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
        if _provider_sent_since(db, row.provider, since.replace(tzinfo=None)):
            row.status = "resolved"
            row.resolved_at = now.replace(tzinfo=None)
            resolved += 1

    active_count = db.query(ProviderBlock).filter(ProviderBlock.status == "active").count()

    # Alerting
    alert_on_change_only = settings.get("provider_block_alert_on_change_only", "true") == "true"
    should_alert = (len(new_blocks) > 0) if alert_on_change_only else (active_count > 0)
    if should_alert and settings.get("provider_block_mail_to"):
        subject, body = format_alert_email(new_blocks, active_count, resolved)
        send_alert(settings, subject, body)

    scan_time = now.isoformat()
    _set_setting(db, "provider_block_last_scan_time", scan_time)
    db.commit()

    return {
        "scanned": scanned,
        "matched": matched,
        "new_blocks": len(new_blocks),
        "resolved": resolved,
        "active_count": active_count,
        "scan_time": scan_time,
    }


# ---------------------------------------------------------------------------
# Queries for the API
# ---------------------------------------------------------------------------

def list_blocks(db: Session, resolved_within_days: int = 7) -> list[ProviderBlock]:
    """Active blocks plus recently resolved ones, newest first."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=resolved_within_days)).replace(tzinfo=None)
    rows = (
        db.query(ProviderBlock)
        .filter(
            (ProviderBlock.status == "active")
            | (ProviderBlock.resolved_at.isnot(None) & (ProviderBlock.resolved_at >= cutoff))
        )
        .order_by(ProviderBlock.status.asc(), ProviderBlock.last_seen.desc())
        .all()
    )
    return rows


def get_status(db: Session) -> dict:
    settings = get_settings(db)
    enabled = settings.get("provider_block_enabled", "false") == "true"
    last_scan_time = settings.get("provider_block_last_scan_time", "")
    active_count = db.query(ProviderBlock).filter(ProviderBlock.status == "active").count()
    return {
        "enabled": enabled,
        "last_scan_time": last_scan_time,
        "active_count": active_count,
        "all_clear": active_count == 0 and bool(last_scan_time),
    }


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def format_alert_email(new_blocks: list[ProviderBlock], active_count: int, resolved: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if new_blocks:
        if len(new_blocks) == 1:
            b = new_blocks[0]
            subject = f"[PROVIDER-SPERRE] {b.provider_label}: IP {b.blocked_ip} gesperrt"
        else:
            subject = f"[PROVIDER-SPERRE] {len(new_blocks)} neue Provider-Sperren erkannt"
    else:
        subject = f"[PROVIDER-SPERRE] {active_count} aktive Provider-Sperre(n)"

    lines = [
        f"Provider-Block-Monitoring — {now}",
        "=" * 60,
        "",
        f"Neue Sperren: {len(new_blocks)}   Aktiv gesamt: {active_count}   Aufgehoben: {resolved}",
        "",
    ]
    blocks = new_blocks if new_blocks else []
    if blocks:
        lines.append("NEUE SPERREN")
        lines.append("-" * 40)
        for b in blocks:
            d = delisting_for(
                b.provider, b.blocked_ip, b.relay_host or "",
                b.block_code or "", b.sample_response or "",
            )
            lines.append("")
            lines.append(f"  Provider:     {b.provider_label}")
            if d["variant_label"]:
                lines.append(f"  Sperr-Typ:    {d['variant_label']}")
            lines.append(f"  Gesperrte IP: {b.blocked_ip}")
            if b.block_code:
                lines.append(f"  Code:         {b.block_code}")
            if b.relay_host:
                lines.append(f"  Remote-Host:  {b.relay_host}")
            if b.sample_response:
                lines.append(f"  Bounce:       {b.sample_response[:300]}")
            if d["note"]:
                lines.append(f"  Hinweis:      {d['note']}")
            if d["portal"]:
                lines.append(f"  Delisting:    {d['portal']}")
            for step in d["steps"]:
                lines.append(f"     - {step}")

    lines.extend([
        "",
        "-" * 60,
        "Details und Delisting-Anleitungen im Admin-Panel unter 'Provider-Sperren'.",
        f"Zeitpunkt: {now}",
    ])
    return subject, "\n".join(lines)


def send_alert(settings: dict[str, str], subject: str, body: str) -> bool:
    mail_from = settings.get("provider_block_mail_from", "")
    mail_to = settings.get("provider_block_mail_to", "")
    if not mail_from or not mail_to:
        logger.warning("Provider-block alert: no mail_from or mail_to configured")
        return False

    msg = MIMEMultipart()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("open-mail-relay", 25, timeout=30)
        server.sendmail(mail_from, [mail_to], msg.as_string())
        server.quit()
        logger.info("Provider-block alert sent: %s", subject)
        return True
    except Exception as e:
        logger.error("Provider-block alert send failed: %s", e)
        return False


def send_test_email(db: Session) -> bool:
    settings = get_settings(db)
    mail_from = settings.get("provider_block_mail_from", "")
    mail_to = settings.get("provider_block_mail_to", "")
    if not mail_from or not mail_to:
        return False
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "[Provider-Sperren Test] Test-Mail vom Block-Monitoring"
    body = (
        "Dies ist eine Test-Mail vom Provider-Block-Monitoring.\n\n"
        f"Absender: {mail_from}\n"
        f"Empfaenger: {mail_to}\n"
        f"Zeitpunkt: {now}\n\n"
        "Wenn Sie diese Mail erhalten, funktioniert der E-Mail-Versand korrekt."
    )
    return send_alert(settings, subject, body)
