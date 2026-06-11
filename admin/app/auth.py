from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt only uses the first 72 bytes; truncate explicitly to keep the
    # behavior passlib had (silent truncation) for existing hashes.
    try:
        return bcrypt.checkpw(plain_password.encode()[:72], hashed_password.encode())
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        return None
