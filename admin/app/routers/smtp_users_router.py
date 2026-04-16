"""SMTP Users CRUD router.

Manages SMTP authentication users (SASL). All endpoints require admin privileges.
Every mutation syncs the Dovecot passwd-file and logs an audit entry.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import SmtpUser, AuditLog, User, Package
from app.schemas import SmtpUserCreate, SmtpUserOut, SmtpUserWithPassword, SmtpUserUpdate
from app.services.crypto_service import generate_smtp_password, encrypt_password, decrypt_password
from app.services.sasl_service import sync_dovecot_users
from app.services.pdf_service import generate_config_pdf
from app.services.postfix_service import read_main_cf
from app.services.spf_check_service import check_customer_spf, check_customer_dkim_cname
from app.services.abuse_service import get_abuse_settings
from app.services.billing_service import send_single_usage_report

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_smtp_host() -> str:
    """Read SMTP hostname from postfix config."""
    config = read_main_cf()
    return config.get("myhostname", "relay.example.com")


def _audit(db: Session, admin: User, action: str, details: str, request: Request):
    db.add(AuditLog(
        user_id=admin.id,
        action=action,
        details=details,
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()


@router.get("", response_model=list[SmtpUserOut])
def list_smtp_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(SmtpUser).order_by(SmtpUser.id).all()
    # Resolve package names
    pkg_ids = {u.package_id for u in users if u.package_id}
    pkg_map = {}
    if pkg_ids:
        pkgs = db.query(Package).filter(Package.id.in_(pkg_ids)).all()
        pkg_map = {p.id: p.name for p in pkgs}

    result = []
    for u in users:
        data = SmtpUserOut.model_validate(u)
        data.package_name = pkg_map.get(u.package_id) if u.package_id else None
        result.append(data)
    return result


@router.post("", response_model=SmtpUserWithPassword, status_code=201)
def create_smtp_user(
    body: SmtpUserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(SmtpUser).filter(SmtpUser.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="SMTP-Benutzername existiert bereits")

    password = generate_smtp_password()

    user = SmtpUser(
        username=body.username,
        password_encrypted=encrypt_password(password),
        is_active=True,
        company=body.company,
        service=body.service,
        mail_domain=body.mail_domain,
        contact_email=body.contact_email,
        receive_reports=body.receive_reports,
        package_id=body.package_id,
        created_by=admin.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _audit(db, admin, "smtp_user_created", f"Created SMTP user '{body.username}'", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after creating user: {msg}")

    pkg_name = None
    if user.package_id:
        pkg = db.query(Package).filter(Package.id == user.package_id).first()
        pkg_name = pkg.name if pkg else None

    return SmtpUserWithPassword(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        company=user.company,
        service=user.service,
        mail_domain=user.mail_domain,
        contact_email=user.contact_email,
        package_id=user.package_id,
        package_name=pkg_name,
        created_at=user.created_at,
        created_by=user.created_by,
        password=password,
    )


@router.put("/{user_id}", response_model=SmtpUserOut)
def update_smtp_user(
    user_id: int,
    body: SmtpUserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.company is not None:
        user.company = body.company
    if body.service is not None:
        user.service = body.service
    if body.mail_domain is not None:
        user.mail_domain = body.mail_domain or None
    if body.contact_email is not None:
        user.contact_email = body.contact_email or None
    if body.receive_reports is not None:
        user.receive_reports = body.receive_reports
    if body.package_id is not None:
        user.package_id = body.package_id if body.package_id != 0 else None

    db.commit()
    db.refresh(user)

    _audit(db, admin, "smtp_user_updated", f"SMTP user '{user.username}' updated", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after updating user: {msg}")

    # Resolve package name for response
    pkg_name = None
    if user.package_id:
        pkg = db.query(Package).filter(Package.id == user.package_id).first()
        pkg_name = pkg.name if pkg else None

    data = SmtpUserOut.model_validate(user)
    data.package_name = pkg_name
    return data


@router.post("/{user_id}/regenerate-password", response_model=SmtpUserWithPassword)
def regenerate_password(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    password = generate_smtp_password()
    user.password_encrypted = encrypt_password(password)
    db.commit()
    db.refresh(user)

    _audit(db, admin, "smtp_user_password_regenerated",
           f"Regenerated password for SMTP user '{user.username}'", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after password regeneration: {msg}")

    pkg_name = None
    if user.package_id:
        pkg = db.query(Package).filter(Package.id == user.package_id).first()
        pkg_name = pkg.name if pkg else None

    return SmtpUserWithPassword(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        company=user.company,
        service=user.service,
        mail_domain=user.mail_domain,
        contact_email=user.contact_email,
        package_id=user.package_id,
        package_name=pkg_name,
        created_at=user.created_at,
        created_by=user.created_by,
        password=password,
    )


@router.delete("/{user_id}", status_code=204)
def delete_smtp_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    username = user.username
    db.delete(user)
    db.commit()

    _audit(db, admin, "smtp_user_deleted", f"Deleted SMTP user '{username}'", request)

    success, msg = sync_dovecot_users(db)
    if not success:
        logger.warning(f"Dovecot sync failed after deleting user: {msg}")


def _build_config_pdf(user: SmtpUser, db: Session) -> tuple[bytes, dict | None]:
    """Generate config PDF and return (pdf_bytes, operator_info)."""
    try:
        password = decrypt_password(user.password_encrypted)
    except Exception:
        raise HTTPException(status_code=500, detail="Passwort konnte nicht entschluesselt werden")

    smtp_host = _get_smtp_host()

    # SPF + DKIM checks for customer domain
    spf_info = None
    dkim_info = None
    if user.mail_domain:
        parts = smtp_host.split(".")
        relay_domain = ".".join(parts[1:]) if len(parts) > 2 else smtp_host
        try:
            spf_info = check_customer_spf(user.mail_domain, relay_domain)
        except Exception as e:
            logger.warning(f"SPF check failed for {user.mail_domain}: {e}")
        try:
            dkim_info = check_customer_dkim_cname(user.mail_domain, smtp_host)
        except Exception as e:
            logger.warning(f"DKIM check failed for {user.mail_domain}: {e}")

    # Operator info from abuse/config settings
    operator_info = None
    abuse = {}
    try:
        abuse = get_abuse_settings(db)
        responsible = abuse.get("abuse_responsible", "")
        email = abuse.get("postmaster_email", "")
        phone = abuse.get("abuse_phone", "")
        if responsible or email or phone:
            operator_info = {
                "responsible": responsible,
                "email": email,
                "phone": phone,
            }
    except Exception as e:
        logger.warning(f"Failed to load operator info: {e}")

    # Resolve package name
    pkg_name = None
    if user.package_id:
        pkg = db.query(Package).filter(Package.id == user.package_id).first()
        pkg_name = pkg.name if pkg else None

    pdf_bytes = generate_config_pdf(
        user.username, password, smtp_host,
        company=user.company, service=user.service,
        mail_domain=user.mail_domain, contact_email=user.contact_email,
        package_name=pkg_name,
        spf_info=spf_info, dkim_info=dkim_info, operator_info=operator_info,
    )

    return pdf_bytes, operator_info, abuse


@router.get("/{user_id}/config-pdf")
def download_config_pdf(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    pdf_bytes, _, _ = _build_config_pdf(user, db)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="smtp-config-{user.username}.pdf"',
        },
    )


@router.post("/{user_id}/send-credentials")
def send_credentials(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    if not user.contact_email:
        raise HTTPException(status_code=400, detail="Keine Kontakt-E-Mail hinterlegt")

    pdf_bytes, operator_info, abuse = _build_config_pdf(user, db)

    # Build email
    mail_from = abuse.get("postmaster_email", f"postmaster@{_get_smtp_host()}")
    mail_to = user.contact_email
    smtp_host = _get_smtp_host()

    # Operator signature
    sig_parts = []
    if operator_info and operator_info.get("responsible"):
        sig_parts.append(operator_info["responsible"])
    if operator_info and operator_info.get("email"):
        sig_parts.append(f'E-Mail: <a href="mailto:{operator_info["email"]}">{operator_info["email"]}</a>')
    if operator_info and operator_info.get("phone"):
        sig_parts.append(f"Telefon: {operator_info['phone']}")
    signature_html = "<br>".join(sig_parts) if sig_parts else smtp_host

    html_body = f"""\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; line-height: 1.6; max-width: 600px; margin: 0 auto;">
  <div style="background: #1e293b; padding: 24px 32px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 20px;">SMTP-Relay Zugangsdaten</h1>
  </div>
  <div style="padding: 32px; background: #ffffff; border: 1px solid #e2e8f0; border-top: none;">
    <p>Guten Tag,</p>
    <p>anbei erhalten Sie die Zugangsdaten fuer den SMTP-Relay-Dienst
       <strong>{smtp_host}</strong> fuer den Benutzer <strong>{user.username}</strong>.</p>
    <p>Die vollstaendigen Verbindungsdaten inkl. Einrichtungsanleitung finden Sie im
       beigefuegten PDF-Dokument.</p>
    <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 16px; margin: 24px 0;">
      <strong style="color: #92400e;">Sicherheitshinweis:</strong>
      <p style="margin: 8px 0 0 0; color: #92400e;">Bewahren Sie die Zugangsdaten sicher auf und geben Sie diese
         nicht an unbefugte Personen weiter. Bei Verdacht auf Missbrauch
         verstaendigen Sie uns umgehend.</p>
    </div>
    <p>Mit freundlichen Gruessen</p>
    <div style="border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 16px; color: #64748b; font-size: 14px;">
      {signature_html}
    </div>
  </div>
