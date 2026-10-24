"""Benchmark market simulator generation and ring-buffer throughput."""

import asyncio
import time

from chronosmatch.market_firehose import write_orders_to_buffer
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.ring_buffer import RingBuffer


async def benchmark() -> None:
    count = 100_000

    # ---------------------------------------------------------
    # Benchmark 1: Simulator generation only
    # ---------------------------------------------------------
    simulator = MarketSimulator(seed=42)

    start_ns = time.perf_counter_ns()

    orders = [
        order
        async for order in simulator.generate_orders(count=count)
    ]

    end_ns = time.perf_counter_ns()

    generation_seconds = (end_ns - start_ns) / 1_000_000_000

    generation_throughput = (
        len(orders) / generation_seconds
        if generation_seconds > 0
        else 0.0
    )

    print("=== Simulator Generation Benchmark ===")
    print(f"Generated orders: {len(orders)}")
    print(f"Elapsed time: {generation_seconds:.6f} seconds")
    print(f"Orders per second: {generation_throughput:.2f}")

    # ---------------------------------------------------------
    # Benchmark 2: Ring-buffer write throughput
    # ---------------------------------------------------------
    buffer = RingBuffer(capacity=count)

    try:
        simulator = MarketSimulator(seed=42)

        start_ns = time.perf_counter_ns()

        stats = await write_orders_to_buffer(
            simulator=simulator,
            buffer=buffer,
            count=count,
            batch_size=64,
        )

        end_ns = time.perf_counter_ns()

        firehose_seconds = (end_ns - start_ns) / 1_000_000_000

        firehose_throughput = (
            stats.successful_writes / firehose_seconds
            if firehose_seconds > 0
            else 0.0
        )

        print()
        print("=== Simulator + Ring Buffer Benchmark ===")
        print(f"Generated orders: {stats.generated}")
        print(f"Successful writes: {stats.successful_writes}")
        print(f"Buffer-full rejections: {stats.buffer_full}")
        print(f"Elapsed time: {firehose_seconds:.6f} seconds")
        print(f"Successful writes per second: {firehose_throughput:.2f}")

    finally:
        buffer.close()
        buffer.unlink()


if __name__ == "__main__":
    asyncio.run(benchmark())