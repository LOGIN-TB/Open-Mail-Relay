"""Cert background worker — taeglicher TLS-Zertifikats-Check, Auto-Erneuerung und E-Mail-Warnung."""

import asyncio
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.database import SessionLocal
from app.models import AuditLog, SystemSetting
from app.schemas import CertInfo
from app.services.cert_service import get_all_certs, renew_certs

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 6 * 3600  # alle 6 Stunden pruefen
INITIAL_DELAY = 300  # 5 Minuten nach Start
RENEW_COOLDOWN = 12 * 3600  # max. 1 automatische Erneuerung pro 12h


class CertWorker:
    def __init__(self):
        self._running = False
        self._last_renew_attempt: datetime | None = None
        # name -> "YYYY-MM-DD" des letzten Alerts (max. 1 Mail pro Cert/Tag)
        self._last_alert_day: dict[str, str] = {}

    def stop(self):
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("Cert worker starting")
        await asyncio.sleep(INITIAL_DELAY)

        while self._running:
            try:
                await asyncio.to_thread(self._check_once)
            except Exception as e:
                logger.error(f"Cert check error: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

    # ------------------------------------------------------------------
    def _check_once(self) -> None:
        certs = get_all_certs()
        if not certs:
            return

        problem = [c for c in certs if c.status in ("expired", "expiring")]
        if not problem:
            logger.debug("Cert check: all certificates valid")
            return

        names = ", ".join(f"{c.name} ({c.status})" for c in problem)
        logger.warning(f"Cert check: certificates need attention: {names}")

        # 1) Automatische Erneuerung (gedrosselt auf max. 1x/12h)
        renew_ok = None
        renew_msg = ""
        now = datetime.now(timezone.utc)
        cooldown_active = (
            self._last_renew_attempt is not None
            and (now - self._last_renew_attempt).total_seconds() < RENEW_COOLDOWN
        )
        if not cooldown_active:
            self._last_renew_attempt = now
            renew_ok, renew_msg = renew_certs()
            self._audit(renew_ok, names, renew_msg)
            if renew_ok:
                # Status nach Erneuerung neu bewerten
                certs = get_all_certs()
                problem = [c for c in certs if c.status in ("expired", "expiring")]

        # 2) E-Mail-Warnung fuer weiterhin problematische Certs (max. 1/Tag/Cert)
        if problem:
            self._send_alerts(problem, renew_ok, renew_msg)

    def _audit(self, ok: bool, names: str, msg: str) -> None:
        db = SessionLocal()
        try:
            db.add(AuditLog(
                user_id=None,
                action="tls_cert_auto_renew",
                details=f"Auto-Erneuerung ({'OK' if ok else 'FEHLER'}) fuer {names}: {msg}",
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Cert audit log failed: {e}")
        finally:
            db.close()

    # ------------------------------------------------------------------
    def _send_alerts(self, problem: list[CertInfo], renew_ok, renew_msg: str) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        to_alert = [c for c in problem if self._last_alert_day.get(c.name) != today]
        if not to_alert:
            return

        recipient = self._recipient()
        if not recipient:
            logger.warning("Cert alert: kein Empfaenger (LETSENCRYPT_EMAIL/rbl_mail_to) konfiguriert")
            return

        lines = []
        for c in to_alert:
            if c.status == "expired":
                lines.append(f"- {c.name}: ABGELAUFEN seit {abs(c.days_remaining or 0)} Tag(en) (Aussteller: {c.issuer or '?'})")
            else:
                lines.append(f"- {c.name}: laeuft in {c.days_remaining} Tag(en) ab (Aussteller: {c.issuer or '?'})")

        if renew_ok is True:
            renew_note = f"Eine automatische Erneuerung wurde ausgeloest, das Problem besteht aber weiterhin:\n{renew_msg}"
        elif renew_ok is False:
            renew_note = f"Die automatische Erneuerung ist FEHLGESCHLAGEN:\n{renew_msg}"
        else:
            renew_note = "Eine automatische Erneuerung wurde in den letzten 12h bereits versucht (Cooldown aktiv)."

        body = (
            "Achtung: Ein oder mehrere TLS-Zertifikate des Mail-Relays benoetigen Aufmerksamkeit.\n\n"
            + "\n".join(lines)
            + "\n\n"
            + renew_note
            + "\n\nBitte pruefen Sie die DNS-/Netzwerk-Konfiguration (Ports 80/443 erreichbar?) "
            "und den Status im Admin-Panel unter Konfiguration -> TLS-Zertifikat.\n"
        )
        subject = "[Mail-Relay] TLS-Zertifikat laeuft ab / abgelaufen"

        if self._send_mail(recipient, subject, body):
            for c in to_alert:
                self._last_alert_day[c.name] = today

    def _recipient(self) -> str:
        # Bevorzugt LETSENCRYPT_EMAIL (nicht unter ADMIN_-Prefix -> direkt aus env)
        env_mail = os.getenv("LETSENCRYPT_EMAIL", "").strip()
        if env_mail:
            return env_mail
        return self._setting("rbl_mail_to")

    def _setting(self, key: str) -> str:
        db = SessionLocal()
        try:
            row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            return (row.value if row else "").strip()
        finally:
            db.close()

    def _send_mail(self, recipient: str, subject: str, body: str) -> bool:
        mail_from = self._setting("rbl_mail_from")
        if not mail_from:
            from app.services.postfix_service import read_main_cf
            domain = read_main_cf().get("mydomain", "localhost")
            mail_from = f"cert-alert@{domain}"

        msg = MIMEMultipart()
        msg["From"] = mail_from
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            server = smtplib.SMTP("open-mail-relay", 25, timeout=30)
            server.sendmail(mail_from, [recipient], msg.as_string())
            server.quit()
            logger.info("Cert alert sent to %s", recipient)
            return True
        except Exception as e:
            logger.error("Cert alert send failed: %s", e)
            return False
