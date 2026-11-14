import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession
from .database import get_db
from .models import Session, User
from .config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(candidate, digest)


def create_session(db: DBSession, user: User, response: Response):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(Session(id=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, csrf=csrf,
                   expires=datetime.now(timezone.utc) + timedelta(days=settings.session_days)))
    db.commit()
    response.set_cookie("spendwise_session", token, httponly=True, secure=settings.cookie_secure,
                        samesite="lax", max_age=settings.session_days * 86400, path="/")
    return {"csrf": csrf, "user": public_user(user)}


def public_user(user):
    return {"id": user.id, "name": user.name, "email": user.email, "currency": user.currency, "notifications": user.notifications}


def current_user(request: Request, db: DBSession = Depends(get_db)):
    token = request.cookies.get("spendwise_session", "")
    session = db.get(Session, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not session or session.expires.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Please sign in")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf):
            raise HTTPException(403, "Invalid CSRF token")
    request.state.session = session
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Please sign in")
    return user
