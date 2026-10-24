import pytest

from chronosmatch.models import Order, OrderSide, Trade


def make_order(**overrides):
    data = {
        "order_id": "O-1",
        "side": OrderSide.BUY,
        "price": 100,
        "quantity": 5,
        "timestamp": 0,
    }
    data.update(overrides)
    return Order(**data)


def make_trade(**overrides):
    data = {
        "trade_id": "T-1",
        "buy_order_id": "B-1",
        "sell_order_id": "S-1",
        "price": 100,
        "quantity": 5,
        "timestamp": 0,
    }
    data.update(overrides)
    return Trade(**data)


def test_order_initializes_remaining_quantity():
    order = make_order()
    assert order.remaining_quantity == 5


def test_order_accepts_explicit_remaining_quantity():
    order = make_order(remaining_quantity=3)
    assert order.remaining_quantity == 3


@pytest.mark.parametrize("price", [0, -1])
def test_order_rejects_non_positive_price(price):
    with pytest.raises(ValueError, match="price"):
        make_order(price=price)


@pytest.mark.parametrize("quantity", [0, -1])
def test_order_rejects_non_positive_quantity(quantity):
    with pytest.raises(ValueError, match="quantity"):
        make_order(quantity=quantity)


@pytest.mark.parametrize("order_id", ["", "   "])
def test_order_rejects_empty_id(order_id):
    with pytest.raises(ValueError, match="order_id"):
        make_order(order_id=order_id)


def test_order_rejects_invalid_side():
    with pytest.raises(TypeError, match="side"):
        make_order(side="BUY")


def test_order_rejects_negative_timestamp():
    with pytest.raises(ValueError, match="timestamp"):
        make_order(timestamp=-1)


@pytest.mark.parametrize("remaining", [-1, 6])
def test_order_rejects_invalid_remaining_quantity(remaining):
    with pytest.raises(ValueError, match="remaining_quantity"):
        make_order(remaining_quantity=remaining)


def test_order_accepts_zero_remaining_quantity():
    order = make_order(remaining_quantity=0)
    assert order.remaining_quantity == 0


def test_trade_rejects_empty_trade_id():
    with pytest.raises(ValueError, match="trade_id"):
        make_trade(trade_id="")


@pytest.mark.parametrize(
    "field,value",
    [
        ("buy_order_id", ""),
        ("sell_order_id", ""),
    ],
)
def test_trade_rejects_empty_order_ids(field, value):
    with pytest.raises(ValueError, match="trade order IDs"):
        make_trade(**{field: value})


@pytest.mark.parametrize("price", [0, -1])
def test_trade_rejects_non_positive_price(price):
    with pytest.raises(ValueError, match="price"):
        make_trade(price=price)


@pytest.mark.parametrize("quantity", [0, -1])
def test_trade_rejects_non_positive_quantity(quantity):
    with pytest.raises(ValueError, match="quantity"):
        make_trade(quantity=quantity)


def test_trade_rejects_negative_timestamp():
    with pytest.raises(ValueError, match="timestamp"):
        make_trade(timestamp=-1)


def test_trade_is_immutable():
    trade = make_trade()

    with pytest.raises(AttributeError):
        trade.price = 200


@pytest.mark.parametrize("timestamp", [1.5, "100", True])
def test_order_rejects_invalid_timestamp_type(timestamp):
    with pytest.raises(TypeError, match="timestamp"):
        make_order(timestamp=timestamp)


@pytest.mark.parametrize("timestamp", [1.5, "100", True])
def test_trade_rejects_invalid_timestamp_type(timestamp):
    with pytest.raises(TypeError, match="timestamp"):
        make_trade(timestamp=timestamp)


@pytest.mark.parametrize("remaining", [2.5, "2", True])
def test_order_rejects_invalid_remaining_quantity_type(remaining):
    with pytest.raises(TypeError, match="remaining_quantity"):
        make_order(remaining_quantity=remaining)


@pytest.mark.parametrize("order_id", [123, None, True])
def test_order_rejects_invalid_id_type(order_id):
    with pytest.raises(TypeError, match="order_id"):
        make_order(order_id=order_id)


@pytest.mark.parametrize("field", ["trade_id", "buy_order_id", "sell_order_id"])
def test_trade_rejects_invalid_id_type(field):
    with pytest.raises(TypeError):
        make_trade(**{field: 123})


@pytest.mark.parametrize("value", ["100", 1.5, True])
@pytest.mark.parametrize("field", ["price", "quantity"])
def test_order_rejects_invalid_numeric_field_types(field, value):
    with pytest.raises(TypeError, match=field):
        make_order(**{field: value})


@pytest.mark.parametrize("value", ["100", 1.5, True])
@pytest.mark.parametrize("field", ["price", "quantity"])
def test_trade_rejects_invalid_numeric_field_types(field, value):
    with pytest.raises(TypeError, match=field):
        make_trade(**{field: value})


def test_order_accepts_minimum_valid_values():
    order = make_order(price=1, quantity=1, timestamp=0)
    assert order.price == 1
    assert order.quantity == 1
    assert order.remaining_quantity == 1


def test_trade_accepts_minimum_valid_values():
    trade = make_trade(price=1, quantity=1, timestamp=0)
    assert trade.price == 1
    assert trade.quantity == 1
    assert trade.timestamp == 0


def test_order_accepts_remaining_quantity_equal_to_quantity():
    order = make_order(quantity=5, remaining_quantity=5)
    assert order.remaining_quantity == order.quantity