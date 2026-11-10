from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate


def register_user(db: Session, user_data: UserCreate) -> User:
    """Register a user with a securely hashed password."""

    existing_user = db.scalar(
        select(User).where(
            or_(
                User.username == user_data.username,
                User.email == str(user_data.email).lower(),
            )
        )
    )

    if existing_user:
        raise ValueError("Username or email is already registered")

    user = User(
        username=user_data.username,
        email=str(user_data.email).lower(),
        password_hash=get_password_hash(user_data.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Username or email is already registered"
        ) from exc
    except Exception:
        db.rollback()
        raise


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user using email and password."""

    user = db.scalar(
        select(User).where(User.email == email.strip().lower())
    )

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def login_user(
    db: Session,
    email: str,
    password: str,
) -> dict | None:
    """Authenticate a user and issue an access token."""

    user = authenticate_user(db, email, password)

    if user is None:
        return None

    token = create_access_token(subject=str(user.id))

    return {
        "access_token": token,
        "token_type": "bearer",
    }
