"""Rotate ADMIN_SECRET_KEY: re-encrypt all Fernet-encrypted data in the DB.

The Fernet key for SMTP user passwords is derived from ADMIN_SECRET_KEY
(see app/services/crypto_service.py). Changing the secret therefore makes
all stored SMTP passwords undecryptable. This tool re-encrypts them.

Usage (inside the admin container, while the panel is running or stopped):

    docker exec -it open-mail-relay-admin \
        python -m app.tools.rotate_secret_key '<OLD_KEY>' '<NEW_KEY>'

Afterwards:
    1. Set ADMIN_SECRET_KEY=<NEW_KEY> in .env
    2. docker compose up -d admin-panel   (recreates with the new key)

Note: rotating the key invalidates all active admin sessions (re-login
required). SMTP user passwords keep working because they are re-encrypted.
"""
import base64
import sys

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.database import SessionLocal
from app.models import SmtpUser

# Must match app/services/crypto_service.py exactly
KDF_SALT = b"open-mail-relay-smtp-users"
KDF_ITERATIONS = 480_000


def _derive_fernet(secret: str) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=KDF_SALT,
        iterations=KDF_ITERATIONS,
    )
    return Fernet(base64.urlsafe_b64encode(kdf.derive(secret.encode())))


def rotate(old_key: str, new_key: str) -> int:
    if old_key == new_key:
        print("ERROR: old and new key are identical — nothing to do.")
        return 1
    if len(new_key) < 32:
        print("ERROR: new key must be at least 32 characters (openssl rand -hex 32).")
        return 1

    old_fernet = _derive_fernet(old_key)
    new_fernet = _derive_fernet(new_key)

    db = SessionLocal()
    try:
        users = db.query(SmtpUser).all()
        rotated = []
        for user in users:
            try:
                plain = old_fernet.decrypt(user.password_encrypted.encode()).decode()
            except InvalidToken:
                print(
                    f"ERROR: cannot decrypt password of '{user.username}' with the "
                    "OLD key — wrong old key? Aborting without changes."
                )
                db.rollback()
                return 1
            rotated.append((user, new_fernet.encrypt(plain.encode()).decode()))

        for user, token in rotated:
            user.password_encrypted = token
        db.commit()
        print(f"OK: re-encrypted {len(rotated)} SMTP user password(s).")
        print("Now set ADMIN_SECRET_KEY in .env and run: docker compose up -d admin-panel")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(rotate(sys.argv[1], sys.argv[2]))
