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
) -> FirehoseStats:
    """Generate orders and write them to the ring buffer."""

    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count must be an integer")

    if count < 0:
        raise ValueError("count must not be negative")

    generated = 0
    successful_writes = 0
    buffer_full = 0

    async for order in simulator.generate_orders(count=count):
        generated += 1
        binary_order = convert_to_binary_order(order)

        if buffer.write(binary_order):
            successful_writes += 1
        else:
            buffer_full += 1

    return FirehoseStats(
        generated=generated,
        successful_writes=successful_writes,
        buffer_full=buffer_full,
    )