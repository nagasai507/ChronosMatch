"""Tests for the market simulator and ring buffer integration."""

import asyncio

from chronosmatch.market_firehose import (
    convert_to_binary_order,
    write_orders_to_buffer,
)
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.models import Order, OrderSide
from chronosmatch.ring_buffer import BinaryOrder, RingBuffer


def test_convert_simulator_order_to_binary_order():
    order = Order(
        order_id="SIM-1",
        side=OrderSide.BUY,
        price=100,
        quantity=5,
        timestamp=0,
    )

    binary_order = convert_to_binary_order(order)

    assert isinstance(binary_order, BinaryOrder)
    assert binary_order.order_id == 1
    assert binary_order.side == 0
    assert binary_order.price == 100
    assert binary_order.quantity == 5
    assert binary_order.timestamp_ns > 0


def test_firehose_writes_all_orders_when_buffer_has_space():
    async def run_test():
        buffer = RingBuffer(capacity=10)
        try:
            stats = await write_orders_to_buffer(
                MarketSimulator(seed=42), buffer, count=5
            )

            assert stats.generated == 5
            assert stats.successful_writes == 5
            assert stats.buffer_full == 0
            assert len(buffer) == 5
        finally:
            buffer.close()
            buffer.unlink()

    asyncio.run(run_test())


def test_firehose_handles_full_buffer():
    async def run_test():
        buffer = RingBuffer(capacity=2)
        try:
            stats = await write_orders_to_buffer(
                MarketSimulator(seed=42), buffer, count=5
            )

            assert stats.generated == 5
            assert stats.successful_writes == 2
            assert stats.buffer_full == 3
            assert len(buffer) == 2
        finally:
            buffer.close()
            buffer.unlink()

    asyncio.run(run_test())


def test_firehose_preserves_binary_record_fields():
    async def run_test():
        buffer = RingBuffer(capacity=5)
        try:
            await write_orders_to_buffer(
                MarketSimulator(seed=42), buffer, count=3
            )

            first_order = buffer.read()

            assert first_order is not None
            assert first_order.order_id == 1
            assert first_order.side in (0, 1)
            assert 95 <= first_order.price <= 105
            assert 1 <= first_order.quantity <= 100
            assert first_order.timestamp_ns > 0
        finally:
            buffer.close()
            buffer.unlink()

    asyncio.run(run_test())


def test_firehose_rejects_negative_count():
    async def run_test():
        buffer = RingBuffer(capacity=5)
        try:
            try:
                await write_orders_to_buffer(
                    MarketSimulator(seed=42), buffer, count=-1
                )
            except ValueError as error:
                assert "count" in str(error)
            else:
                raise AssertionError("Expected ValueError for negative count")
        finally:
            buffer.close()
            buffer.unlink()

    asyncio.run(run_test())


def test_firehose_is_compatible_with_batched_simulator_orders():
    async def run_test():
        buffer = RingBuffer(capacity=10)

        try:
            stats = await write_orders_to_buffer(
                MarketSimulator(seed=42),
                buffer,
                count=7,
                batch_size=3,
            )

            assert stats.generated == 7
            assert stats.successful_writes == 7
            assert stats.buffer_full == 0
            assert len(buffer) == 7

            orders = buffer.read_many(7)

            assert len(orders) == 7
            assert [order.order_id for order in orders] == list(range(1, 8))
            assert all(order.side in (0, 1) for order in orders)
            assert all(95 <= order.price <= 105 for order in orders)
            assert all(1 <= order.quantity <= 100 for order in orders)

        finally:
            buffer.close()
            buffer.unlink()

    asyncio.run(run_test())
