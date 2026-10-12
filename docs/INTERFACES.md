# ChronosMatch Shared Interface Contract

This document defines the agreement between the four workstreams. Read it before coding a module that imports another member's work. Discuss interface changes in the team chat first.

## 1. Shared Model — Member 1

Module: `src/chronosmatch/models.py`

### OrderSide

- `OrderSide.BUY`
- `OrderSide.SELL`

### Order

Fields:

- `order_id: str`
- `side: OrderSide`
- `price: int`
- `quantity: int`
- `timestamp: int = 0`
- `remaining_quantity: int | None = None`

Rules:

- Prices are integer ticks; do not use floats for price comparisons.
- Quantities must be positive integers.
- `remaining_quantity` starts equal to `quantity` when not supplied.
- The engine may reduce `remaining_quantity` after a fill.
- An order with zero remaining quantity is no longer live.

### Trade

Fields:

- `trade_id`
- `buy_order_id`
- `sell_order_id`
- `price`
- `quantity`
- `timestamp`

Rules:

- Each trade represents one execution between a buy order and a sell order.
- Trade quantity must be positive.
- Trade records are immutable.

The existing Python model interfaces must remain compatible with the order book and matching engine unless the team agrees to a change.

## 2. Order Book — Member 2

Module: `src/chronosmatch/order_book.py`

Public methods:

- `add_order(order: Order) -> None`
- `get_best_bid() -> Order | None`
- `get_best_ask() -> Order | None`
- `remove_order(order_id: str) -> bool`

Rules:

- Highest buy price has priority; lowest sell price has priority.
- At the same price, preserve FIFO by accepted/sequence order.
- Orders with no remaining quantity must not be returned as best orders.
- The book stores only the unmatched remainder after the engine has tried to match.

## 3. Matching Engine — Member 3

Module: `src/chronosmatch/matching_engine.py`

Public method:

- `submit_order(order: Order) -> list[Trade]`

Rules:

- A buy can match the best ask when buy price >= ask price.
- A sell can match the best bid when sell price <= bid price.
- Match at the resting order's price unless the team documents a different rule.
- Each fill reduces both orders' remaining quantities.
- Each fill creates one `Trade` with positive quantity.
- Add the incoming order to the book only if it has remaining quantity.
- Return only the trades created by this submission.
- Record created trades in the engine's trade history.

## 4. Zero-Copy IPC Ring Buffer — Week 1

Module: `src/chronosmatch/ring_buffer.py`

### Purpose

Use Python's `mmap` and `struct` modules to transfer fixed-size binary order records through memory-mapped storage without JSON or pickle serialization.

### Proposed binary order record

Status: **Pending confirmation by the ring-buffer owner, market-simulator owner, and team lead.**

Proposed Python format:

```python
ORDER_RECORD_FORMAT = "<QBQQQ"
ORDER_RECORD_SIZE = 33
```

The `<` prefix specifies little-endian byte order with standard field sizes and no native alignment padding.

| Field          | Format |         Size | Meaning                                  |
| -------------- | ------ | -----------: | ---------------------------------------- |
| `order_id`     | `Q`    |      8 bytes | Unsigned 64-bit numeric order ID         |
| `side`         | `B`    |       1 byte | `0 = BUY`, `1 = SELL`                    |
| `price`        | `Q`    |      8 bytes | Unsigned 64-bit integer price ticks      |
| `quantity`     | `Q`    |      8 bytes | Unsigned 64-bit quantity                 |
| `timestamp_ns` | `Q`    |      8 bytes | Unsigned 64-bit timestamp in nanoseconds |
| **Total**      |        | **33 bytes** | Fixed-size record                        |

All fields must fit their unsigned integer ranges. Price and quantity must be positive, and the side byte must be either `0` or `1`.

### Mapping numeric IDs to Python model IDs

The existing `Order.order_id` remains a string.

- The market simulator generates unique numeric IDs for binary records.
- The IPC consumer converts a decoded numeric ID to a string when constructing an `Order`, if that representation is sufficient.
- If external string IDs must be preserved, an explicit mapping between numeric and string IDs is required.
- Do not assume arbitrary string IDs can be converted directly to integers.

### Timestamp semantics

The binary `timestamp_ns` field is separate from the existing `Order.timestamp` field.

- Do not assume `Order.timestamp` already represents nanoseconds.
- The team must define when `timestamp_ns` is captured and what it represents.
- Use `time.perf_counter_ns()` for measuring elapsed processing time.
- Only compare timestamps across processes when their clock source and clock domain are compatible.

### Required ring-buffer behavior

