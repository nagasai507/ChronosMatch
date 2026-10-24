# ChronosMatch

### Zero-Copy-Style Order Matching and Market Simulation Engine

ChronosMatch is an educational trading-engine prototype built to explore limit-order matching, price-time priority, shared-memory communication, simulated market order flow, and performance measurement. It includes a Python backend and a React dashboard for interacting with the simulation.

> **Disclaimer:** ChronosMatch is an educational simulation. It is not connected to a live stock exchange and is not intended for real-money trading.

---

## Current Status

**Current verified milestone:** the local dashboard, FastAPI API, matching engine, order book, market simulator controls, and ring-buffer implementation are integrated in the development environment.

- The frontend displays API connection status, best bid, best ask, active orders, executed trades, and bid–ask spread.
- Users can submit manual BUY and SELL orders through the dashboard.
- The simulator can be started and stopped through API endpoints.
- The dashboard displays recent trades and the order book.
- A ring-buffer benchmark section presents previously recorded throughput results; these are historical measurements, not live telemetry.
- The latest recorded full test run completed with **122 passed, 0 failed** in approximately 2.09 seconds. It emitted one Starlette deprecation warning related to the TestClient/HTTPX integration.

Status is based on work verified locally during development. Re-run the commands in this README before a formal review or release.

---

## Features Implemented

### Trading engine

- Shared `Order` and `Trade` models.
- Limit order book with best-bid and best-ask access.
- Matching engine that records executions and updates remaining quantities.
- Integer price ticks for comparisons.
- Tests for models, order book, matching behavior, and integration.

### Ring buffer and market simulation

- Binary order records and shared-memory ring-buffer implementation.
- Individual and batched write paths.
- Buffer capacity, empty/full behavior, FIFO, cleanup, and multiprocess tests.
- Market simulator and firehose modules for generating simulated orders.
- Benchmark scripts for multiprocess ring-buffer throughput and traced memory usage.

### API and web dashboard

- FastAPI endpoints for health, order book, trades, order submission, and simulator control/status.
- React + Vite dashboard.
- Manual BUY/SELL order form.
- Live polling of the API for order book, trades, and simulator status.
- Bid–ask spread calculation when both best bid and best ask exist.
- Responsive dark dashboard layout.
- Recorded ring-buffer benchmark comparison displayed separately from live market data.

### Automated tests

The current test suite covers models, order book, matching engine, integration, ring buffer, market simulator, firehose, multiprocess behavior, and API endpoints.

---

## Technology Stack

| Technology                      | Purpose                                                   |
| ------------------------------- | --------------------------------------------------------- |
| Python 3.11+                    | Core matching engine, models, simulation, and ring buffer |
| FastAPI                         | HTTP API for dashboard integration                        |
| Uvicorn                         | Local API server                                          |
| Pydantic                        | API request validation                                    |
| React                           | Interactive dashboard                                     |
| Vite                            | Frontend development server and build tooling             |
| `asyncio`                       | Asynchronous simulator task and API integration           |
| `multiprocessing.shared_memory` | Shared-memory ring-buffer storage                         |
| `struct`                        | Fixed-size binary order encoding                          |
| `pytest`                        | Automated tests                                           |
| HTTPX / FastAPI TestClient      | API endpoint tests                                        |
| Git and GitHub                  | Version control and team collaboration                    |

Some earlier project proposals mentioned Cython, `mmap`, `curses`, SQLite, and ClickHouse. Those are not described here as current integrated features; they should be added to the implemented stack only after their code and tests are integrated.

---

## Architecture

```text
                         React + Vite Dashboard
                                   |
                              HTTP / JSON
                                   |
                           FastAPI application
                      /       /      |       \
                 /health  /orders  /trades  /orderbook
                                   |
                          Matching Engine
                           /            \
                    Limit Order Book   Trade Records
                                   ^
                                   |
                            Market Simulator

        Shared-memory Ring Buffer
        (separately tested IPC and benchmark component)
```

The web simulator currently submits generated orders to the matching engine. The ring buffer is implemented and tested as an IPC component, with separate benchmark scripts. Do not assume the web simulator is routed through a ring-buffer consumer unless that integration is explicitly completed and verified.

---

## Repository Structure

```text
ChronosMatch/
├── src/
│   └── chronosmatch/
│       ├── __init__.py
│       ├── api.py
│       ├── models.py
│       ├── order_book.py
│       ├── matching_engine.py
│       ├── ring_buffer.py
│       ├── market_simulator.py
│       └── market_firehose.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── test_api.py
│   ├── test_models.py
│   ├── test_order_book.py
│   ├── test_matching_engine.py
│   ├── test_integration.py
│   ├── test_ring_buffer.py
│   ├── test_ring_buffer_multiprocess.py
│   ├── test_market_simulator.py
│   ├── test_market_firehose.py
│   ├── benchmark_ring_buffer_memory.py
│   ├── benchmark_ring_buffer_multiprocess.py
│   └── benchmark_market_simulator.py
├── docs/
│   └── INTERFACES.md
├── pyproject.toml
└── README.md
```

This tree reflects the expected current layout. Confirm names against the checked-out branch if files have changed.

---

## Installation and Setup

### Requirements

- Python 3.11+
- Node.js and npm
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/nagasai507/ChronosMatch.git
cd ChronosMatch
```

### 2. Create and activate the Python virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If your local virtual environment is stored outside the repository, activate that environment instead.

### 3. Install the Python project

From the repository root:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If the project extras do not install the API dependencies in your branch, install the dependencies listed in `pyproject.toml` and ensure FastAPI, Uvicorn, and HTTPX are available in the active environment.

### 4. Run the automated tests

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```

To run only the API tests:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_api.py -v
```

The latest recorded full-suite result is **122 passed**. Re-run the tests after any changes; do not treat a past result as a guarantee about a different commit or environment.

---

## Run the Backend

From the repository root, with the virtual environment activated:

```powershell
$env:PYTHONPATH = "src"
python -m uvicorn chronosmatch.api:app --reload --host 127.0.0.1 --port 8000
```

Useful endpoints:

| Endpoint            | Method | Purpose                                          |
| ------------------- | ------ | ------------------------------------------------ |
| `/`                 | GET    | API root information                             |
| `/health`           | GET    | Health check                                     |
| `/orderbook`        | GET    | Current bids, asks, and best prices              |
| `/trades`           | GET    | Recorded trade executions                        |
| `/orders`           | POST   | Submit a BUY or SELL order                       |
| `/simulator/start`  | POST   | Start simulated order generation                 |
| `/simulator/stop`   | POST   | Stop simulated order generation                  |
| `/simulator/status` | GET    | Read simulator running state and generated count |
| `/docs`             | GET    | Interactive Swagger API documentation            |

Example order body:

```json
{
  "side": "BUY",
  "price": 100,
  "quantity": 10
}
```

Prices and quantities must be positive integers. The API validates malformed or invalid orders before submitting them to the matching engine.

---

## Run the Frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm install
```

Start Vite on the development port used by the current local setup:

```powershell
.\node_modules\.bin\vite.cmd --host 127.0.0.1 --port 5174 --strictPort
```

