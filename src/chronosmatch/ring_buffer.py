"""Windows-compatible SPSC ring buffer using shared memory.

Binary record format: <QBQQQ (33 bytes)
Side: 0 = BUY, 1 = SELL

Create the buffer in the parent process and pass its name and
the same multiprocessing lock to producer and consumer processes.

This implementation uses locking; it is NOT lock-free.
"""

import struct
from dataclasses import dataclass
from multiprocessing import Lock
from multiprocessing.shared_memory import SharedMemory


ORDER_RECORD = struct.Struct("<QBQQQ")
RECORD_SIZE = ORDER_RECORD.size
UINT64_MAX = (1 << 64) - 1

# Shared metadata: read position, write position, item count.
HEADER = struct.Struct("<QQQ")
HEADER_SIZE = HEADER.size


@dataclass(frozen=True)
class BinaryOrder:
    order_id: int
    side: int  # 0 = BUY, 1 = SELL
    price: int
    quantity: int
    timestamp_ns: int


class RingBuffer:
    """Fixed-capacity, process-shared FIFO ring buffer."""

    def __init__(
        self,
        capacity: int,
        *,
        name: str | None = None,
        lock=None,
        create: bool = True,
    ):
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")

        if capacity <= 0:
            raise ValueError("capacity must be positive")

        if not create and (name is None or lock is None):
            raise ValueError(
                "Attaching requires a shared-memory name and shared lock"
            )

        self.capacity = capacity
        self.lock = lock if lock is not None else Lock()
        self._owner = create
        self._closed = False

        total_size = HEADER_SIZE + capacity * RECORD_SIZE

        if create:
            self._shm = SharedMemory(
                name=name,
                create=True,
                size=total_size,
            )
            self.name = self._shm.name
            self._memory = self._shm.buf

            # Initialize shared metadata.
            with self.lock:
                HEADER.pack_into(self._memory, 0, 0, 0, 0)
        else:
            self._shm = SharedMemory(name=name, create=False)
            self.name = self._shm.name
            self._memory = self._shm.buf

            if self._shm.size < total_size:
                self._memory.release()
                self._shm.close()
                self._closed = True
                raise ValueError(
                    "Shared-memory size does not match capacity"
                )

    @staticmethod
    def encode(order: BinaryOrder) -> bytes:
        """Validate and encode an order into exactly 33 bytes."""
        if not isinstance(order, BinaryOrder):
            raise TypeError("order must be a BinaryOrder")

        values = (
            order.order_id,
            order.side,
            order.price,
            order.quantity,
            order.timestamp_ns,
        )

        names = (
            "order_id",
            "side",
            "price",
            "quantity",
            "timestamp_ns",
        )

        for field_name, value in zip(names, values):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")

        if not 0 <= order.order_id <= UINT64_MAX:
            raise ValueError("order_id must fit in unsigned 64-bit")

        if order.side not in (0, 1):
            raise ValueError("side must be 0 (BUY) or 1 (SELL)")

        if not 0 <= order.price <= UINT64_MAX:
            raise ValueError("price must fit in unsigned 64-bit")

        if not 1 <= order.quantity <= UINT64_MAX:
            raise ValueError("quantity must be a positive unsigned 64-bit integer")

        if not 0 <= order.timestamp_ns <= UINT64_MAX:
            raise ValueError("timestamp_ns must fit in unsigned 64-bit")

        return ORDER_RECORD.pack(*values)

    @staticmethod
    def decode(data: bytes) -> BinaryOrder:
        """Decode one 33-byte record and validate its values."""
        if len(data) != RECORD_SIZE:
            raise ValueError(
                f"record must be exactly {RECORD_SIZE} bytes"
            )

        order = BinaryOrder(*ORDER_RECORD.unpack(data))

        # Reuse the encoder's validation rules.
        RingBuffer.encode(order)

        return order

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("RingBuffer is closed")

    def _state(self) -> tuple[int, int, int]:
        return HEADER.unpack_from(self._memory, 0)

    def write(self, order: BinaryOrder) -> bool:
        """Write an order; return False if the buffer is full."""
        self._ensure_open()
        record = self.encode(order)

        with self.lock:
            read_pos, write_pos, count = self._state()

            if count >= self.capacity:
                return False

            offset = HEADER_SIZE + write_pos * RECORD_SIZE
            self._memory[offset:offset + RECORD_SIZE] = record

            write_pos = (write_pos + 1) % self.capacity
            count += 1

            HEADER.pack_into(
                self._memory, 0, read_pos, write_pos, count
            )

            return True

    def read(self) -> BinaryOrder | None:
        """Read the oldest order; return None if the buffer is empty."""
        self._ensure_open()

        with self.lock:
            read_pos, write_pos, count = self._state()

            if count == 0:
                return None

            offset = HEADER_SIZE + read_pos * RECORD_SIZE
            record = bytes(
                self._memory[offset:offset + RECORD_SIZE]
            )

            read_pos = (read_pos + 1) % self.capacity
            count -= 1

            HEADER.pack_into(
                self._memory, 0, read_pos, write_pos, count
            )

            return self.decode(record)

    def __len__(self) -> int:
        self._ensure_open()

        with self.lock:
            _, _, count = self._state()
            return count

    def close(self) -> None:
        """Close this process's view of shared memory."""
        if self._closed:
            return

        self._memory.release()
        self._shm.close()
        self._closed = True

    def unlink(self) -> None:
        """Remove the shared-memory name; call once from the owner."""
        if not self._owner:
            raise RuntimeError(
                "Only the process that created the buffer may unlink it"
            )

        self._shm.unlink()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()