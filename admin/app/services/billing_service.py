"""Billing service — package CRUD, monthly usage aggregation, overage calculation, report generation."""

import json
import logging
import math
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.abuse_service import get_abuse_settings

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Package, SmtpUser, UserMonthlyUsage, BillingReport, MailEvent, SystemSetting

logger = logging.getLogger(__name__)


# --- Seed ---

def seed_default_packages(db: Session) -> None:
    """Seed default packages if table is empty."""
    if db.query(Package).count() > 0:
        return
    defaults = [
        Package(name="Trans-S", category="transaction", monthly_limit=500, description="Transaktional bis 500 E-Mails/Monat"),
        Package(name="Trans-M", category="transaction", monthly_limit=1000, description="Transaktional bis 1.000 E-Mails/Monat"),
        Package(name="Trans-L", category="transaction", monthly_limit=5000, description="Transaktional bis 5.000 E-Mails/Monat"),
        Package(name="News-S", category="newsletter", monthly_limit=5000, description="Newsletter bis 5.000 E-Mails/Monat"),
        Package(name="News-M", category="newsletter", monthly_limit=10000, description="Newsletter bis 10.000 E-Mails/Monat"),
        Package(name="News-L", category="newsletter", monthly_limit=25000, description="Newsletter bis 25.000 E-Mails/Monat"),
        Package(name="News-XL", category="newsletter", monthly_limit=50000, description="Newsletter bis 50.000 E-Mails/Monat"),
        Package(name="Ext-1K", category="overage", monthly_limit=1000, description="Zusatzpaket 1.000 E-Mails"),
    ]
    db.add_all(defaults)
    db.commit()
    logger.info("Seeded %d default packages", len(defaults))


# --- Package CRUD ---

def get_all_packages(db: Session) -> list[Package]:
    return db.query(Package).order_by(Package.category, Package.monthly_limit).all()


def get_active_packages(db: Session) -> list[Package]:
    return db.query(Package).filter(Package.is_active == True).order_by(Package.category, Package.monthly_limit).all()


def create_package(db: Session, name: str, category: str, monthly_limit: int, description: str | None = None) -> Package:
    pkg = Package(name=name, category=category, monthly_limit=monthly_limit, description=description)
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg


def update_package(db: Session, package_id: int, **kwargs) -> Package | None:
    pkg = db.query(Package).filter(Package.id == package_id).first()
    if not pkg:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(pkg, key):
            setattr(pkg, key, value)
    db.commit()
    db.refresh(pkg)
    return pkg


def delete_package(db: Session, package_id: int) -> bool:
    """Delete a package. Returns False if users are still assigned."""
    assigned = db.query(SmtpUser).filter(SmtpUser.package_id == package_id).count()
    if assigned > 0:
        return False
    pkg = db.query(Package).filter(Package.id == package_id).first()
    if not pkg:
        return False
    db.delete(pkg)
    db.commit()
    return True


# --- Monthly Usage ---

def refresh_monthly_usage(db: Session, year_month: str | None = None) -> None:
    """Aggregate sent emails from mail_events into user_monthly_usage for the given month."""
    if year_month is None:
        year_month = datetime.now().strftime("%Y-%m")

    year, month = int(year_month[:4]), int(year_month[5:7])
    month_start = datetime(year, month, 1)
    if month == 12:
        month_end = datetime(year + 1, 1, 1)
    else:
        month_end = datetime(year, month + 1, 1)

    # Aggregate from mail_events
    rows = (
        db.query(MailEvent.sasl_username, func.count(MailEvent.id))
        .filter(
            MailEvent.status == "sent",
            MailEvent.sasl_username.isnot(None),
            MailEvent.sasl_username != "",
            MailEvent.timestamp >= month_start,
            MailEvent.timestamp < month_end,
        )
        .group_by(MailEvent.sasl_username)
        .all()
    )

    # Map sasl_username -> smtp_user_id
    smtp_users = db.query(SmtpUser).all()
    username_to_id = {u.username: u.id for u in smtp_users}

    now = datetime.now()
    for sasl_username, count in rows:
        user_id = username_to_id.get(sasl_username)
        if user_id is None:
            continue

        usage = (
            db.query(UserMonthlyUsage)
            .filter(UserMonthlyUsage.smtp_user_id == user_id, UserMonthlyUsage.year_month == year_month)
            .first()
        )
        if usage:
            usage.sent_count = count
            usage.last_updated = now
        else:
            db.add(UserMonthlyUsage(
                smtp_user_id=user_id,
                year_month=year_month,
                sent_count=count,
                last_updated=now,
            ))

    db.commit()
    logger.info("Monthly usage refreshed for %s (%d users with sent mail)", year_month, len(rows))


