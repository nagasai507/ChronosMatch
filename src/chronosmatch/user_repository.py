"""Database repository functions for ChronosMatch users."""

from sqlalchemy.orm import Session

from .database import SessionLocal
from .db_models import UserRecord


def create_user(
    username: str,
    email: str,
    password_hash: str,
) -> UserRecord:
    """Create and save a new user in PostgreSQL."""

    db: Session = SessionLocal()

    try:
        user = UserRecord(
            username=username,
            email=email.lower(),
            password_hash=password_hash,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_user_by_email(email: str) -> UserRecord | None:
    """Find a user using their email address."""

    db: Session = SessionLocal()

    try:
        return (
            db.query(UserRecord)
            .filter(UserRecord.email == email.lower())
            .first()
        )
    finally:
        db.close()


def get_user_by_username(username: str) -> UserRecord | None:
    """Find a user using their username."""

    db: Session = SessionLocal()

    try:
        return (
            db.query(UserRecord)
            .filter(UserRecord.username == username)
            .first()
        )
    finally:
        db.close()