</body>
</html>"""

    msg = MIMEMultipart()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = f"SMTP-Relay Zugangsdaten \u2014 {user.username}"
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Attach PDF
    pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_attachment.add_header(
        "Content-Disposition", "attachment",
        filename=f"smtp-config-{user.username}.pdf",
    )
    msg.attach(pdf_attachment)

    try:
        server = smtplib.SMTP("open-mail-relay", 25, timeout=30)
        server.sendmail(mail_from, [mail_to], msg.as_string())
        server.quit()
    except Exception as e:
        logger.error(f"Failed to send credentials email to {mail_to}: {e}")
        raise HTTPException(status_code=500, detail="E-Mail konnte nicht gesendet werden")

    _audit(db, admin, "smtp_credentials_sent",
           f"Sent credentials for '{user.username}' to {mail_to}", request)

    return {"detail": "Zugangsdaten wurden versendet"}


@router.post("/{user_id}/send-usage-report")
def send_usage_report(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(SmtpUser).filter(SmtpUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SMTP-Benutzer nicht gefunden")

    if not user.contact_email:
        raise HTTPException(status_code=400, detail="Keine Kontakt-E-Mail hinterlegt")

    if not user.package_id:
        raise HTTPException(status_code=400, detail="Kein Paket zugewiesen")

    success = send_single_usage_report(db, user)
    if not success:
        raise HTTPException(status_code=500, detail="Bericht konnte nicht gesendet werden")

    _audit(db, admin, "smtp_usage_report_sent",
           f"Sent usage report for '{user.username}' to {user.contact_email}", request)

    return {"detail": "Kontingent-Bericht wurde versendet"}
