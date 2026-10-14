
"""Unit tests for the ChronosMatch matching engine."""

import pytest

from chronosmatch.models import Order, OrderSide
from chronosmatch.matching_engine import MatchingEngine


def make_order(order_id, side, price, quantity, timestamp=0):
    """Create an order for testing."""
    return Order(
        order_id=order_id,
        side=side,
        price=price,
        quantity=quantity,
        timestamp=timestamp,
    )


def test_fifo_priority_at_same_price():
    """The earliest resting order at the same price fills first."""
    engine = MatchingEngine()

    engine.submit_order(make_order("S1", OrderSide.SELL, 100, 3, 1))
    engine.submit_order(make_order("S2", OrderSide.SELL, 100, 5, 2))

    trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 100, 3, 3)
    )

    assert len(trades) == 1
    assert trades[0].sell_order_id == "S1"
    assert trades[0].quantity == 3

    best_ask = engine.order_book.get_best_ask()
    assert best_ask is not None
    assert best_ask.order_id == "S2"
    assert best_ask.remaining_quantity == 5


def test_one_order_matches_multiple_resting_orders():
    """A large incoming order can consume multiple resting orders."""
    engine = MatchingEngine()

    engine.submit_order(make_order("S1", OrderSide.SELL, 100, 2, 1))
    engine.submit_order(make_order("S2", OrderSide.SELL, 101, 3, 2))

    trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 101, 5, 3)
    )

    assert len(trades) == 2
    assert trades[0].sell_order_id == "S1"
    assert trades[0].price == 100
    assert trades[0].quantity == 2

    assert trades[1].sell_order_id == "S2"
    assert trades[1].price == 101
    assert trades[1].quantity == 3

    assert all(trade.buy_order_id == "B1" for trade in trades)
    assert engine.order_book.get_best_ask() is None


def test_best_price_has_priority_before_fifo():
    """A better-priced resting order fills before a worse-priced order."""
    engine = MatchingEngine()

    engine.submit_order(make_order("S1", OrderSide.SELL, 102, 2, 1))
    engine.submit_order(make_order("S2", OrderSide.SELL, 100, 2, 2))

    trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 102, 2, 3)
    )

    assert len(trades) == 1
    assert trades[0].sell_order_id == "S2"
    assert trades[0].price == 100
    assert trades[0].quantity == 2

    best_ask = engine.order_book.get_best_ask()
    assert best_ask is not None
    assert best_ask.order_id == "S1"


def test_trade_ids_are_unique():
    """Each generated trade receives a unique ID."""
    engine = MatchingEngine()

    engine.submit_order(make_order("S1", OrderSide.SELL, 100, 2, 1))
    engine.submit_order(make_order("S2", OrderSide.SELL, 100, 2, 2))

    trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 100, 4, 3)
    )

    trade_ids = [trade.trade_id for trade in trades]

    assert len(trade_ids) == 2
    assert len(set(trade_ids)) == 2


def test_trade_history_records_all_executions():
    """Engine history contains trades created by each submission."""
    engine = MatchingEngine()

    engine.submit_order(make_order("S1", OrderSide.SELL, 100, 2, 1))
    first_trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 100, 2, 2)
    )

    engine.submit_order(make_order("S2", OrderSide.SELL, 101, 3, 3))
    second_trades = engine.submit_order(
        make_order("B2", OrderSide.BUY, 101, 3, 4)
    )

    assert len(first_trades) == 1
    assert len(second_trades) == 1
    assert len(engine.trades) == 2
    assert engine.trades == first_trades + second_trades


def test_partial_fill_across_multiple_orders_preserves_remainders():
    """Partial execution preserves any unmatched quantities."""
    engine = MatchingEngine()

    engine.submit_order(make_order("S1", OrderSide.SELL, 100, 2, 1))
    engine.submit_order(make_order("S2", OrderSide.SELL, 100, 5, 2))

    trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 100, 4, 3)
    )

    assert len(trades) == 2
    assert [trade.quantity for trade in trades] == [2, 2]

    best_ask = engine.order_book.get_best_ask()
    assert best_ask is not None
    assert best_ask.order_id == "S2"
    assert best_ask.remaining_quantity == 3


