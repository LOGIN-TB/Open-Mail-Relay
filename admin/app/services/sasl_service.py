"""SASL service for syncing SMTP users to Dovecot passwd-file.

Reads active users from DB, decrypts passwords, writes dovecot-users file,
and reloads Dovecot via Docker exec.
"""
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import SmtpUser
from app.services.crypto_service import decrypt_password
from app.services.docker_service import exec_in_container

logger = logging.getLogger(__name__)

DOVECOT_USERS_FILE = settings.POSTFIX_CONFIG_PATH / "dovecot-users"


def sync_dovecot_users(db: Session) -> tuple[bool, str]:
    """Sync all active SMTP users from DB to Dovecot passwd-file and reload."""
    try:
        users = db.query(SmtpUser).filter(SmtpUser.is_active == True).all()

        lines = []
        for user in users:
            try:
                plain_pw = decrypt_password(user.password_encrypted)
                lines.append(f"{user.username}:{{PLAIN}}{plain_pw}")
            except Exception as e:
                logger.error(f"Failed to decrypt password for user {user.username}: {e}")
                continue

        content = "\n".join(lines) + "\n" if lines else ""
        DOVECOT_USERS_FILE.write_text(content)
        DOVECOT_USERS_FILE.chmod(0o600)

        logger.info(f"Wrote {len(lines)} SMTP users to dovecot-users file")

        # Copy file into mail container and reload Dovecot
        exit_code, output = exec_in_container(
            "cp /etc/postfix-config/dovecot-users /etc/dovecot/users"
        )
        if exit_code != 0:
            return False, f"Failed to copy dovecot-users: {output}"

        exit_code, output = exec_in_container(
            "sh -c 'chown root:dovecot /etc/dovecot/users && chmod 640 /etc/dovecot/users'"
        )
        if exit_code != 0:
            return False, f"Failed to set permissions: {output}"

        exit_code, output = exec_in_container("doveadm reload")
        if exit_code != 0:
            # Dovecot might not be running yet (first start), try starting it
            exit_code2, output2 = exec_in_container("dovecot")
            if exit_code2 != 0:
                return False, f"Failed to reload/start Dovecot: {output} / {output2}"

        return True, f"Synced {len(lines)} SMTP users"

    except Exception as e:
        logger.error(f"Failed to sync dovecot users: {e}")
        return False, str(e)
