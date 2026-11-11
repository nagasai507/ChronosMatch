"""Database repository functions for ChronosMatch order and trade persistence."""

from collections.abc import Sequence

from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from .database import SessionLocal
from .db_models import OrderRecord, TradeRecord
from .models import Order, Trade


def save_order(order: Order, user_id: int | None = None) -> None:
    """Save or update an order while preserving its ownership."""
    db: Session = SessionLocal()

    try:
        existing = db.get(OrderRecord, order.order_id)

        # Keep the existing owner when updating a resting order.
        owner_id = (
            user_id
            if user_id is not None
            else existing.user_id if existing is not None else None
        )

        record = OrderRecord(
            order_id=order.order_id,
            side=order.side.value,
            price=order.price,
            quantity=order.quantity,
            remaining_quantity=(
                order.remaining_quantity
                if order.remaining_quantity is not None
                else order.quantity
            ),
            timestamp=order.timestamp,
            user_id=owner_id,
        )

        db.merge(record)
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def save_trades(trades: Sequence[Trade]) -> None:
    """Save executed trades in PostgreSQL."""
    if not trades:
        return

    db: Session = SessionLocal()

    try:
        for trade in trades:
            record = TradeRecord(
                trade_id=trade.trade_id,
                buy_order_id=trade.buy_order_id,
                sell_order_id=trade.sell_order_id,
                price=trade.price,
                quantity=trade.quantity,
                timestamp=trade.timestamp,
            )

            db.merge(record)

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def update_order_remaining_quantity(order: Order) -> None:
    """Update the remaining quantity of an existing order."""
    db: Session = SessionLocal()

    try:
        record = db.get(OrderRecord, order.order_id)

        if record is not None:
            record.remaining_quantity = (
                order.remaining_quantity
                if order.remaining_quantity is not None
                else 0
            )
            db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def get_all_orders() -> list[OrderRecord]:
    """Retrieve all persisted orders."""
    db: Session = SessionLocal()

    try:
        return db.query(OrderRecord).all()
    finally:
        db.close()


def get_all_trades() -> list[TradeRecord]:
    """Retrieve all persisted trades."""
    db: Session = SessionLocal()

    try:
        return db.query(TradeRecord).all()
    finally:
        db.close()

def order_id_exists(order_id: str) -> bool:
    """Check whether an order ID already exists in the database."""
    db: Session = SessionLocal()

    try:
        return db.get(OrderRecord, order_id) is not None
    finally:
        db.close()

def get_user_trades(user_id: int) -> list[dict]:
    """Retrieve trades involving a specific user's orders."""
    db: Session = SessionLocal()

    buy_order = aliased(OrderRecord)
    sell_order = aliased(OrderRecord)

    try:
        records = (
            db.query(
                TradeRecord,
                buy_order.user_id,
                sell_order.user_id,
            )
            .join(
                buy_order,
                TradeRecord.buy_order_id == buy_order.order_id,
            )
            .join(
                sell_order,
                TradeRecord.sell_order_id == sell_order.order_id,
            )
            .filter(
                or_(
                    buy_order.user_id == user_id,
                    sell_order.user_id == user_id,
                )
            )
            .order_by(TradeRecord.timestamp.desc())
            .all()
        )

        return [
            {
                "trade_id": trade.trade_id,
                "side": (
                    "BOTH"
                    if buy_user_id == user_id
                    and sell_user_id == user_id
                    else "BUY"
                    if buy_user_id == user_id
                    else "SELL"
                ),
                "price": trade.price,
                "quantity": trade.quantity,
                "timestamp": trade.timestamp,
                "buy_order_id": trade.buy_order_id,
                "sell_order_id": trade.sell_order_id,
            }
            for trade, buy_user_id, sell_user_id in records
        ]

    finally:
        db.close()