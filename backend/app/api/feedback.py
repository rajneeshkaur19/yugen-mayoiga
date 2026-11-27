"""Feedback & Issue Reporting API endpoint."""

from __future__ import annotations

import html
import re
import threading
import time
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.api.auth import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.feedback import FeedbackSubmission
from backend.app.models.user import User
from backend.app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])

_optional_bearer = HTTPBearer(auto_error=False)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Simple thread-safe in-memory sliding-window rate limiter
_RATE_LIMIT_WINDOW_SECONDS = 300
_RATE_LIMIT_MAX_REQUESTS = 5
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()


def _sanitize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = _CONTROL_CHARS_RE.sub("", value).strip()
    return html.escape(cleaned, quote=False)


def _get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user if a valid Bearer token is provided; otherwise None."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        sub = payload.get("sub")
        if not sub:
            return None
        user_id = int(sub)
        return db.get(User, user_id)
    except Exception:
        return None


def _check_rate_limit(bucket_key: str) -> None:
    now = time.monotonic()
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
    with _rate_lock:
        recent = [ts for ts in _rate_buckets[bucket_key] if ts > cutoff]
        if len(recent) >= _RATE_LIMIT_MAX_REQUESTS:
            _rate_buckets[bucket_key] = recent
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many feedback submissions in a short period. Please wait a few minutes before submitting again.",
            )
        recent.append(now)
        _rate_buckets[bucket_key] = recent


def reset_feedback_rate_limiter() -> None:
    """Test helper to clear the in-memory rate-limit buckets."""
    with _rate_lock:
        _rate_buckets.clear()


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    payload: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(_get_optional_current_user),
):
    """Submit a bug report, technical issue, suggestion, or general feedback."""
    client_ip = request.client.host if request.client else "unknown"
    bucket_key = f"user:{current_user.id}" if current_user else f"ip:{client_ip}"
    _check_rate_limit(bucket_key)

    sanitized_name = _sanitize_text(payload.name)
    sanitized_subject = _sanitize_text(payload.subject) or ""
    sanitized_message = _sanitize_text(payload.message) or ""

    if len(sanitized_subject.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Subject must contain at least 2 valid characters.",
        )
    if len(sanitized_message.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message must contain at least 5 valid characters.",
        )

    submission = FeedbackSubmission(
        user_id=current_user.id if current_user else None,
        name=sanitized_name,
        email=str(payload.email) if payload.email else None,
        feedback_type=payload.feedback_type,
        subject=sanitized_subject,
        message=sanitized_message,
        client_ip=client_ip[:64],
    )
    try:
        db.add(submission)
        db.commit()
        db.refresh(submission)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to record your feedback right now. Please try again later.",
        )

    return FeedbackResponse(
        id=submission.id,
        user_id=submission.user_id,
        feedback_type=submission.feedback_type,
        subject=submission.subject,
        created_at=submission.created_at,
        email_sent=False,
        message="Thank you. Your feedback has been recorded in our archive.",
    )