- Encode and decode records using the agreed binary format.
- Support fixed-capacity storage.
- Provide write and read operations.
- Detect full and empty states.
- Handle wraparound correctly.
- Define producer-consumer synchronization.
- Validate records before packing.
- Close mapped memory and associated resources safely.

The initial implementation must document whether it supports a single producer and single consumer or multiple producers and consumers.

The buffer API, capacity behavior, and synchronization protocol must be agreed upon before dependent modules are finalized.

## 5. Market Simulator — Week 1

Module: `src/chronosmatch/market_simulator.py`

### Purpose

Generate asynchronous mock BUY and SELL orders and submit them to the IPC ring buffer.

### Required behavior

- Generate valid mock order IDs, sides, prices, and quantities.
- Use the agreed binary order record format.
- Submit records through the ring-buffer interface.
- Handle full-buffer conditions safely.
- Avoid JSON and pickle for the IPC records.
- Measure successfully written orders per second.
- Provide configurable workload size and benchmark duration.

### Performance target

The Week 1 target is **100,000 mock orders per second**.

This is a target to measure, not a guaranteed result. Report the actual throughput and document the workload and test environment.

The simulator and ring buffer must use the same agreed record layout and API.

## 6. Integration and Tests — Member 4

Required testing includes:

### Models

- Valid order initialization.
- Invalid order fields.
- Remaining-quantity validation.
- Trade validation.

### Order Book

- Empty-book behavior.
- Best-price selection.
- FIFO at equal prices.
- Order removal.
- Exclusion of orders with zero remaining quantity.

### Matching Engine

- No match.
- Exact fill.
- Partial fill.
- One incoming order filling multiple resting orders.
- FIFO at equal prices.
- Best-price selection.
- Invalid input.
- Trade history and remaining quantities.

Verify that executed quantity never exceeds the available quantity of either order.

### Ring Buffer

- Binary record encoding and decoding.
- Write and read operations.
- Empty and full states.
- Wraparound.
- Invalid record fields.
- Producer-consumer correctness.
- Safe resource cleanup.

### Market Simulator

- Valid order generation.
- Correct binary encoding.
- Successful writes to the buffer.
- Full-buffer handling.
- Throughput measurement.

Run `pytest` before requesting integration. Passing unit tests alone does not prove that the full application works.

## 7. Four-Week Development Roadmap

### Week 1 — Memory Mapping and Market Firehose

Low-latency engineering:

- Build the `mmap` ring buffer using Python's `mmap` and `struct`.
- Read and write binary order records.

Market logic:

- Build the `asyncio` mock-order producer.
- Target 100,000 mock orders per second.
- Measure actual throughput.

### Week 2 — Cython Engine and Dashboard

Low-latency engineering:

- Implement the limit order book and matching loop in `.pyx`.
- Use C types and appropriate low-level data structures.

Market logic and UI:

- Build a `curses` terminal dashboard.
- Display the best bid, best ask, and spread.
- Verify basic matching behavior.

### Mid-Project Review

- Demonstrate the IPC architecture transferring one million orders between two Python processes without pickling.
- Verify that compatible buy and sell orders produce trades.
- Present test results and measured performance.

### Week 3 — C-Level Optimization and Metrics

Low-latency engineering:

- Reduce Python object interactions in the Cython matching loop.
- Investigate garbage-collection and latency behavior.

Metrics:

- Use `time.perf_counter_ns()` to measure relevant processing stages.
- Record and analyze latency distributions.

### Week 4 — Resiliency and Final Demonstration

Low-latency engineering:

- Implement asynchronous trade persistence to SQLite or ClickHouse.

Market logic and UI:

- Polish the terminal dashboard.
- Highlight large orders clearing multiple price levels.
- Demonstrate the complete system and report measured performance.

## 8. Change Process

- Discuss interface changes in the team chat before implementing them.
- Update this document when an interface change is agreed.
- Update dependent code and tests in the same reviewed change.
- Each member works on their assigned branch and opens a pull request targeting `teamlead`.
- The team lead reviews changes and runs the integrated test suite before merging.
- Do not claim performance targets are achieved without recorded measurements.

## 9. Current Workstream Ownership

- **Sai — Member 4 / Team Lead:** Integration, interface coordination, test review, and performance reporting.
- **Joshitha — Member 2:** Order book completed; proposed owner of the Week 1 ring buffer.
- **Ramya — Member 1:** Shared models and model tests; proposed owner of the Week 1 market simulator.
- **Shivam — Member 3:** Matching engine implementation and matching-engine tests.

Week 1 assignments are recommendations for coordinating the additional IPC and market-simulator work. Confirm ownership with each member before treating it as accepted.
