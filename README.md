# ChronosMatch

### Zero-Copy High-Frequency Trading Engine

ChronosMatch is an educational project that explores low-latency order processing, price-time-priority matching, inter-process communication (IPC), and performance measurement using Python and Cython.

The project aims to build a simulated trading engine with a memory-mapped ring buffer, a limit order book, a matching engine, and a terminal-based market dashboard.

> **Disclaimer:** ChronosMatch is an educational simulation. It is not connected to a live stock exchange and is not intended for real-money trading.

---

## Project Objectives

- Implement a limit order book with price-time priority.
- Build a matching engine that supports full fills, partial fills, and multiple executions.
- Explore zero-copy-style IPC using Python `mmap` and `struct`.
- Generate mock orders asynchronously using `asyncio`.
- Explore Cython optimization for performance-critical matching logic.
- Measure throughput and latency using reproducible benchmarks.
- Persist executed trades to a database asynchronously.
- Display market activity through a terminal-based dashboard.

## Technology Stack

| Technology          | Purpose                               |
| ------------------- | ------------------------------------- |
| Python 3.11+        | Core application and simulation       |
| `mmap`              | Memory-mapped IPC buffer              |
| `struct`            | Binary order encoding and decoding    |
| `asyncio`           | Asynchronous mock-order generation    |
| Cython              | Compiled matching-engine optimization |
| `curses`            | Terminal-based market dashboard       |
| `pytest`            | Automated testing                     |
| SQLite / ClickHouse | Trade persistence target              |
| Git and GitHub      | Version control and collaboration     |

Some technologies are planned for later development and should not be considered implemented until their code and tests are available.

---

## Project Architecture

```text
Market Simulator
      |
      | Binary order records
      v
Memory-Mapped Ring Buffer
      |
      | IPC consumer
      v
Order Decoder
      |
      v
Matching Engine
      |
      +------> Limit Order Book
      |
      +------> Executed Trades
                    |
                    v
           Asynchronous Ledger
                    |
                    v
             SQLite / ClickHouse

Market State ------> Terminal Dashboard
```

The intended IPC design uses fixed-size binary records rather than JSON or pickle serialization. The implementation must still define buffer synchronization, full/empty behavior, and producer-consumer ownership.

## Repository Structure

```text
ChronosMatch/
├── src/
│   └── chronosmatch/
│       ├── __init__.py
│       ├── models.py
│       ├── order_book.py
│       ├── matching_engine.py
│       ├── ring_buffer.py          # Week 1 planned module
│       └── market_simulator.py     # Week 1 planned module
├── tests/
│   ├── test_models.py
│   └── test_integration.py
├── docs/
│   └── INTERFACES.md
├── pyproject.toml
├── .gitignore
└── README.md
```

The ring-buffer and market-simulator files are planned additions. Create them when their assigned implementation work begins.

---

## Core Components

### 1. Shared Models

Module: `src/chronosmatch/models.py`

Defines the shared data structures:

- `OrderSide` — BUY and SELL.
- `Order` — order ID, side, price, quantity, timestamp, and remaining quantity.
- `Trade` — trade ID, buy and sell order IDs, execution price, quantity, and timestamp.

Prices use integer ticks to avoid floating-point price comparisons.

### 2. Limit Order Book

Module: `src/chronosmatch/order_book.py`

Maintains unmatched orders and exposes:

- `add_order(order)`
- `get_best_bid()`
- `get_best_ask()`
- `remove_order(order_id)`

Expected rules:

- Highest bid has priority.
- Lowest ask has priority.
- Orders at the same price follow FIFO.
- Fully filled orders are not available as live orders.

### 3. Matching Engine

Module: `src/chronosmatch/matching_engine.py`

Planned public method:

```python
submit_order(order) -> list[Trade]
```

Expected behavior:

- Match compatible incoming orders against the best resting orders.
- Execute at the resting order's price unless the team agrees on another rule.
- Support partial fills and one order matching multiple resting orders.
- Update remaining quantities.
- Add only an unmatched remainder to the order book.
- Return and record the trades created by the submission.

### 4. Zero-Copy IPC Ring Buffer

Planned module: `src/chronosmatch/ring_buffer.py`

Week 1 implementation requirements:

- Use `mmap` for memory-mapped storage.
- Use `struct` for fixed-size binary records.
- Implement write and read operations.
- Handle capacity, empty/full states, and wraparound.
- Define safe producer-consumer synchronization.
- Avoid JSON and pickle for IPC order records.

The record layout and public buffer API must be confirmed in [`docs/INTERFACES.md`](docs/INTERFACES.md) before dependent modules are finalized.

### 5. Market Simulator

Planned module: `src/chronosmatch/market_simulator.py`

The simulator will:

- Generate mock BUY and SELL orders.
- Submit orders through the ring buffer.
- Handle buffer backpressure.
- Measure actual throughput.
- Target **100,000 orders per second** during the Week 1 benchmark.

The target is not a measured result. Any performance claim must include the actual benchmark result and test environment.

### 6. Cython Matching Engine

Planned for Week 2:

- Move performance-critical matching logic into a `.pyx` module.
- Use C-level types and suitable data structures.
- Minimize Python-object interactions in the critical loop.
- Validate behavior against the Python implementation.

### 7. Terminal Dashboard and Trade Ledger

