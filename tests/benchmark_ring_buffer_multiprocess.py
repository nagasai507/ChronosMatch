
"""Compare individual and batch shared-memory RingBuffer operations."""

import multiprocessing as mp
import queue
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chronosmatch.ring_buffer import BinaryOrder, RingBuffer


ORDER_COUNT = 1_000_000
CAPACITY = 1024
BATCH_SIZE = 64
TIMEOUT_SECONDS = 120
POLL_INTERVAL = 0.00001


def make_order(order_id: int) -> BinaryOrder:
    """Create a deterministic order for benchmark validation."""
    return BinaryOrder(
        order_id=order_id,
        side=order_id % 2,
        price=100 + order_id % 100,
        quantity=1 + order_id % 5,
        timestamp_ns=1_000 + order_id,
    )


def producer_worker(name, lock, results, mode):
    """Produce orders using individual or batch operations."""
    buffer = None

    try:
        buffer = RingBuffer(
            CAPACITY, name=name, lock=lock, create=False
        )

        next_id = 1
        deadline = time.monotonic() + TIMEOUT_SECONDS

        while next_id <= ORDER_COUNT:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Producer timed out at order {next_id}"
                )

            if mode == "individual":
                written = buffer.write(make_order(next_id))

                if written:
                    next_id += 1
                else:
                    time.sleep(POLL_INTERVAL)

            else:
                batch_end = min(
                    next_id + BATCH_SIZE - 1, ORDER_COUNT
                )
                orders = [
                    make_order(order_id)
                    for order_id in range(next_id, batch_end + 1)
                ]

                offset = 0

                while offset < len(orders):
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            f"Batch producer timed out at "
                            f"order {next_id + offset}"
                        )

                    written = buffer.write_many(orders[offset:])

                    if written == 0:
                        time.sleep(POLL_INTERVAL)
                    else:
                        offset += written

                next_id += len(orders)

        results.put(("producer_ok", mode, ORDER_COUNT))

    except BaseException as exc:
        results.put(("producer_error", mode, repr(exc)))
        raise

    finally:
        if buffer is not None:
            buffer.close()


def consumer_worker(name, lock, results, mode):
    """Consume and validate FIFO order and record integrity."""
    buffer = None

    try:
        buffer = RingBuffer(
            CAPACITY, name=name, lock=lock, create=False
        )

        received = 0
        deadline = time.monotonic() + TIMEOUT_SECONDS

        while received < ORDER_COUNT:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Consumer timed out after {received} orders"
                )

            if mode == "individual":
                order = buffer.read()
                orders = [] if order is None else [order]
            else:
                orders = buffer.read_many(BATCH_SIZE)

            if not orders:
                time.sleep(POLL_INTERVAL)
                continue

            for order in orders:
                expected_id = received + 1

                if order.order_id != expected_id:
                    raise AssertionError(
                        f"Expected order {expected_id}, "
                        f"received {order.order_id}"
                    )

                if order != make_order(expected_id):
                    raise AssertionError(
                        f"Record integrity failed for order "
                        f"{expected_id}"
                    )

                received += 1

        results.put(("consumer_ok", mode, received))

    except BaseException as exc:
        results.put(("consumer_error", mode, repr(exc)))
        raise

    finally:
        if buffer is not None:
            buffer.close()


def run_benchmark(mode):
    """Run one producer and one consumer for the selected mode."""
    ctx = mp.get_context("spawn")
    lock = ctx.Lock()
    results = ctx.Queue()
    owner = RingBuffer(CAPACITY, lock=lock)

    producer = ctx.Process(
        target=producer_worker,
        args=(owner.name, lock, results, mode),
        name=f"{mode}-Producer",
    )
    consumer = ctx.Process(
        target=consumer_worker,
        args=(owner.name, lock, results, mode),
        name=f"{mode}-Consumer",
    )

    start = time.perf_counter()

    try:
        consumer.start()
        producer.start()

        producer.join(TIMEOUT_SECONDS + 10)
        consumer.join(TIMEOUT_SECONDS + 10)

        for process in (producer, consumer):
            if process.is_alive():
                process.terminate()
                process.join()

        if producer.exitcode != 0 or consumer.exitcode != 0:
            messages = []
            while True:
                try:
                    messages.append(results.get_nowait())
                except queue.Empty:
                    break

            raise RuntimeError(
                f"{mode} benchmark failed. "
                f"Producer exit={producer.exitcode}, "
                f"consumer exit={consumer.exitcode}; "
                f"messages={messages}"
            )

        messages = [
            results.get(timeout=10),
            results.get(timeout=10),
        ]

        expected = {
            ("producer_ok", mode, ORDER_COUNT),
            ("consumer_ok", mode, ORDER_COUNT),
        }

        if set(messages) != expected:
            raise AssertionError(
                f"Unexpected {mode} results: {messages}"
            )

        elapsed = time.perf_counter() - start
        throughput = ORDER_COUNT / elapsed

        return {
            "mode": mode,
            "elapsed": elapsed,
            "throughput": throughput,
        }

    finally:
        for process in (producer, consumer):
            if process.is_alive():
                process.terminate()
                process.join()

        owner.close()
        owner.unlink()
        results.close()
        results.join_thread()


def main():
    """Compare individual and batch throughput."""
    print("Shared-Memory Ring Buffer Benchmark")
    print("=" * 48)
    print(f"Orders per run : {ORDER_COUNT:,}")
    print(f"Buffer capacity: {CAPACITY:,}")
    print(f"Batch size     : {BATCH_SIZE}")
    print("Running individual mode...")

    individual = run_benchmark("individual")

    print("Running batch mode...")
    batch = run_benchmark("batch")

    improvement = (
        (batch["throughput"] / individual["throughput"]) - 1
    ) * 100

    print("\nResults")
    print("-" * 48)

    for result in (individual, batch):
        print(f"\nMode             : {result['mode']}")
        print(f"Elapsed time     : {result['elapsed']:.3f} seconds")
        print(f"Throughput       : {result['throughput']:,.0f} orders/sec")
        print("FIFO ordering    : PASSED")
        print("Record integrity : PASSED")
        print("Multiprocess run : PASSED")

    print("\nComparison")
    print("-" * 48)
    print(f"Throughput change: {improvement:+.2f}%")

    if improvement > 0:
        print(f"Batch speedup    : {batch['throughput'] / individual['throughput']:.2f}x")
    else:
        print("Batch mode was not faster in this run.")

    print("\nNote: Repeat the benchmark to assess run-to-run variability.")


if __name__ == "__main__":
    mp.freeze_support()
    main()
