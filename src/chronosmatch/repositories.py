"""Database repository functions for ChronosMatch order and trade persistence."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from .database import SessionLocal
from .db_models import OrderRecord, TradeRecord
from .models import Order, Trade


def save_order(order: Order) -> None:
    """Save or update an order in PostgreSQL."""
    db: Session = SessionLocal()

    try:
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