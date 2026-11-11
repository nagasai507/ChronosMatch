"""SQLAlchemy database models for ChronosMatch."""

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class OrderRecord(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(
        String(100), primary_key=True
    )
    side: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    price: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    remaining_quantity: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    timestamp: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )


class TradeRecord(Base):
    __tablename__ = "trades"

    trade_id: Mapped[str] = mapped_column(
        String(100), primary_key=True
    )
    buy_order_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("orders.order_id"),
        nullable=False,
    )
    sell_order_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("orders.order_id"),
        nullable=False,
    )
    price: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    timestamp: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )


class UserRecord(Base):
    """Database model for registered ChronosMatch users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )