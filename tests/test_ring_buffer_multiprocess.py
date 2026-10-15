
import multiprocessing as mp
import time

from src.chronosmatch.ring_buffer import (
    BinaryOrder,
    RECORD_SIZE,
    HEADER_SIZE,
    RingBuffer,
)


ORDER_COUNT = 1_000
CAPACITY = 64
TIMEOUT_SECONDS = 30


def make_order(order_id: int) -> BinaryOrder:
    """Create a deterministic order so every field can be verified."""
    return BinaryOrder(
        order_id=order_id,
        side=order_id % 2,
        price=100 + order_id % 10,
        quantity=1 + order_id % 5,
        timestamp_ns=1_000 + order_id,
    )


def producer_worker(name, lock, result_queue):
    """Attach to shared memory and publish orders."""
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
                time.sleep(0.0001)

        result_queue.put(("producer_ok", ORDER_COUNT))

    except Exception as exc:
        result_queue.put(("producer_error", repr(exc)))
        raise

    finally:
        if buffer is not None:
            buffer.close()


def consumer_worker(name, lock, result_queue):
    """Attach independently and validate every received order."""
    buffer = None

    try:
        buffer = RingBuffer(
            CAPACITY,
            name=name,
            lock=lock,
            create=False,
        )

        received = 0
        deadline = time.monotonic() + TIMEOUT_SECONDS

        while received < ORDER_COUNT:
            order = buffer.read()

            if order is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Consumer timed out after {received} orders"
                    )
                time.sleep(0.0001)
                continue

            expected = make_order(received + 1)

            if order != expected:
                raise AssertionError(
                    f"Order mismatch at position {received + 1}: "
                    f"expected {expected}, got {order}"
                )

            received += 1

        result_queue.put(("consumer_ok", received))

    except Exception as exc:
        result_queue.put(("consumer_error", repr(exc)))
        raise

    finally:
        if buffer is not None:
            buffer.close()


def test_ring_buffer_transfers_orders_between_processes():
    """Verify cross-process transfer, FIFO order and record integrity."""
    ctx = mp.get_context("spawn")
    lock = ctx.Lock()
    results = ctx.Queue()

    owner = RingBuffer(CAPACITY, lock=lock)
    consumer = ctx.Process(
        target=consumer_worker,
        args=(owner.name, lock, results),
    )
    producer = ctx.Process(
        target=producer_worker,
        args=(owner.name, lock, results),
    )

    try:
        assert owner._shm.size == HEADER_SIZE + CAPACITY * RECORD_SIZE

        consumer.start()
        producer.start()

        producer.join(TIMEOUT_SECONDS)
        consumer.join(TIMEOUT_SECONDS)

        for process in (producer, consumer):
            if process.is_alive():
                process.terminate()
                process.join(5)

        assert not producer.is_alive(), "Producer process hung"
        assert not consumer.is_alive(), "Consumer process hung"
        assert producer.exitcode == 0
        assert consumer.exitcode == 0

        messages = [results.get(timeout=5) for _ in range(2)]

        assert ("producer_ok", ORDER_COUNT) in messages
        assert ("consumer_ok", ORDER_COUNT) in messages
        assert len(owner) == 0

    finally:
        for process in (producer, consumer):
            if process.is_alive():
                process.terminate()
                process.join(5)

        owner.close()
        owner.unlink()
        results.close()
        results.join_thread()