Planned for later weeks:

- Use `curses` to display the best bid, best ask, and spread.
- Display market activity and large orders clearing multiple price levels.
- Flush executed trades asynchronously to SQLite or ClickHouse.

---

## Installation and Setup

### Requirements

- Python 3.11 or newer
- Git
- Windows, Linux, or macOS
- A C compiler may be required for the Cython build stage.

### 1. Clone the Repository

```bash
git clone https://github.com/nagasai507/ChronosMatch.git
cd ChronosMatch
```

### 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use an appropriate local execution-policy setting or activate the environment through your IDE.

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

From the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 4. Run Tests

```bash
python -m pytest -v
```

Run a specific test file:

```bash
python -m pytest tests/test_models.py -v
python -m pytest tests/test_integration.py -v
```

**Note:** Integration tests for matching behavior will pass only after the matching engine implements the required interface and behavior.

---

## Testing Strategy

ChronosMatch uses automated tests to validate correctness before optimization.

### Model Tests

- Valid order initialization.
- Invalid order fields.
- Remaining-quantity validation.
- Trade validation.

### Order Book Tests

- Empty-book behavior.
- Best bid and best ask selection.
- FIFO ordering at the same price.
- Order removal.
- Exclusion of fully filled orders.

### Matching Tests

- No match.
- Exact fill.
- Partial fill.
- One incoming order filling multiple resting orders.
- Price-time priority.
- Correct trade history and remaining quantities.

### IPC Tests

- Binary encoding and decoding.
- Buffer read/write operations.
- Full and empty conditions.
- Wraparound.
- Producer-consumer correctness.
- Resource cleanup.

### Performance Tests

Measure and report:

- Orders successfully processed per second.
- Processing latency.
- Latency distribution, including median and high percentiles where appropriate.
- Test workload, hardware, Python version, and relevant configuration.

Use `time.perf_counter_ns()` for elapsed-time measurements. Do not present an unmeasured target as an achieved benchmark.

---

## Four-Week Development Roadmap

### Week 1 — IPC and Market Firehose

- Implement the memory-mapped ring buffer using `mmap` and `struct`.
- Implement the asynchronous mock-order producer.
- Define and test the shared binary record format.
- Measure throughput against the 100,000-orders-per-second target.
- Complete and test the Python matching-engine baseline.

### Week 2 — Cython and Dashboard

- Implement the performance-critical matching logic in Cython.
- Integrate the limit order book.
- Build the `curses` terminal dashboard.
- Verify matching correctness after integration.

### Mid-Project Review

Demonstrate:

- One million orders transferred between two Python processes without pickling.
- Correct matching behavior for compatible orders.
- Automated test results.
- Reproducible throughput and latency measurements.

### Week 3 — Performance Optimization

- Reduce Python overhead in the critical matching loop.
- Measure latency using `time.perf_counter_ns()`.
- Compare the Python baseline with the Cython implementation.
- Document optimization results and trade-offs.

### Week 4 — Persistence and Final Demo

- Flush executed trades asynchronously to SQLite or ClickHouse.
- Polish the dashboard.
- Demonstrate large orders consuming multiple price levels.
- Present architecture, correctness tests, benchmark methodology, and measured results.

---

## Team Responsibilities

| Team member     | Primary responsibility                                                           |
| --------------- | -------------------------------------------------------------------------------- |
| Sai — Team Lead | Integration, interface coordination, end-to-end tests, and performance reporting |
| Joshitha        | Order book; proposed owner of the Week 1 ring buffer                             |
| Ramya           | Shared models and model tests; proposed owner of the Week 1 market simulator     |
| Shivam          | Matching engine and matching-engine tests                                        |

Confirm the additional Week 1 workstream assignments with the relevant members before treating them as final.

---

## Git and Collaboration Workflow

The team uses individual branches and a shared integration branch named `teamlead`.

1. Fetch the latest changes before starting work.
2. Work on your assigned branch or agreed workstream.
3. Commit related changes with clear messages.
4. Push your branch to GitHub.
5. Open a pull request targeting `teamlead`.
6. Review the changes and run the tests before merging.
7. Keep `main` aligned with the project's review and submission requirements.

Before changing a shared method, data model, or binary format, discuss the change with the team and update [`docs/INTERFACES.md`](docs/INTERFACES.md).

Do not force-push over teammates' work or claim that a pull request is tested without running the relevant tests.

---

## Current Project Status

The project has an initial Python package structure, shared models, an order book implementation, test files, and an interface contract. The current foundation has previously passed 12 tests in the local environment.

The following work still requires implementation and/or verification before it can be described as complete:

- Full matching-engine behavior and integration tests.
- Memory-mapped ring buffer.
- Asynchronous market simulator and throughput benchmark.
- Two-process, one-million-order IPC demonstration.
- Cython matching engine and terminal dashboard.
- Asynchronous trade persistence.
- Final end-to-end performance measurements.

Test counts and status should be updated after running the latest integrated test suite.

---

## Documentation

- [Shared Interface Contract](docs/INTERFACES.md)
- [ChronosMatch GitHub Repository](https://github.com/nagasai507/ChronosMatch)

## Project Goal

Build a correct, testable trading-engine simulation first, then optimize it and demonstrate its behavior with measured evidence.

**Correctness first. Measured performance second.**