def test_unmatched_incoming_quantity_is_added_to_book():
    """Any quantity left after matching becomes a resting order."""
    engine = MatchingEngine()

    engine.submit_order(make_order("S1", OrderSide.SELL, 100, 2, 1))

    trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 100, 5, 2)
    )

    assert len(trades) == 1
    assert trades[0].quantity == 2

    best_bid = engine.order_book.get_best_bid()
    assert best_bid is not None
    assert best_bid.order_id == "B1"
    assert best_bid.remaining_quantity == 3


def test_exact_fill_removes_fully_filled_orders():
    """An exact match leaves neither order resting in the book."""
    engine = MatchingEngine()

    sell_order = make_order("S1", OrderSide.SELL, 100, 5, 1)
    buy_order = make_order("B1", OrderSide.BUY, 100, 5, 2)

    engine.submit_order(sell_order)
    trades = engine.submit_order(buy_order)

    assert len(trades) == 1
    assert trades[0].quantity == 5
    assert sell_order.remaining_quantity == 0
    assert buy_order.remaining_quantity == 0
    assert engine.order_book.get_best_ask() is None
    assert engine.order_book.get_best_bid() is None


def test_non_crossing_orders_remain_unmatched():
    """Orders that do not cross remain in the book without a trade."""
    engine = MatchingEngine()

    sell_order = make_order("S1", OrderSide.SELL, 105, 3, 1)
    buy_order = make_order("B1", OrderSide.BUY, 100, 4, 2)

    assert engine.submit_order(sell_order) == []
    assert engine.submit_order(buy_order) == []

    best_ask = engine.order_book.get_best_ask()
    best_bid = engine.order_book.get_best_bid()

    assert best_ask is sell_order
    assert best_bid is buy_order
    assert sell_order.remaining_quantity == 3
    assert buy_order.remaining_quantity == 4
    assert engine.trades == []


def test_sell_order_matches_multiple_bids_in_price_priority():
    """An incoming sell consumes the highest-priced bids first."""
    engine = MatchingEngine()

    lower_bid = make_order("B1", OrderSide.BUY, 100, 3, 1)
    higher_bid = make_order("B2", OrderSide.BUY, 101, 2, 2)

    engine.submit_order(lower_bid)
    engine.submit_order(higher_bid)

    incoming_sell = make_order("S1", OrderSide.SELL, 100, 4, 3)
    trades = engine.submit_order(incoming_sell)

    assert len(trades) == 2
    assert trades[0].buy_order_id == "B2"
    assert trades[0].price == 101
    assert trades[0].quantity == 2

    assert trades[1].buy_order_id == "B1"
    assert trades[1].price == 100
    assert trades[1].quantity == 2

    assert higher_bid.remaining_quantity == 0
    assert lower_bid.remaining_quantity == 1
    assert incoming_sell.remaining_quantity == 0

    best_bid = engine.order_book.get_best_bid()
    assert best_bid is lower_bid
    assert best_bid.remaining_quantity == 1


def test_sell_order_trade_uses_resting_bid_price():
    """An incoming sell executes at the resting buy order's price."""
    engine = MatchingEngine()

    resting_buy = make_order("B1", OrderSide.BUY, 105, 3, 1)
    incoming_sell = make_order("S1", OrderSide.SELL, 100, 2, 2)

    engine.submit_order(resting_buy)
    trades = engine.submit_order(incoming_sell)

    assert len(trades) == 1
    assert trades[0].buy_order_id == "B1"
    assert trades[0].sell_order_id == "S1"
    assert trades[0].price == 105
    assert trades[0].quantity == 2
    assert resting_buy.remaining_quantity == 1
    assert incoming_sell.remaining_quantity == 0
