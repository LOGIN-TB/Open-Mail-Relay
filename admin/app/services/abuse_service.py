"""Read / write abuse-page settings from the system_settings table."""

import html
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import SystemSetting
from app.services.postfix_service import read_main_cf
from app.services.abuse_template import ABUSE_HTML_TEMPLATE

logger = logging.getLogger(__name__)

ALLOWED_KEYS = {
    "abuse_email",
    "postmaster_email",
    "abuse_responsible",
    "abuse_phone",
    "abuse_imprint_url",
    "abuse_data_retention",
    "abuse_spam_filtering",
    "abuse_rfc2142",
}


def _hostname_and_domain() -> tuple[str, str]:
    cf = read_main_cf()
    hostname = cf.get("myhostname", "localhost")
    domain = cf.get("mydomain", hostname)
    return hostname, domain


def _defaults(domain: str) -> dict[str, str]:
    return {
        "abuse_email": f"abuse@{domain}",
        "postmaster_email": f"postmaster@{domain}",
        "abuse_responsible": "",
        "abuse_phone": "",
        "abuse_imprint_url": "",
        "abuse_data_retention": "Deutschland, DSGVO-konform. Logs werden 30 Tage gespeichert.",
        "abuse_spam_filtering": "SPF-, DKIM- und DMARC-Pruefung aller ein- und ausgehenden Mails",
        "abuse_rfc2142": "abuse@ und postmaster@ sind gemaess RFC 2142 konfiguriert und aktiv",
    }


def get_abuse_settings(db: Session) -> dict[str, str]:
    hostname, domain = _hostname_and_domain()
    defaults = _defaults(domain)

    result: dict[str, str] = {}
    for key, default in defaults.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        result[key] = row.value if row else default

    result["hostname"] = hostname
    result["domain"] = domain
    return result


def update_abuse_settings(db: Session, data: dict[str, str]) -> dict[str, str]:
    for key, value in data.items():
        if key not in ALLOWED_KEYS or value is None:
            continue
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
    db.commit()
    return get_abuse_settings(db)


def render_abuse_html(db: Session) -> str:
    """Build the public abuse page HTML from current settings."""
    s = get_abuse_settings(db)

    # HTML-escape all values to prevent XSS
    esc = {k: html.escape(v) for k, v in s.items()}

    # Build conditional sections
    hostname = esc["hostname"]
    responsible = esc["abuse_responsible"]
    phone = esc["abuse_phone"]
    imprint_url = esc["abuse_imprint_url"]

    # Intro text: optionally include responsible party name
    if responsible:
        esc["responsible_intro"] = f" ({responsible})"
    else:
        esc["responsible_intro"] = ""

    # Responsible party in contact grid
    if responsible:
        esc["responsible_section"] = (
            '      <div class="contact-item">\n'
            "        <label>Verantwortlich</label>\n"
            f'        <div class="value">{responsible}</div>\n'
            "      </div>\n"
        )
    else:
        esc["responsible_section"] = ""

    # Phone in contact grid
    if phone:
        esc["phone_section"] = (
            '      <div class="contact-item">\n'
            "        <label>Telefon (Geschaeftszeiten)</label>\n"
            f'        <div class="value"><a href="tel:{phone}">{phone}</a></div>\n'
            "      </div>\n"
        )
    else:
        esc["phone_section"] = ""

    # Impressum link in card
    if imprint_url:
        esc["imprint_link"] = f'<a href="{imprint_url}">&rarr; Impressum &amp; Datenschutz</a>'
    else:
        esc["imprint_link"] = '<span style="font-size:0.8rem;color:var(--muted)">Nicht konfiguriert</span>'

    # Responsible row in tech table
    if responsible:
        esc["responsible_row"] = (
            "      <tr>\n"
            "        <td>Betreiber</td>\n"
            f"        <td>{responsible}</td>\n"
            "      </tr>\n"
        )
    else:
        esc["responsible_row"] = ""

    # Footer left
    year = datetime.now(timezone.utc).year
    if responsible:
        esc["footer_left"] = f"&copy; {year} {responsible}"
    else:
        esc["footer_left"] = f"&copy; {year} {hostname}"

    return ABUSE_HTML_TEMPLATE.format(**esc)
