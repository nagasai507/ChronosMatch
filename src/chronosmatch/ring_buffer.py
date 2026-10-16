
"""Windows-compatible SPSC ring buffer using shared memory.

Binary record format: <QBQQQ (33 bytes).
Side: 0 = BUY, 1 = SELL.

Create the buffer in the parent process and pass its name and
the same multiprocessing lock to producer and consumer processes.

This implementation uses locking; it is NOT lock-free.

Batch writes validate every input before modifying shared memory.
A disk-backed temporary spool avoids retaining large batches in RAM.
"""

import struct
import tempfile
from dataclasses import dataclass
from multiprocessing import Lock
from multiprocessing.shared_memory import SharedMemory
from typing import Iterable

ORDER_RECORD = struct.Struct("<QBQQQ")
RECORD_SIZE = ORDER_RECORD.size
UINT64_MAX = (1 << 64) - 1

# Shared metadata: read position, write position, item count.
HEADER = struct.Struct("<QQQ")
HEADER_SIZE = HEADER.size

# Keep only a limited amount of staged data in memory before spilling to disk.
SPOOL_MEMORY_LIMIT = 1024 * 1024  # 1 MiB


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
            raise ValueError(
                "quantity must be a positive unsigned 64-bit integer"
            )
        if not 0 <= order.timestamp_ns <= UINT64_MAX:
            raise ValueError(
                "timestamp_ns must fit in unsigned 64-bit"
            )

        return ORDER_RECORD.pack(*values)

    @staticmethod
    def decode(data: bytes) -> BinaryOrder:
        """Decode one 33-byte record and validate its values."""
        if len(data) != RECORD_SIZE:
            raise ValueError(
                f"record must be exactly {RECORD_SIZE} bytes"
            )

        order = BinaryOrder(*ORDER_RECORD.unpack(data))
        RingBuffer.encode(order)
        return order

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("RingBuffer is closed")

    def _state(self) -> tuple[int, int, int]:
        return HEADER.unpack_from(self._memory, 0)

    def write_many(self, orders: Iterable[BinaryOrder]) -> int:
        """Validate a complete batch, then write as many orders as fit.

        Orders are encoded into a temporary spool during validation.
        Large batches spill to disk instead of growing a Python list.

        Invalid input leaves shared memory unchanged. The shared lock is
        acquired once for the actual batch write.

        Returns the number of orders written.
        """
        self._ensure_open()

        # Stage and validate the entire input before touching shared memory.
        # SpooledTemporaryFile keeps up to SPOOL_MEMORY_LIMIT in memory,
        # then automatically rolls the staged data to disk.
        with tempfile.SpooledTemporaryFile(
            max_size=SPOOL_MEMORY_LIMIT,
            mode="w+b",
        ) as staged:
            total = 0

            for order in orders:
                staged.write(self.encode(order))
                total += 1

            if total == 0:
                return 0

            staged.seek(0)

            with self.lock:
                read_pos, write_pos, count = self._state()
                written = min(total, self.capacity - count)

                for _ in range(written):
                    record = staged.read(RECORD_SIZE)

                    # Defensive check: staged records must be complete.
                    if len(record) != RECORD_SIZE:
                        raise RuntimeError(
                            "Incomplete record in temporary spool"
                        )

                    offset = HEADER_SIZE + write_pos * RECORD_SIZE
                    self._memory[offset:offset + RECORD_SIZE] = record
                    write_pos = (write_pos + 1) % self.capacity

                if written:
                    count += written
                    HEADER.pack_into(
                        self._memory,
                        0,
                        read_pos,
                        write_pos,
                        count,
                    )

            return written

    def read_many(self, max_items: int) -> list[BinaryOrder]:
        """Read up to max_items FIFO orders using one lock acquisition."""
        self._ensure_open()

        if isinstance(max_items, bool) or not isinstance(max_items, int):
            raise TypeError("max_items must be an integer")
        if max_items < 0:
            raise ValueError("max_items cannot be negative")
        if max_items == 0:
            return []

        records = []

        with self.lock:
            read_pos, write_pos, count = self._state()
            amount = min(max_items, count)

            for _ in range(amount):
                offset = HEADER_SIZE + read_pos * RECORD_SIZE
                records.append(
                    bytes(
                        self._memory[
                            offset:offset + RECORD_SIZE
                        ]
                    )
                )
                read_pos = (read_pos + 1) % self.capacity

            if amount:
                count -= amount
                HEADER.pack_into(
                    self._memory,
                    0,
                    read_pos,
                    write_pos,
                    count,
                )

        return [self.decode(record) for record in records]

    def write(self, order: BinaryOrder) -> bool:
        """Write one order; return False if the buffer is full."""
        return self.write_many((order,)) == 1

    def read(self) -> BinaryOrder | None:
        """Read one FIFO order; return None if the buffer is empty."""
        orders = self.read_many(1)
        return orders[0] if orders else None

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
