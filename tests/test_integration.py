
"""Integration tests for the ChronosMatch trading engine."""

import pytest
import asyncio
from chronosmatch.ring_buffer import BinaryOrder, RingBuffer
from chronosmatch.market_firehose import write_orders_to_buffer
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.ring_buffer import RingBuffer

from chronosmatch.models import Order, OrderSide
from chronosmatch.matching_engine import MatchingEngine


def make_order(order_id, side, price, quantity, timestamp=0):
    return Order(
        order_id=order_id,
        side=side,
        price=price,
        quantity=quantity,
        timestamp=timestamp,
    )


def test_buy_and_sell_orders_can_match():
    engine = MatchingEngine()

    engine.submit_order(
        make_order("B1", OrderSide.BUY, 100, 5, timestamp=1)
    )
    trades = engine.submit_order(
        make_order("S1", OrderSide.SELL, 100, 5, timestamp=2)
    )

    assert len(trades) == 1
    assert trades[0].buy_order_id == "B1"
    assert trades[0].sell_order_id == "S1"
    assert trades[0].quantity == 5


def test_non_matching_orders_remain_open():
    engine = MatchingEngine()

    buy_trades = engine.submit_order(
        make_order("B1", OrderSide.BUY, 95, 5, timestamp=1)
    )
    sell_trades = engine.submit_order(
        make_order("S1", OrderSide.SELL, 100, 5, timestamp=2)
    )

    assert buy_trades == []
    assert sell_trades == []
    assert engine.order_book.get_best_bid().order_id == "B1"
    assert engine.order_book.get_best_ask().order_id == "S1"


def test_partial_fill_preserves_remaining_quantity():
    engine = MatchingEngine()

    engine.submit_order(
        make_order("B1", OrderSide.BUY, 100, 10, timestamp=1)
    )
    trades = engine.submit_order(
        make_order("S1", OrderSide.SELL, 100, 4, timestamp=2)
    )

    assert len(trades) == 1
    assert trades[0].quantity == 4

    best_bid = engine.order_book.get_best_bid()
    assert best_bid is not None
    assert best_bid.order_id == "B1"
    assert best_bid.remaining_quantity == 6

def test_simulator_firehose_ring_buffer_to_matching_engine():
    async def run_test():
        buffer = RingBuffer(capacity=10)
        try:
            stats = await write_orders_to_buffer(
                MarketSimulator(seed=42),
                buffer,
                count=2,
            )

            assert stats.generated == 2
            assert stats.successful_writes == 2
            assert stats.buffer_full == 0

            binary_orders = buffer.read_many(10)
            assert len(binary_orders) == 2

            engine = MatchingEngine()

            for binary_order in binary_orders:
                order = Order(
                    order_id=f"SIM-{binary_order.order_id}",
                    side=(
                        OrderSide.BUY
                        if binary_order.side == 0
                        else OrderSide.SELL
                    ),
                    price=binary_order.price,
                    quantity=binary_order.quantity,
                    timestamp=binary_order.order_id,
                )
                engine.submit_order(order)

            # Every decoded order must be accepted by the engine.
            assert len(engine._seen_order_ids) == 2
        finally:
            buffer.close()
            buffer.unlink()

    asyncio.run(run_test())

def test_ring_buffer_orders_produce_a_real_trade():
    from chronosmatch.ring_buffer import BinaryOrder, RingBuffer

    buffer = RingBuffer(capacity=2)
    try:
        # BUY and SELL orders cross at price 100.
        assert buffer.write_many([
            BinaryOrder(1, 0, 100, 5, 1),
            BinaryOrder(2, 1, 100, 3, 2),
        ]) == 2

        binary_orders = buffer.read_many(2)
        assert len(binary_orders) == 2

        engine = MatchingEngine()
        generated_trades = []

        for binary_order in binary_orders:
            order = Order(
                order_id=f"PIPE-{binary_order.order_id}",
                side=(
                    OrderSide.BUY
                    if binary_order.side == 0
                    else OrderSide.SELL
                ),
                price=binary_order.price,
                quantity=binary_order.quantity,
                timestamp=binary_order.timestamp_ns,
            )
            generated_trades.extend(engine.submit_order(order))

        assert len(generated_trades) == 1

        trade = generated_trades[0]
        assert trade.buy_order_id == "PIPE-1"
        assert trade.sell_order_id == "PIPE-2"
        assert trade.price == 100
        assert trade.quantity == 3

        # The BUY order has 2 units remaining.
        best_bid = engine.order_book.get_best_bid()
        assert best_bid is not None
        assert best_bid.order_id == "PIPE-1"
        assert best_bid.remaining_quantity == 2

        # The fully filled SELL order is removed.
        assert engine.order_book.get_best_ask() is None
    finally:
        buffer.close()
        buffer.unlink()
