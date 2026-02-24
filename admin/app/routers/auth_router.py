from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import verify_password, get_password_hash, create_access_token
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import User, AuditLog
from app.schemas import LoginRequest, TokenResponse, UserOut, UserCreate, UserUpdate

router = APIRouter()

# Simple in-memory rate limiting for login
_login_attempts: dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300


def _check_rate_limit(ip: str):
    import time

    now = time.time()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < LOGIN_WINDOW_SECONDS]
    _login_attempts[ip] = attempts
    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )
    attempts.append(now)
    _login_attempts[ip] = attempts


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


# --- User management (admin only) ---

@router.get("/users", response_model=list[UserOut])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=get_password_hash(body.password),
        is_admin=body.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(AuditLog(
        user_id=admin.id,
        action="user_created",
        details=f"Created user '{body.username}'",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.password is not None:
        user.password_hash = get_password_hash(body.password)
    if body.is_admin is not None:
        user.is_admin = body.is_admin

    db.commit()
    db.refresh(user)

    db.add(AuditLog(
        user_id=admin.id,
        action="user_updated",
        details=f"Updated user '{user.username}' (id={user_id})",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()

    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    username = user.username
    db.delete(user)
    db.commit()

    db.add(AuditLog(
        user_id=admin.id,
        action="user_deleted",
        details=f"Deleted user '{username}' (id={user_id})",
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