def calculate_overage(sent: int, limit: int) -> int:
    """Calculate number of Ext-1K overage units needed."""
    if sent <= limit:
        return 0
    return math.ceil((sent - limit) / 1000)


# --- Billing Overview ---

def get_billing_overview(db: Session, year_month: str) -> dict:
    """Build billing overview for all SMTP users for a given month."""
    users = db.query(SmtpUser).order_by(SmtpUser.username).all()
    packages = {p.id: p for p in db.query(Package).all()}

    # Get usage data
    usage_rows = (
        db.query(UserMonthlyUsage)
        .filter(UserMonthlyUsage.year_month == year_month)
        .all()
    )
    usage_map = {u.smtp_user_id: u.sent_count for u in usage_rows}

    items = []
    total_sent = 0
    total_overage = 0

    for user in users:
        sent = usage_map.get(user.id, 0)
        pkg = packages.get(user.package_id) if user.package_id else None
        limit = pkg.monthly_limit if pkg else 0
        overage = calculate_overage(sent, limit) if pkg else 0
        overage_emails = max(0, sent - limit) if pkg else 0

        items.append({
            "smtp_user_id": user.id,
            "username": user.username,
            "company": user.company,
            "package_name": pkg.name if pkg else None,
            "package_limit": limit if pkg else None,
            "sent_count": sent,
            "overage_count": overage,
            "overage_emails": overage_emails,
        })
        total_sent += sent
        total_overage += overage

    return {
        "year_month": year_month,
        "items": items,
        "total_sent": total_sent,
        "total_overage_units": total_overage,
    }


# --- Settings ---

def get_billing_settings(db: Session) -> dict[str, str]:
    keys = ["billing_report_email", "billing_report_from", "usage_report_enabled", "usage_report_day"]
    defaults = {
        "billing_report_email": "",
        "billing_report_from": "",
        "usage_report_enabled": "true",
        "usage_report_day": "monday",
    }
    rows = db.query(SystemSetting).filter(SystemSetting.key.in_(keys)).all()
    result = dict(defaults)
    for row in rows:
        result[row.key] = row.value
    return result


def update_billing_settings(db: Session, **kwargs) -> dict[str, str]:
    for key, value in kwargs.items():
        if value is None:
            continue
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if existing:
            existing.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
    db.commit()
    return get_billing_settings(db)


# --- Report Generation & Sending ---

