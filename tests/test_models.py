import pytest

from chronosmatch.models import Order, OrderSide, Trade


def test_order_initializes_remaining_quantity() -> None:
    order = Order(order_id="O-1", side=OrderSide.BUY, price=100, quantity=5)
    assert order.remaining_quantity == 5


def test_order_rejects_non_positive_price() -> None:
    with pytest.raises(ValueError, match="price"):
        Order(order_id="O-1", side=OrderSide.BUY, price=0, quantity=5)


def test_order_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        Order(order_id="O-1", side=OrderSide.BUY, price=100, quantity=0)


def test_trade_requires_positive_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        Trade(
            trade_id="T-1",
            buy_order_id="B-1",
            sell_order_id="S-1",
            price=100,
            quantity=0,
        )
