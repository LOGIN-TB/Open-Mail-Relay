"""Cryptographic service for SMTP user password management.

Generates passwords and provides Fernet encryption/decryption
with a key derived from ADMIN_SECRET_KEY via PBKDF2.
"""
import base64
import hashlib
import secrets
import string

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from app.config import settings

_fernet: Fernet | None = None

CHARSET = string.ascii_letters + string.digits


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"open-mail-relay-smtp-users",
            iterations=480_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        _fernet = Fernet(key)
    return _fernet


def generate_smtp_password() -> str:
    """Generate a password in format xxxx-xxxxxx-xxxx (4-6-4, alphanumeric)."""
    part1 = "".join(secrets.choice(CHARSET) for _ in range(4))
    part2 = "".join(secrets.choice(CHARSET) for _ in range(6))
    part3 = "".join(secrets.choice(CHARSET) for _ in range(4))
    return f"{part1}-{part2}-{part3}"


def encrypt_password(plain: str) -> str:
    """Encrypt a plaintext password using Fernet."""
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_password(token: str) -> str:
    """Decrypt a Fernet-encrypted password back to plaintext."""
    return _get_fernet().decrypt(token.encode()).decode()


# Dovecot passwd-file hash format: {SHA512-CRYPT}$6$<salt>$<86 chars>
SMTP_PASSWORD_HASH_RE = r"^\{SHA512-CRYPT\}\$6\$[./A-Za-z0-9]{8,16}\$[./A-Za-z0-9]{86}$"


def hash_smtp_password(plain: str) -> str:
    """Hash a plaintext SMTP password for the Dovecot passwd-file.

    Primary: glibc sha512_crypt via the stdlib crypt module (python:3.12
    base image). Fallback for Python >= 3.13 (crypt removed) or platforms
    without $6$ support: `openssl passwd -6`, password passed via stdin so
    it never appears in a process list.
    """
    try:
        import crypt
        if any(getattr(m, "name", "") == "SHA512" for m in crypt.methods):
            return "{SHA512-CRYPT}" + crypt.crypt(plain, crypt.mksalt(crypt.METHOD_SHA512))
    except ImportError:
        pass
    import subprocess
    out = subprocess.run(
        ["openssl", "passwd", "-6", "-stdin"],
        input=plain, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return "{SHA512-CRYPT}" + out