def generate_billing_report(db: Session, year_month: str) -> dict:
    """Generate and store a billing report for the given month."""
    overview = get_billing_overview(db, year_month)

    report = BillingReport(
        year_month=year_month,
        generated_at=datetime.now(),
        report_data=json.dumps(overview, default=str),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return overview


def _build_report_html(overview: dict) -> str:
    """Build HTML email body for the billing report."""
    ym = overview["year_month"]
    rows_html = ""
    for item in overview["items"]:
        pkg_name = item["package_name"] or "-"
        pkg_limit = f'{item["package_limit"]:,}'.replace(",", ".") if item["package_limit"] else "-"
        sent = f'{item["sent_count"]:,}'.replace(",", ".")
        overage = ""
        if item["overage_count"] > 0:
            overage = f'+ {item["overage_count"]}x Ext-1K'

        rows_html += f"""<tr>
            <td style="padding:6px 12px;border:1px solid #e2e8f0">{item["username"]}</td>
            <td style="padding:6px 12px;border:1px solid #e2e8f0">{item["company"] or "-"}</td>
            <td style="padding:6px 12px;border:1px solid #e2e8f0">{pkg_name}</td>
            <td style="padding:6px 12px;border:1px solid #e2e8f0;text-align:right">{pkg_limit}</td>
            <td style="padding:6px 12px;border:1px solid #e2e8f0;text-align:right">{sent}</td>
            <td style="padding:6px 12px;border:1px solid #e2e8f0">{overage}</td>
        </tr>"""

    total_sent = f'{overview["total_sent"]:,}'.replace(",", ".")
    total_overage = overview["total_overage_units"]

    return f"""<html><body style="font-family:Arial,sans-serif;color:#1e293b">
<h2>Monatsbericht E-Mail-Versand — {ym}</h2>
<table style="border-collapse:collapse;width:100%">
<thead>
<tr style="background:#f1f5f9">
    <th style="padding:8px 12px;border:1px solid #e2e8f0;text-align:left">Benutzer</th>
    <th style="padding:8px 12px;border:1px solid #e2e8f0;text-align:left">Firma</th>
    <th style="padding:8px 12px;border:1px solid #e2e8f0;text-align:left">Paket</th>
    <th style="padding:8px 12px;border:1px solid #e2e8f0;text-align:right">Limit</th>
    <th style="padding:8px 12px;border:1px solid #e2e8f0;text-align:right">Gesendet</th>
    <th style="padding:8px 12px;border:1px solid #e2e8f0;text-align:left">Zusatzpakete</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
<tfoot>
<tr style="background:#f1f5f9;font-weight:bold">
    <td colspan="4" style="padding:8px 12px;border:1px solid #e2e8f0">Gesamt</td>
    <td style="padding:8px 12px;border:1px solid #e2e8f0;text-align:right">{total_sent}</td>
    <td style="padding:8px 12px;border:1px solid #e2e8f0">{total_overage}x Ext-1K</td>
</tr>
</tfoot>
</table>
<p style="color:#64748b;font-size:12px;margin-top:20px">
Automatisch generiert von Open Mail Relay Admin
</p>
</body></html>"""


def send_billing_report(db: Session, year_month: str) -> bool:
    """Generate report and send via email. Returns True on success."""
    settings = get_billing_settings(db)
    mail_to = settings.get("billing_report_email", "")
    mail_from = settings.get("billing_report_from", "")
    if not mail_to or not mail_from:
        logger.warning("Billing report: no email addresses configured")
        return False

    # Refresh usage first
    refresh_monthly_usage(db, year_month)

    overview = generate_billing_report(db, year_month)
    html = _build_report_html(overview)

    msg = MIMEMultipart()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = f"Monatsbericht E-Mail-Versand — {year_month}"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        server = smtplib.SMTP("open-mail-relay", 25, timeout=30)
        server.sendmail(mail_from, [mail_to], msg.as_string())
        server.quit()

        # Update report with sent_to
        report = (
            db.query(BillingReport)
            .filter(BillingReport.year_month == year_month)
            .order_by(BillingReport.id.desc())
            .first()
        )
        if report:
            report.sent_to = mail_to
            db.commit()

        logger.info("Billing report sent for %s to %s", year_month, mail_to)
        return True
    except Exception as e:
        logger.error("Billing report send failed: %s", e)
        return False


# --- Customer Usage Reports ---

def _build_user_section_html(user_data: dict) -> str:
    """Build the per-user block (heading + table + progress bar) for a usage report."""
    sent = user_data["sent_count"]
    limit = user_data["package_limit"] or 0
    remaining = max(0, limit - sent)
    pct = min(100, round(sent / limit * 100)) if limit > 0 else 0

    if pct >= 90:
        bar_color = "#ef4444"
        status_text = "Kontingent fast erschoepft"
    elif pct >= 75:
        bar_color = "#f59e0b"
        status_text = "Kontingent zu mehr als 75% genutzt"
    else:
        bar_color = "#22c55e"
        status_text = ""

    sent_fmt = f"{sent:,}".replace(",", ".")
    limit_fmt = f"{limit:,}".replace(",", ".") if limit else "-"
    remaining_fmt = f"{remaining:,}".replace(",", ".")

    company_line = f' <span style="color:#64748b;font-weight:400;">({user_data["company"]})</span>' if user_data.get("company") else ""

    warning_html = ""
    if status_text:
        warning_html = f"""
    <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:12px;margin:12px 0 0 0;">
      <strong style="color:#92400e;">{status_text}</strong>
    </div>"""

    return f"""
    <div style="margin:24px 0;">
      <h2 style="font-size:16px;margin:0 0 12px 0;color:#1e293b;">SMTP-Benutzer: <strong>{user_data["username"]}</strong>{company_line}</h2>
      <table style="width:100%;border-collapse:collapse;margin:0 0 12px 0;">
        <tr>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;background:#f8fafc;font-weight:600;width:40%">Paket</td>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;">{user_data["package_name"] or "-"}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;background:#f8fafc;font-weight:600;">Monatliches Limit</td>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;">{limit_fmt} E-Mails</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;background:#f8fafc;font-weight:600;">Gesendet</td>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;">{sent_fmt} E-Mails</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;background:#f8fafc;font-weight:600;">Verbleibend</td>
          <td style="padding:10px 14px;border:1px solid #e2e8f0;">{remaining_fmt} E-Mails</td>
        </tr>
      </table>
      <div>
        <div style="background:#e2e8f0;border-radius:8px;height:20px;overflow:hidden;">
          <div style="background:{bar_color};height:100%;width:{pct}%;border-radius:8px;min-width:2px;"></div>
        </div>
        <div style="text-align:right;font-size:13px;color:#64748b;margin-top:4px;">{pct}% genutzt</div>
      </div>{warning_html}
    </div>"""


def _build_usage_report_html(users_data: list[dict], operator_info: dict, year_month: str) -> str:
    """Build HTML email aggregating one or more SMTP users for a single contact recipient."""
    month_names = {
        "01": "Januar", "02": "Februar", "03": "Maerz", "04": "April",
        "05": "Mai", "06": "Juni", "07": "Juli", "08": "August",
        "09": "September", "10": "Oktober", "11": "November", "12": "Dezember"
    }
    month_label = month_names.get(year_month[5:7], year_month[5:7])
    year_label = year_month[:4]

    sig_parts = []
    if operator_info.get("responsible"):
        sig_parts.append(f'<strong>{operator_info["responsible"]}</strong>')
    if operator_info.get("email"):
        sig_parts.append(f'E-Mail: {operator_info["email"]}')
    if operator_info.get("phone"):
        sig_parts.append(f'Telefon: {operator_info["phone"]}')
    signature = "<br>".join(sig_parts)

    if len(users_data) == 1:
        u = users_data[0]
        company_line = f' ({u["company"]})' if u.get("company") else ""
        intro = (f'hier ist die aktuelle Uebersicht Ihres E-Mail-Kontingents fuer '
                 f'<strong>{u["username"]}</strong>{company_line}:')
    else:
        intro = (f'hier ist die aktuelle Uebersicht Ihrer E-Mail-Kontingente fuer '
                 f'Ihre <strong>{len(users_data)}</strong> SMTP-Benutzer:')

    sections = "".join(_build_user_section_html(u) for u in users_data)

    return f"""\
<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1e293b;line-height:1.6;max-width:600px;margin:0 auto;">
  <div style="background:#1e293b;padding:24px 32px;border-radius:8px 8px 0 0;">
    <h1 style="color:white;margin:0;font-size:20px;">Kontingent-Bericht {month_label} {year_label}</h1>
  </div>
  <div style="padding:32px;background:#ffffff;border:1px solid #e2e8f0;border-top:none;">
    <p>Guten Tag,</p>
    <p>{intro}</p>
    {sections}
    <p style="margin-top:24px;">Mit freundlichen Gruessen</p>
    <div style="border-top:1px solid #e2e8f0;padding-top:16px;margin-top:16px;color:#64748b;font-size:14px;">
      {signature}
    </div>
  </div>
</body>
</html>"""


def send_usage_reports(db: Session) -> int:
    """Send aggregated usage reports — one e-mail per contact_email covering all eligible users."""
    year_month = datetime.now().strftime("%Y-%m")

    users = (
        db.query(SmtpUser)
        .filter(
            SmtpUser.receive_reports == True,
            SmtpUser.contact_email.isnot(None),
            SmtpUser.contact_email != "",
            SmtpUser.package_id.isnot(None),
            SmtpUser.is_active == True,
        )
        .all()
    )

    if not users:
        logger.info("No eligible users for usage reports")
        return 0

    packages = {p.id: p for p in db.query(Package).all()}
    usage_rows = (
        db.query(UserMonthlyUsage)
        .filter(UserMonthlyUsage.year_month == year_month)
        .all()
    )
    usage_map = {u.smtp_user_id: u.sent_count for u in usage_rows}

    operator_info = {}
    try:
        abuse = get_abuse_settings(db)
        operator_info = {
            "responsible": abuse.get("abuse_responsible", ""),
            "email": abuse.get("postmaster_email", ""),
            "phone": abuse.get("abuse_phone", ""),
        }
    except Exception:
        pass

    settings = get_billing_settings(db)
    mail_from = settings.get("billing_report_from", "")
    if not mail_from:
        mail_from = operator_info.get("email", "")
    if not mail_from:
        logger.warning("Usage reports: no sender address configured")
        return 0

    # Group eligible users by contact_email (case-insensitive) so each recipient gets one e-mail
    grouped: dict[str, list[dict]] = {}
    for user in users:
        pkg = packages.get(user.package_id)
        if not pkg:
            continue
        key = user.contact_email.strip().lower()
        grouped.setdefault(key, []).append({
            "contact_email": user.contact_email,
            "username": user.username,
            "company": user.company,
            "package_name": pkg.name,
            "package_limit": pkg.monthly_limit,
            "sent_count": usage_map.get(user.id, 0),
        })

    sent_count = 0
    for key, users_data in grouped.items():
        users_data.sort(key=lambda d: d["username"].lower())
        recipient = users_data[0]["contact_email"]

        html = _build_usage_report_html(users_data, operator_info, year_month)

        msg = MIMEMultipart()
        msg["From"] = mail_from
        msg["To"] = recipient
        msg["Subject"] = f"SMTP-Relay Kontingent-Bericht \u2014 {year_month}"
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            server = smtplib.SMTP("open-mail-relay", 25, timeout=30)
            server.sendmail(mail_from, [recipient], msg.as_string())
            server.quit()
            sent_count += 1
        except Exception as e:
            logger.error("Failed to send usage report to %s: %s", recipient, e)

    logger.info("Sent %d usage reports for %s (%d eligible users)", sent_count, year_month, len(users))
    return sent_count


def send_single_usage_report(db: Session, user: SmtpUser) -> bool:
    """Send a usage report for a single user. Returns True on success."""
    year_month = datetime.now().strftime("%Y-%m")

    # Refresh usage data first
    refresh_monthly_usage(db, year_month)

    # Get package
    pkg = db.query(Package).filter(Package.id == user.package_id).first()
    if not pkg:
        return False

    # Get usage
    usage = (
        db.query(UserMonthlyUsage)
        .filter(UserMonthlyUsage.smtp_user_id == user.id, UserMonthlyUsage.year_month == year_month)
        .first()
    )

    # Get operator info
    operator_info = {}
    try:
        abuse = get_abuse_settings(db)
        operator_info = {
            "responsible": abuse.get("abuse_responsible", ""),
            "email": abuse.get("postmaster_email", ""),
            "phone": abuse.get("abuse_phone", ""),
        }
    except Exception:
        pass

    # Get sender address
    settings = get_billing_settings(db)
    mail_from = settings.get("billing_report_from", "")
    if not mail_from:
        mail_from = operator_info.get("email", "")
    if not mail_from:
        logger.warning("Usage report: no sender address configured")
        return False

    user_data = {
        "username": user.username,
        "company": user.company,
        "package_name": pkg.name,
        "package_limit": pkg.monthly_limit,
        "sent_count": usage.sent_count if usage else 0,
    }

    html = _build_usage_report_html([user_data], operator_info, year_month)

    msg = MIMEMultipart()
    msg["From"] = mail_from
    msg["To"] = user.contact_email
    msg["Subject"] = f"SMTP-Relay Kontingent-Bericht \u2014 {year_month}"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        server = smtplib.SMTP("open-mail-relay", 25, timeout=30)
        server.sendmail(mail_from, [user.contact_email], msg.as_string())
        server.quit()
        logger.info("Sent usage report for %s to %s", user.username, user.contact_email)
        return True
    except Exception as e:
        logger.error("Failed to send usage report to %s: %s", user.contact_email, e)
        return False
