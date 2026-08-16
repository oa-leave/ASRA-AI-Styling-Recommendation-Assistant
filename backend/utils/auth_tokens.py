import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.core.config import settings
from database.models import LoginAttempt, RefreshToken


def utcnow() -> datetime:
    """Return naive UTC for SQLite-friendly timestamp comparisons."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(token),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
    ))
    db.commit()
    return token


def consume_refresh_token(
    db: Session,
    raw_token: str,
) -> Optional[RefreshToken]:
    """Atomically revoke a refresh token, returning it only when this call wins."""
    token_hash = _hash_token(raw_token)
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    if row is None or row.revoked_at is not None:
        return None

    updated = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.id == row.id,
            RefreshToken.revoked_at.is_(None),
        )
        .update(
            {RefreshToken.revoked_at: utcnow()},
            synchronize_session=False,
        )
    )
    db.commit()
    if updated != 1:
        return None
    return row


def revoke_refresh_token(db: Session, raw_token: str) -> bool:
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == _hash_token(raw_token))
        .first()
    )
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = utcnow()
    db.commit()
    return True


def is_login_locked(db: Session, username: str) -> bool:
    cutoff = utcnow() - timedelta(minutes=settings.login_lockout_minutes)
    failed_attempts = (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.username == username,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.created_at >= cutoff,
        )
        .count()
    )
    return failed_attempts >= settings.max_login_attempts


def record_login_attempt(db: Session, username: str, succeeded: bool) -> None:
    db.add(LoginAttempt(username=username, succeeded=succeeded))
    db.commit()


def clear_login_attempts(db: Session, username: str) -> None:
    attempts = (
        db.query(LoginAttempt)
        .filter(LoginAttempt.username == username)
        .all()
    )
    for attempt in attempts:
        db.delete(attempt)
    db.commit()
