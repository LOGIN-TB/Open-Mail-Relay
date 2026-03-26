"""SPF record checker for customer mail domains.

Checks whether a customer's mail domain has an SPF record that includes
the relay server's domain. Used when generating SMTP config PDFs.
"""
import logging

import dns.resolver

logger = logging.getLogger(__name__)


def _resolve_txt(domain: str) -> list[str]:
    """Resolve TXT records for a domain."""
    try:
        answers = dns.resolver.resolve(domain, "TXT", lifetime=5)
        results = []
        for rdata in answers:
            txt = "".join(s.decode() if isinstance(s, bytes) else s for s in rdata.strings)
            results.append(txt)
        return results
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return []
    except Exception as e:
        logger.warning(f"DNS TXT lookup failed for {domain}: {e}")
        return []


def _extract_domain(hostname: str) -> str:
    """Extract registerable domain from hostname (e.g. relay2.spamgo.de -> spamgo.de)."""
    parts = hostname.split(".")
    if len(parts) > 2:
        return ".".join(parts[1:])
    return hostname


def check_customer_spf(mail_domain: str, relay_domain: str) -> dict:
    """Check SPF record for a customer domain and suggest updates.

    Returns dict with:
        mail_domain: The customer's mail domain
        relay_domain: The relay server's domain
        status: "ok" | "needs_update" | "missing"
        current_record: Existing SPF record or None
        suggested_record: Suggested SPF record
    """
    txt_records = _resolve_txt(mail_domain)
    spf_records = [r for r in txt_records if r.startswith("v=spf1")]

    include_value = f"include:spf.{relay_domain}"

    if not spf_records:
        return {
            "mail_domain": mail_domain,
            "relay_domain": relay_domain,
            "status": "missing",
            "current_record": None,
            "suggested_record": f"v=spf1 {include_value} ~all",
        }

    current = spf_records[0]

    # Check if relay SPF subdomain is already included
    if f"spf.{relay_domain}" in current:
        return {
            "mail_domain": mail_domain,
            "relay_domain": relay_domain,
            "status": "ok",
            "current_record": current,
            "suggested_record": current,
        }

    # Need to insert include before the all mechanism
    # Find ~all, -all, +all, or ?all at the end
    suggested = current
    for qualifier in ("~all", "-all", "+all", "?all"):
        if qualifier in suggested:
            suggested = suggested.replace(qualifier, f"{include_value} {qualifier}")
            break
    else:
        # No all mechanism found, append include
        suggested = f"{suggested} {include_value}"

    return {
        "mail_domain": mail_domain,
        "relay_domain": relay_domain,
        "status": "needs_update",
        "current_record": current,
        "suggested_record": suggested,
    }
