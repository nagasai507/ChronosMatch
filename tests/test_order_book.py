from chronosmatch.order_book import OrderBook
from chronosmatch.models import Order, OrderSide


def make_order(order_id, side, price, timestamp, quantity=10):
    return Order(
        order_id=order_id,
        side=side,
        price=price,
        quantity=quantity,
        timestamp=timestamp,
    )


def test_empty_book():
    book = OrderBook()
    assert book.get_best_bid() is None
    assert book.get_best_ask() is None


def test_zero_remaining_quantity_order_is_not_added():
    book = OrderBook()
    order = make_order("b1", OrderSide.BUY, 100, 1)
    order.remaining_quantity = 0

    book.add_order(order)

    assert book.get_best_bid() is None


def test_best_bid_is_highest_price():
    book = OrderBook()
    book.add_order(make_order("b1", OrderSide.BUY, 100, 1))
    book.add_order(make_order("b2", OrderSide.BUY, 105, 2))

    assert book.get_best_bid().order_id == "b2"


def test_best_ask_is_lowest_price():
    book = OrderBook()
    book.add_order(make_order("s1", OrderSide.SELL, 110, 1))
    book.add_order(make_order("s2", OrderSide.SELL, 108, 2))

    assert book.get_best_ask().order_id == "s2"


def test_fifo_at_same_price():
    book = OrderBook()
    book.add_order(make_order("b1", OrderSide.BUY, 100, 1))
    book.add_order(make_order("b2", OrderSide.BUY, 100, 2))

    assert book.get_best_bid().order_id == "b1"


def test_remove_order():
    book = OrderBook()
    book.add_order(make_order("b1", OrderSide.BUY, 100, 1))

    assert book.remove_order("b1") is True
    assert book.get_best_bid() is None
    assert book.remove_order("unknown") is False


def test_remove_sell_order():
    book = OrderBook()
    book.add_order(make_order("s1", OrderSide.SELL, 110, 1))
    book.add_order(make_order("s2", OrderSide.SELL, 115, 2))

    assert book.get_best_ask().order_id == "s1"

    assert book.remove_order("s1") is True

    assert book.get_best_ask().order_id == "s2"


def test_remove_best_order_reveals_next_best_order():
    book = OrderBook()
    book.add_order(make_order("b1", OrderSide.BUY, 100, 1))
    book.add_order(make_order("b2", OrderSide.BUY, 105, 2))

    assert book.get_best_bid().order_id == "b2"
    assert book.remove_order("b2") is True
    assert book.get_best_bid().order_id == "b1"


def test_buy_fifo_uses_timestamp_at_same_price():
    book = OrderBook()
    book.add_order(make_order("b2", OrderSide.BUY, 100, 2))
    book.add_order(make_order("b1", OrderSide.BUY, 100, 1))

    assert book.get_best_bid().order_id == "b1"


def test_sell_fifo_uses_timestamp_at_same_price():
    book = OrderBook()
    book.add_order(make_order("s2", OrderSide.SELL, 100, 2))
    book.add_order(make_order("s1", OrderSide.SELL, 100, 1))

    assert book.get_best_ask().order_id == "s1"