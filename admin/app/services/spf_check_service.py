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


def _resolve_cname(domain: str) -> str | None:
    """Resolve a CNAME record for a domain (lower-cased, trailing dot stripped)."""
    try:
        answers = dns.resolver.resolve(domain, "CNAME", lifetime=5)
        for rdata in answers:
            return str(rdata.target).rstrip(".").lower()
        return None
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return None
    except Exception as e:
        logger.warning(f"DNS CNAME lookup failed for {domain}: {e}")
        return None


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


def check_customer_dkim_cname(mail_domain: str, hostname: str) -> dict:
    """Check the DKIM CNAME for a customer domain.

    The relay publishes its DKIM key under <selector>._domainkey.<relay_domain>
    and customers add a CNAME at <selector>._domainkey.<their_domain> pointing
    to it. The selector is the first label of the relay hostname (e.g. "relay2").

    Returns dict with:
        mail_domain: customer's mail domain
        relay_domain: relay server's registerable domain
        selector: DKIM selector (first hostname label)
        lookup_name: full DNS name to query at the customer side
        expected_target: the CNAME target the customer must use
        status: "ok" | "needs_update" | "missing"
        current_record: current CNAME target (or first TXT) or None
        suggested_record: human-readable record line for the PDF
    """
    selector = hostname.split(".")[0]
    relay_domain = _extract_domain(hostname)
    lookup_name = f"{selector}._domainkey.{mail_domain}"
    expected_target = f"{selector}._domainkey.{relay_domain}"
    suggested_record = f"{lookup_name} CNAME {expected_target}"

    current_cname = _resolve_cname(lookup_name)
    if current_cname and current_cname == expected_target.lower():
        status = "ok"
        current_record = current_cname
    elif current_cname:
        status = "needs_update"
        current_record = current_cname
    else:
        # Some customers may have a manual TXT-based DKIM key under the same name.
        txt = _resolve_txt(lookup_name)
        # Special case: when the customer domain *is* the relay domain, the lookup
        # name resolves to the relay's own DKIM TXT key. A CNAME would self-loop —
        # DKIM is already published directly. Accept any DKIM-looking TXT as ok.
        is_self_domain = mail_domain.lower() == relay_domain.lower()
        dkim_txt = next((t for t in txt if "v=DKIM1" in t or "p=" in t), None)
        if is_self_domain and dkim_txt:
            status = "ok"
            current_record = dkim_txt
        elif txt:
            status = "needs_update"
            current_record = txt[0]
        else:
            status = "missing"
            current_record = None

    return {
        "mail_domain": mail_domain,
        "relay_domain": relay_domain,
        "selector": selector,
        "lookup_name": lookup_name,
        "expected_target": expected_target,
        "status": status,
        "current_record": current_record,
        "suggested_record": suggested_record,
    }
