import pytest

from src.chronosmatch.ring_buffer import (
    BinaryOrder,
    RECORD_SIZE,
    RingBuffer,
)


def make_order(order_id, side=0, price=100, quantity=2, timestamp_ns=12345):
    return BinaryOrder(order_id, side, price, quantity, timestamp_ns)


def test_record_size_and_encoding_round_trip():
    order = make_order(1, side=1, price=250, quantity=5, timestamp_ns=999999)

    encoded = RingBuffer.encode(order)

    assert len(encoded) == 33
    assert len(encoded) == RECORD_SIZE
    assert RingBuffer.decode(encoded) == order


def test_invalid_side_is_rejected():
    with pytest.raises(ValueError):
        RingBuffer.encode(make_order(1, side=2))


def test_negative_order_id_is_rejected():
    with pytest.raises(ValueError):
        RingBuffer.encode(make_order(-1))


def test_zero_quantity_is_rejected():
    with pytest.raises(ValueError):
        RingBuffer.encode(make_order(1, quantity=0))


def test_decode_rejects_wrong_record_size():
    with pytest.raises(ValueError):
        RingBuffer.decode(b"short")


def test_empty_buffer_returns_none():
    with RingBuffer(2) as buffer:
        assert buffer.read() is None
        assert len(buffer) == 0


def test_full_buffer_rejects_extra_write():
    with RingBuffer(2) as buffer:
        assert buffer.write(make_order(1))
        assert buffer.write(make_order(2))
        assert buffer.write(make_order(3)) is False
        assert len(buffer) == 2


def test_fifo_order():
    with RingBuffer(3) as buffer:
        first = make_order(1)
        second = make_order(2)

        assert buffer.write(first)
        assert buffer.write(second)
        assert buffer.read() == first
        assert buffer.read() == second
        assert buffer.read() is None


def test_wraparound_preserves_order():
    with RingBuffer(2) as buffer:
        first = make_order(1)
        second = make_order(2)
        third = make_order(3)

        assert buffer.write(first)
        assert buffer.write(second)
        assert buffer.read() == first
        assert buffer.write(third)

        assert buffer.read() == second
        assert buffer.read() == third
        assert buffer.read() is None


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        RingBuffer(0)