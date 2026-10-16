
"""Tests for the shared-memory ring buffer."""

import pytest

from chronosmatch.ring_buffer import (
    RECORD_SIZE,
    BinaryOrder,
    RingBuffer,
)


def make_order(order_id: int) -> BinaryOrder:
    """Create a deterministic test order."""
    return BinaryOrder(
        order_id=order_id,
        side=order_id % 2,
        price=100 + order_id,
        quantity=1 + order_id % 5,
        timestamp_ns=1_000 + order_id,
    )


def test_record_size_and_encoding_round_trip():
    order = make_order(1)

    encoded = RingBuffer.encode(order)

    assert len(encoded) == RECORD_SIZE == 33
    assert RingBuffer.decode(encoded) == order


def test_invalid_side_is_rejected():
    order = BinaryOrder(1, 2, 100, 1, 1000)

    with pytest.raises(ValueError, match="side"):
        RingBuffer.encode(order)


def test_negative_order_id_is_rejected():
    order = BinaryOrder(-1, 0, 100, 1, 1000)

    with pytest.raises(ValueError, match="order_id"):
        RingBuffer.encode(order)


def test_zero_quantity_is_rejected():
    order = BinaryOrder(1, 0, 100, 0, 1000)

    with pytest.raises(ValueError, match="quantity"):
        RingBuffer.encode(order)


def test_decode_rejects_wrong_record_size():
    with pytest.raises(ValueError, match="exactly"):
        RingBuffer.decode(b"short")


def test_empty_buffer_returns_none():
    buffer = RingBuffer(capacity=2)

    try:
        assert buffer.read() is None
        assert len(buffer) == 0
    finally:
        buffer.close()
        buffer.unlink()


def test_full_buffer_rejects_extra_write():
    buffer = RingBuffer(capacity=2)

    try:
        assert buffer.write(make_order(1)) is True
        assert buffer.write(make_order(2)) is True
        assert buffer.write(make_order(3)) is False
        assert len(buffer) == 2
    finally:
        buffer.close()
        buffer.unlink()


def test_fifo_order():
    buffer = RingBuffer(capacity=4)
    orders = [make_order(i) for i in range(1, 4)]

    try:
        for order in orders:
            assert buffer.write(order) is True

        assert [buffer.read() for _ in orders] == orders
    finally:
        buffer.close()
        buffer.unlink()


def test_wraparound_preserves_order():
    buffer = RingBuffer(capacity=3)

    try:
        first_batch = [make_order(i) for i in range(1, 4)]

        for order in first_batch:
            assert buffer.write(order) is True

        assert buffer.read() == first_batch[0]
        assert buffer.read() == first_batch[1]

        next_orders = [make_order(4), make_order(5)]

        for order in next_orders:
            assert buffer.write(order) is True

        assert [
            buffer.read(),
            buffer.read(),
            buffer.read(),
        ] == [first_batch[2], *next_orders]
    finally:
        buffer.close()
        buffer.unlink()


def test_capacity_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        RingBuffer(capacity=0)


# ---------------------------------------------------------
# Batch-operation tests
# ---------------------------------------------------------


def test_write_many_preserves_fifo_order():
    """Batch writes should preserve the order of records."""
    buffer = RingBuffer(capacity=5)
    orders = [make_order(i) for i in range(1, 4)]

    try:
        assert buffer.write_many(orders) == 3
        assert [buffer.read() for _ in orders] == orders
    finally:
        buffer.close()
        buffer.unlink()


def test_write_many_handles_partially_available_buffer():
    """Batch writes should write only the orders that fit."""
    buffer = RingBuffer(capacity=3)
    first = make_order(1)
    batch = [make_order(i) for i in range(2, 5)]

    try:
        assert buffer.write(first) is True

        # Only two slots are available.
        assert buffer.write_many(batch) == 2
        assert len(buffer) == 3

        assert buffer.read() == first
        assert buffer.read() == batch[0]
        assert buffer.read() == batch[1]
        assert buffer.read() is None
    finally:
        buffer.close()
        buffer.unlink()


def test_read_many_returns_available_orders_and_empty_list():
    """Batch reads return available orders, then an empty list."""
    buffer = RingBuffer(capacity=4)
    orders = [make_order(i) for i in range(1, 4)]

    try:
        assert buffer.write_many(orders) == 3
        assert buffer.read_many(5) == orders
        assert buffer.read_many(5) == []
    finally:
        buffer.close()
        buffer.unlink()


def test_batch_operations_preserve_fifo_across_wraparound():
    """Batch operations should preserve FIFO when positions wrap."""
    buffer = RingBuffer(capacity=4)
    first_batch = [make_order(i) for i in range(1, 4)]
    second_batch = [make_order(i) for i in range(4, 7)]

    try:
        assert buffer.write_many(first_batch) == 3
        assert buffer.read_many(2) == first_batch[:2]

        # One order remains, so exactly three new orders fit.
        assert buffer.write_many(second_batch) == 3

        expected_remaining = first_batch[2:] + second_batch
        assert buffer.read_many(4) == expected_remaining
        assert buffer.read_many(4) == []
    finally:
        buffer.close()
        buffer.unlink()


def test_write_many_invalid_input_does_not_partially_write():
    """Invalid input must not cause a partial batch write."""
    buffer = RingBuffer(capacity=4)
    valid_order = make_order(1)
    invalid_order = BinaryOrder(2, 9, 100, 1, 1002)

    try:
        with pytest.raises(ValueError, match="side"):
            buffer.write_many([valid_order, invalid_order])

        # The valid first order must not have been written.
        assert len(buffer) == 0
        assert buffer.read() is None
    finally:
        buffer.close()
        buffer.unlink()


def test_full_buffer_recovers_after_read():
    """A freed slot can accept a new order after the buffer is full."""
    buffer = RingBuffer(capacity=2)

    try:
        first = make_order(1)
        second = make_order(2)
        third = make_order(3)

        assert buffer.write(first) is True
        assert buffer.write(second) is True
        assert buffer.write(third) is False
        assert len(buffer) == 2

        # Reading frees a slot.
        assert buffer.read() == first
        assert len(buffer) == 1

        # The buffer should accept another order now.
        assert buffer.write(third) is True
        assert len(buffer) == 2

        # FIFO order must remain correct after recovery.
        assert buffer.read() == second
        assert buffer.read() == third
        assert buffer.read() is None
    finally:
        buffer.close()
        buffer.unlink()
def test_closed_buffer_rejects_operations():
    """Operations on a closed buffer should fail predictably."""
    buffer = RingBuffer(capacity=2)
    buffer.close()

    with pytest.raises(ValueError, match="closed"):
        buffer.write(make_order(1))

    with pytest.raises(ValueError, match="closed"):
        buffer.read()

    with pytest.raises(ValueError, match="closed"):
        len(buffer)