Open [http://127.0.0.1:5174/](http://127.0.0.1:5174/) in a browser.

Keep both the frontend and backend terminals running while using the dashboard. The frontend expects the API at `http://127.0.0.1:8000`.

---

## Dashboard Demo Workflow

1. Start the backend and frontend using the commands above.
2. Confirm that the dashboard reports **API Connected**.
3. Submit a SELL order, for example price `100`, quantity `10`.
4. Submit a matching BUY order at price `100`, quantity `10`.
5. Confirm that the trade appears in Recent Trades and the filled orders are removed from the active book.
6. Start the market simulator and observe the generated-order count, order book, and trades.
7. Stop the simulator and confirm that order generation stops.
8. Observe the best bid, best ask, and spread when both sides of the book are available.

The dashboard's benchmark section contains recorded results and is not a live performance monitor.

---

## Tests and Benchmarks

### Test suite

The latest recorded test run:

```text
122 passed, 0 failed
```

A Starlette deprecation warning was also reported for the current TestClient/HTTPX integration. It did not fail the test suite and remains a cleanup item.

### Previously recorded ring-buffer throughput benchmark

| Mode                   |         Throughput |
| ---------------------- | -----------------: |
| Individual writes      |  96,383 orders/sec |
| Batch writes           | 234,872 orders/sec |
| Batch speedup          |              2.44× |
| Throughput improvement |           +143.69% |

These are previously recorded measurements. Performance depends on hardware, Python version, process scheduling, batch size, and workload. Re-run `tests/benchmark_ring_buffer_multiprocess.py` to refresh the measurements before presenting them as current results.

### Memory benchmark

A previous traced-memory run for 100,000 orders reported a peak of approximately 1,199.9 KiB for the optimized path. Treat this as a historical measurement and rerun `tests/benchmark_ring_buffer_memory.py` before using it in a formal report.

Benchmark scripts are separate from the normal unit-test suite. Run them explicitly when collecting performance data.

---

## Current Limitations and Follow-up Work

- The dashboard uses local in-memory state; restarting the API resets its current order book, trades, and simulator counters.
- The web simulator currently feeds orders directly into the matching engine; ring-buffer IPC is tested separately.
- Benchmark figures shown in the dashboard are historical measurements, not live telemetry.
- API TestClient emits a Starlette deprecation warning that should be reviewed when updating compatible dependencies.
- Persistent trade storage, database integration, and a production deployment are not currently documented as implemented features.
- This project is a local educational simulation, not a production HFT system.

---

## Plan Until Mid-Project Review

The target is a demonstrable, tested prototype with an explainable architecture and repeatable evidence. The following items are planned next; they are not all complete.

### Milestone A — Stabilize the integrated prototype

- [x] Run the React dashboard with the local FastAPI backend.
- [x] Submit manual orders and view the order book and trades.
- [x] Add simulator start, stop, and status controls.
- [x] Display best bid, best ask, and bid–ask spread.
- [x] Add API tests and run the full test suite (latest recorded result: 122 passed).
- [ ] Review API simulator lifecycle and edge cases.
- [ ] Resolve or document the TestClient deprecation warning.
- [ ] Re-run all tests on the exact integration branch intended for review.

### Milestone B — Validate IPC and performance

- [x] Implement and test the ring-buffer component.
- [x] Add individual-write versus batch-write benchmark scripts.
- [x] Record an initial throughput and memory baseline.
- [ ] Re-run benchmarks on the review machine and record hardware, Python version, workload, and configuration.
- [ ] Confirm and demonstrate producer-consumer correctness, full/empty behavior, wraparound, FIFO order, and cleanup.
- [ ] Verify whether the ring buffer is integrated into the end-to-end simulator pipeline; document the actual path accurately.
- [ ] Capture reproducible benchmark output for the review.

### Milestone C — Prepare the review demonstration

- [ ] Add a clear architecture diagram showing the implemented data path and the separately tested IPC component.
- [ ] Prepare a short demo: submit matching orders, show a trade, run and stop the simulator, and explain the spread.
- [ ] Present automated test results and benchmark methodology.
- [ ] Document team contributions and merged changes based on verified repository history.
- [ ] Run the complete test suite and benchmark scripts from a clean checkout of the agreed integration branch.
- [ ] Confirm the review's required deliverables and presentation format with the project coordinator.

---

## Team Workflow

The team uses individual branches and `teamlead` as the integration branch.

1. Fetch the latest changes before starting work.
2. Work on the agreed task and branch.
3. Keep commits focused and descriptive.
4. Open pull requests targeting `teamlead`.
5. Review code and run relevant tests before merging.
6. Avoid merging to `main` until the team agrees the integration is ready.
7. Update `docs/INTERFACES.md` when changing shared models, APIs, or the binary record format.

## Documentation

- [Shared Interface Contract](docs/INTERFACES.md)
- [GitHub Repository](https://github.com/nagasai507/ChronosMatch)

**Project principle:** correctness first, measured performance second, and optimization supported by reproducible evidence.
