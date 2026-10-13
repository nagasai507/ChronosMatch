"""Benchmark successful market-order writes to the ring buffer."""

import asyncio
import time

from chronosmatch.market_firehose import write_orders_to_buffer
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.ring_buffer import RingBuffer


async def benchmark() -> None:
    count = 100_000

    # Make the buffer large enough to hold every generated order.
    buffer = RingBuffer(capacity=count)

    try:
        simulator = MarketSimulator(seed=42)

        start_ns = time.perf_counter_ns()

        stats = await write_orders_to_buffer(
            simulator=simulator,
            buffer=buffer,
            count=count,
        )

        end_ns = time.perf_counter_ns()

        elapsed_ns = end_ns - start_ns
        elapsed_seconds = elapsed_ns / 1_000_000_000

        throughput = (
            stats.successful_writes / elapsed_seconds
            if elapsed_seconds > 0
            else 0.0
        )

        print(f"Generated orders: {stats.generated}")
        print(f"Successful writes: {stats.successful_writes}")
        print(f"Buffer-full rejections: {stats.buffer_full}")
        print(f"Elapsed time: {elapsed_seconds:.6f} seconds")
        print(f"Successful writes per second: {throughput:.2f}")

    finally:
        buffer.close()
        buffer.unlink()


if __name__ == "__main__":
    asyncio.run(benchmark())