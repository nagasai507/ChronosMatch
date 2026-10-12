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


def test_order_rejects_non_integer_price() -> None:
    with pytest.raises((TypeError, ValueError)):
        Order(
            order_id="O-1",
            side=OrderSide.BUY,
            price=100.5,
            quantity=5,
        )


def test_order_rejects_non_integer_quantity() -> None:
    with pytest.raises((TypeError, ValueError)):
        Order(
            order_id="O-1",
            side=OrderSide.BUY,
            price=100,
            quantity=5.5,
        )


def test_order_rejects_invalid_remaining_quantity() -> None:
    with pytest.raises(ValueError, match="remaining_quantity"):
        Order(
            order_id="O-1",
            side=OrderSide.BUY,
            price=100,
            quantity=5,
            remaining_quantity=6,
        )


def test_order_rejects_negative_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        Order(
            order_id="O-1",
            side=OrderSide.BUY,
            price=100,
            quantity=5,
            timestamp=-1,
        )


def test_order_rejects_empty_order_id() -> None:
    with pytest.raises(ValueError, match="order_id"):
        Order(
            order_id="",
            side=OrderSide.BUY,
            price=100,
            quantity=5,
        )


def test_order_accepts_sell_side() -> None:
    order = Order(
        order_id="O-2",
        side=OrderSide.SELL,
        price=100,
        quantity=5,
    )

    assert order.side == OrderSide.SELL


def test_trade_initializes_correctly() -> None:
    trade = Trade(
        trade_id="T-1",
        buy_order_id="B-1",
        sell_order_id="S-1",
        price=100,
        quantity=5,
    )

    assert trade.trade_id == "T-1"
    assert trade.buy_order_id == "B-1"
    assert trade.sell_order_id == "S-1"
    assert trade.price == 100
    assert trade.quantity == 5
    assert trade.timestamp == 0


def test_trade_rejects_non_positive_price() -> None:
    with pytest.raises(ValueError, match="price"):
        Trade(
            trade_id="T-1",
            buy_order_id="B-1",
            sell_order_id="S-1",
            price=0,
            quantity=5,
        )


def test_trade_rejects_non_integer_price() -> None:
    with pytest.raises((TypeError, ValueError)):
        Trade(
            trade_id="T-1",
            buy_order_id="B-1",
            sell_order_id="S-1",
            price=100.5,
            quantity=5,
        )


def test_trade_rejects_non_integer_quantity() -> None:
    with pytest.raises((TypeError, ValueError)):
        Trade(
            trade_id="T-1",
            buy_order_id="B-1",
            sell_order_id="S-1",
            price=100,
            quantity=5.5,
        )