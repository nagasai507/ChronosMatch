# ChronosMatch

**ChronosMatch** is an educational Python project exploring a low-latency, price-time-priority order-matching engine. It is a simulation only; it is not connected to a live exchange.

## Week 1 goal

Build a small, testable foundation that the four team members can develop in parallel:
- shared order/trade models
- an order book with price-time priority
- a matching engine that handles fills and remaining quantities
- automated tests and clear module contracts

## Project structure

```text
ChronosMatch/
├── src/
│   └── chronosmatch/
│       ├── __init__.py
│       ├── models.py
│       ├── order_book.py
│       └── matching_engine.py
├── tests/
│   └── test_models.py
├── docs/
│   └── INTERFACES.md
├── pyproject.toml
├── .gitignore
└── README.md
```

## Setup

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

python -m pip install -e ".[dev]"
pytest
```

## Team module ownership

- **Member 1 — Models:** `models.py`; keep the shared `Order` and `Trade` contracts stable and add model tests.
- **Member 2 — Order book:** `order_book.py`; implement best bid/ask and price-time priority.
- **Member 3 — Matching engine:** `matching_engine.py`; implement matching, trade creation and partial fills.
- **Member 4 — Integration and tests:** `tests/`; add end-to-end/edge-case tests and coordinate integration.

All members should read [the interface contract](docs/INTERFACES.md) before implementing dependent modules.

## Collaboration rules

1. Work on your assigned branch and push commits regularly.
2. Do not rename shared classes or methods without discussing it with the team first.
3. Open pull requests for review and integrate into a shared working branch only as agreed.
4. **Do not merge into `main` before the required Infotact review.** Follow the program's project-progress instructions for linking each member's branch.
5. Never claim performance results until they have been measured and recorded reproducibly.

## Current status

This starter structure establishes the shared contracts. The order-book and matching algorithms are intentionally left for their assigned owners to implement.
