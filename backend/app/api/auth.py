import hashlib
import html
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr
from typing import Generator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.core.security import (
    decode_access_token,
    get_password_hash,
)
from backend.app.database.session import SessionLocal
from backend.app.models.user import User
from backend.app.models.password_reset_token import PasswordResetToken
from backend.app.schemas.user import (
    UserCreate,
    UserLogin,
    UserRead,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from backend.app.services.user_service import (
    register_user,
    login_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def send_branded_email(
    email: str,
    subject: str,
    heading: str,
    body: str,
    button_text: str,
    button_url: str,
) -> bool:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM_EMAIL")
    environment = os.getenv("APP_ENV", "development").lower()

    if not all([host, username, password, sender]):
        if environment != "production":
            print(f"\n[DEV EMAIL] {subject}")
            print(f"To: {email}")
            print(body)
            print(f"Link: {button_url}\n")
            return True
        return False

    safe_heading = html.escape(heading)
    safe_body = html.escape(body).replace("\n", "<br>")
    safe_button = html.escape(button_text)
    safe_url = html.escape(button_url, quote=True)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr(("Yūgen Mayoiga", sender))
    message["To"] = email

    message.set_content(
        f"{heading}\n\n{body}\n\n{button_text}: {button_url}\n\n"
        "If you did not request this, you can safely ignore this email."
    )

    message.add_alternative(
        f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:32px 12px;background:#f4f6f2;
                     font-family:Arial,sans-serif;color:#26352c;">
          <div style="max-width:560px;margin:auto;background:#ffffff;
                      border-radius:12px;overflow:hidden;">
            <div style="background:#143d2b;padding:28px;text-align:center;">
              <div style="color:#d8f3dc;font-size:23px;font-weight:bold;">
                Yūgen Mayoiga
              </div>
              <div style="color:#c5d8ca;font-size:12px;margin-top:8px;">
                STORIES BEYOND THE KNOWN
              </div>
            </div>
            <div style="padding:32px 28px;">
              <h2 style="color:#143d2b;margin-top:0;">{safe_heading}</h2>
              <p style="font-size:15px;line-height:1.7;">{safe_body}</p>
              <p style="margin:28px 0;">
                <a href="{safe_url}"
                   style="background:#143d2b;color:#ffffff;
                          padding:13px 22px;text-decoration:none;
                          border-radius:6px;display:inline-block;">
                  {safe_button}
                </a>
              </p>
              <p style="font-size:12px;color:#68766d;line-height:1.6;">
                If you did not request this, you can safely ignore this email.
                For your security, never share your password with anyone.
              </p>
            </div>
          </div>
        </body>
        </html>
        """,
        subtype="html",
    )

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(message)
        return True
    except Exception as exc:
        print(f"Email delivery failed: {type(exc).__name__}")
        return False


def send_reset_email(email: str, reset_url: str) -> bool:
    return send_branded_email(
        email=email,
        subject="Reset your Yūgen Mayoiga password",
        heading="Password reset requested",
        body=(
            "We received a request to reset your password. "
            "Use the button below to choose a new password. "
            "This link expires in 30 minutes."
        ),
        button_text="Reset password",
        button_url=reset_url,
    )


def send_welcome_email(email: str, username: str) -> bool:
    frontend_url = os.getenv(
        "FRONTEND_URL", "http://localhost:5173"
    ).rstrip("/")

    return send_branded_email(
        email=email,
        subject="Welcome to Yūgen Mayoiga",
        heading=f"Welcome, {username}!",
        body=(
            "Your account has been created successfully. "
            "We're glad you're here. Step into a world of branching "
            "stories, hidden choices, and unexpected paths."
        ),
        button_text="Explore Yūgen Mayoiga",
        button_url=frontend_url,
    )


def send_password_changed_email(email: str, username: str) -> bool:
    frontend_url = os.getenv(
        "FRONTEND_URL", "http://localhost:5173"
    ).rstrip("/")

    return send_branded_email(
        email=email,
        subject="Your Yūgen Mayoiga password was changed",
        heading="Password successfully changed",
        body=(
            f"Hello {username}, your account password was changed "
            "successfully. If you made this change, no further action "
            "is needed. If you did not make this change, please reset "
            "your password immediately and secure your account."
        ),
        button_text="Visit Yūgen Mayoiga",
        button_url=frontend_url,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        user = register_user(db, user_data)

        background_tasks.add_task(
            send_welcome_email,
            user.email,
            user.username,
        )

        return user

    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    result = login_user(db, credentials.email, credentials.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    generic_response = {
        "message": "Password reset instructions sent."
    }

    user = db.scalar(
        select(User).where(User.email == str(request.email).strip().lower())
    )
    if user is None:
        return generic_response

    now = datetime.now(timezone.utc)

    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=30),
    )
    db.add(reset_record)
    db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={raw_token}"

    if not send_reset_email(user.email, reset_url):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email is not configured. Please try again later.",
        )

    return generic_response


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(
        request.token.encode("utf-8")
    ).hexdigest()

    reset_record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    )

    now = datetime.now(timezone.utc)

    if reset_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    expires_at = reset_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        reset_record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    user = db.get(User, reset_record.user_id)
    if user is None:
        reset_record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    user.password_hash = get_password_hash(request.new_password)
    reset_record.used_at = now

    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset_record.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    db.commit()

    background_tasks.add_task(
        send_password_changed_email,
        user.email,
        user.username,
    )

    return {"message": "Password updated successfully!"}
