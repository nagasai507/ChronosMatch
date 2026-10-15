"""Connect the asynchronous market simulator to the binary ring buffer."""

import time
from dataclasses import dataclass

from .market_simulator import MarketSimulator
from .models import Order, OrderSide
from .ring_buffer import BinaryOrder, RingBuffer


@dataclass(frozen=True)
class FirehoseStats:
    """Report how many orders were generated and written."""

    generated: int
    successful_writes: int
    buffer_full: int


def convert_to_binary_order(order: Order) -> BinaryOrder:
    """Convert a simulator Order into the ring buffer's binary format."""
# SIM-1 becomes 1, SIM-2 becomes 2, and so on.
    prefix = "SIM-"
    if not order.order_id.startswith(prefix):
        raise ValueError("Expected a simulator order ID such as SIM-1")

    numeric_id = order.order_id[len(prefix):]
    if not numeric_id.isdigit():
        raise ValueError("Simulator order ID must end with a number")

    order_id = int(numeric_id)
    # The binary format uses 0 for BUY and 1 for SELL.
    side = 0 if order.side == OrderSide.BUY else 1

    return BinaryOrder(
        order_id=order_id,
        side=side,
        price=order.price,
        quantity=order.quantity,
        timestamp_ns=time.perf_counter_ns(),
    )


async def write_orders_to_buffer(
    simulator: MarketSimulator,
    buffer: RingBuffer,
    count: int,
    batch_size: int = 64,
) -> FirehoseStats:
    """Generate orders and write them in batches.

    Orders that cannot fit in the buffer are counted as rejected.
    The function does not retry rejected orders.
    """

    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count must be an integer")
    if count < 0:
        raise ValueError("count must not be negative")

    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise TypeError("batch_size must be an integer")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    generated = 0
    successful_writes = 0
    buffer_full = 0
    batch = []

    async for order in simulator.generate_orders(count=count):
        batch.append(convert_to_binary_order(order))
        generated += 1

        if len(batch) >= batch_size:
            written = buffer.write_many(batch)
            successful_writes += written
            buffer_full += len(batch) - written
            batch.clear()

    # Process any remaining orders.
    if batch:
        written = buffer.write_many(batch)
        successful_writes += written
        buffer_full += len(batch) - written

    return FirehoseStats(
        generated=generated,
        successful_writes=successful_writes,
        buffer_full=buffer_full,
    )
