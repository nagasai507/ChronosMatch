
import tracemalloc

from chronosmatch.ring_buffer import BinaryOrder, RingBuffer


def orders(count):
    for i in range(count):
        yield BinaryOrder(
            order_id=i,
            side=i % 2,
            price=100 + i % 10,
            quantity=1,
            timestamp_ns=i,
        )


def main():
    count = 100_000
    buffer = RingBuffer(capacity=10)

    try:
        tracemalloc.start()
        written = buffer.write_many(orders(count))
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"Orders supplied: {count:,}")
        print(f"Buffer capacity: {buffer.capacity}")
        print(f"Orders written: {written}")
        print(f"Current traced memory: {current / 1024:.1f} KiB")
        print(f"Peak traced memory: {peak / 1024:.1f} KiB")
    finally:
        buffer.close()
        buffer.unlink()


if __name__ == "__main__":
    main()
