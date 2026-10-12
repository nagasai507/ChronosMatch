import asyncio
import time

from chronosmatch.market_simulator import MarketSimulator


async def benchmark():
    simulator = MarketSimulator(seed=42)
    count = 100_000

    start = time.perf_counter_ns()

    generated = 0
    async for _ in simulator.generate_orders(count=count):
        generated += 1

    end = time.perf_counter_ns()

    elapsed_ns = end - start
    elapsed_seconds = elapsed_ns / 1_000_000_000
    throughput = generated / elapsed_seconds

    print(f"Generated orders: {generated}")
    print(f"Elapsed time: {elapsed_seconds:.6f} seconds")
    print(f"Throughput: {throughput:.2f} orders/second")


if __name__ == "__main__":
    asyncio.run(benchmark())