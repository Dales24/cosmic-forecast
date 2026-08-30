"""Authentication — password hashing, session tokens, and the current-user
dependency.

Standard library only (PBKDF2 + SHA-256), so there's no native crypto build to
manage. Passwords are stored as a salted PBKDF2 hash; session tokens are random
and only their SHA-256 hash is stored, so a database leak doesn't expose live
tokens.
"""

import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException

from app import db

_PBKDF2_ROUNDS = 100_000
_MIN_USERNAME = 3
_MIN_PASSWORD = 8


def admin_usernames() -> set:
    """Usernames granted admin, from the COSMIC_ADMIN_USERS env var (comma-list)."""
    raw = os.environ.get("COSMIC_ADMIN_USERS", "")
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """Return (hex_hash, hex_salt). Generates a fresh salt when none is given."""
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS
    )
    return digest.hex(), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def register(username: str, password: str, email: Optional[str] = None) -> dict:
    """Create a user. Raises HTTPException on invalid input or a taken name."""
    username = (username or "").strip()
    if len(username) < _MIN_USERNAME:
        raise HTTPException(
            400, f"username must be at least {_MIN_USERNAME} characters"
        )
    if len(password or "") < _MIN_PASSWORD:
        raise HTTPException(
            400, f"password must be at least {_MIN_PASSWORD} characters"
        )
    if db.get_user_by_username(username):
        raise HTTPException(409, "username already taken")
    pw_hash, salt = hash_password(password)
    is_admin = username.lower() in admin_usernames()
    user_id = db.create_user(username, email, pw_hash, salt, is_admin=is_admin)
    return {"id": user_id, "username": username, "is_admin": is_admin}


def login(username: str, password: str) -> str:
    """Verify credentials and return a fresh session token."""
    user = db.get_user_by_username((username or "").strip())
    if not user or not verify_password(password, user["salt"], user["password_hash"]):
        raise HTTPException(401, "invalid username or password")
    token = new_token()
    db.create_session(user["id"], token_hash(token))
    return token


def logout(token: str) -> None:
    if token:
        db.delete_session(token_hash(token))


def bearer_token(authorization: str) -> str:
    """Pull the token out of an ``Authorization: Bearer <token>`` header."""
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def current_user(authorization: str = Header(default="")):
    """FastAPI dependency: resolve the caller from an ``Authorization: Bearer``
    header, or 401."""
    token = bearer_token(authorization)
    if not token:
        raise HTTPException(401, "not authenticated")
    user = db.get_user_by_token(token_hash(token))
    if not user:
        raise HTTPException(401, "invalid or expired token")
    return user


def require_admin(user=Depends(current_user)):
    """FastAPI dependency: like current_user, but 403 unless the user is admin."""
    if not user["is_admin"]:
        raise HTTPException(403, "admin access required")
    return user
