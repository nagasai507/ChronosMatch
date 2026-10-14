"""Benchmark shared-memory RingBuffer across two processes."""

import multiprocessing as mp
import queue
import sys
import time
from pathlib import Path

# Make the src-layout package importable when running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chronosmatch.ring_buffer import RingBuffer, BinaryOrder


ORDER_COUNT = 1_000_000
CAPACITY = 1024
TIMEOUT_SECONDS = 120


def make_order(order_id: int) -> BinaryOrder:
    """Create a deterministic order for benchmark validation."""
    return BinaryOrder(
        order_id=order_id,
        side=order_id % 2,
        price=100 + order_id % 100,
        quantity=1 + order_id % 5,
        timestamp_ns=1_000 + order_id,
    )


def producer_worker(name, lock, results):
    """Write orders to the shared-memory ring buffer."""
    buffer = None

    try:
        buffer = RingBuffer(
            CAPACITY,
            name=name,
            lock=lock,
            create=False,
        )

        for order_id in range(1, ORDER_COUNT + 1):
            order = make_order(order_id)
            deadline = time.monotonic() + TIMEOUT_SECONDS

            while not buffer.write(order):
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Producer timed out at order {order_id}"
                    )
                time.sleep(0.00001)

        results.put(("producer_ok", ORDER_COUNT))

    except BaseException as exc:
        results.put(("producer_error", repr(exc)))
        raise

    finally:
        if buffer is not None:
            buffer.close()


def consumer_worker(name, lock, results):
    """Read orders and validate FIFO order and record integrity."""
    buffer = None

    try:
        buffer = RingBuffer(
            CAPACITY,
            name=name,
            lock=lock,
            create=False,
        )

        received = 0

        while received < ORDER_COUNT:
            order = buffer.read()

            if order is None:
                time.sleep(0.00001)
                continue

            expected_id = received + 1

            if order.order_id != expected_id:
                raise AssertionError(
                    f"Expected order {expected_id}, "
                    f"received {order.order_id}"
                )

            expected = make_order(expected_id)

            if order != expected:
                raise AssertionError(
                    f"Record integrity failed for order {expected_id}"
                )

            received += 1

        results.put(("consumer_ok", received))

    except BaseException as exc:
        results.put(("consumer_error", repr(exc)))
        raise

    finally:
        if buffer is not None:
            buffer.close()


def main():
    """Run and report the multiprocess benchmark."""
    ctx = mp.get_context("spawn")
    lock = ctx.Lock()
    results = ctx.Queue()

    owner = RingBuffer(CAPACITY, lock=lock)

    producer = ctx.Process(
        target=producer_worker,
        args=(owner.name, lock, results),
        name="RingBufferProducer",
    )

    consumer = ctx.Process(
        target=consumer_worker,
        args=(owner.name, lock, results),
        name="RingBufferConsumer",
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

        if producer.exitcode != 0:
            raise RuntimeError(
                f"Producer exited with code {producer.exitcode}"
            )

        if consumer.exitcode != 0:
            raise RuntimeError(
                f"Consumer exited with code {consumer.exitcode}"
            )

        messages = []

        for _ in range(2):
            try:
                messages.append(results.get(timeout=10))
            except queue.Empty:
                raise RuntimeError(
                    "A producer/consumer result was not received"
                )

        errors = [
            message for message in messages
            if message[0].endswith("_error")
        ]

        if errors:
            raise RuntimeError(f"Worker error: {errors}")

        expected_messages = {
            ("producer_ok", ORDER_COUNT),
            ("consumer_ok", ORDER_COUNT),
        }

        if set(messages) != expected_messages:
            raise AssertionError(
                f"Unexpected worker results: {messages}"
            )

        elapsed = time.perf_counter() - start
        throughput = ORDER_COUNT / elapsed if elapsed else 0

        print("\nShared-Memory Ring Buffer Benchmark")
        print("=" * 42)
        print(f"Orders transferred : {ORDER_COUNT:,}")
        print(f"Elapsed time       : {elapsed:.3f} seconds")
        print(f"Throughput         : {throughput:,.0f} orders/second")
        print("FIFO ordering      : PASSED")
        print("Record integrity   : PASSED")
        print("Producer process   : PASSED")
        print("Consumer process   : PASSED")

    finally:
        for process in (producer, consumer):
            if process.is_alive():
                process.terminate()
                process.join()

        owner.close()
        owner.unlink()
        results.close()
        results.join_thread()


if __name__ == "__main__":
    mp.freeze_support()
    main()