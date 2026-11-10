
"""Deep resting order-book benchmark for ChronosMatch."""

import csv
import statistics
import time
from datetime import datetime
from pathlib import Path

from chronosmatch.matching_engine import MatchingEngine
from chronosmatch.models import Order, OrderSide


RESULTS_FILE = Path(__file__).with_name(
    "benchmark_results_deep_book.csv"
)

REPETITIONS = 5
SIZES = [1000, 2500, 5000]


def create_resting_orders(count: int) -> list[Order]:
    """Create non-crossing SELL orders at multiple price levels."""
    return [
        Order(
            order_id=f"DEEP-ASK-{i}",
            side=OrderSide.SELL,
            price=110 + (i % 100),
            quantity=10,
            timestamp=i,
        )
        for i in range(count)
    ]


def run_once(count: int) -> dict:
    """Build a deep ask book and sweep it with one incoming BUY."""
    engine = MatchingEngine()

    resting_orders = create_resting_orders(count)

    # Build the resting order book before measuring matching.
    for order in resting_orders:
        engine.submit_order(order)

    assert len(engine.order_book._asks) == count
    assert len(engine.order_book._bids) == 0

    incoming_order = Order(
        order_id="DEEP-SWEEP-BUY",
        side=OrderSide.BUY,
        price=209,
        quantity=count * 10,
        timestamp=count + 1,
    )

    start = time.perf_counter_ns()
    trades = engine.submit_order(incoming_order)
    elapsed_ns = time.perf_counter_ns() - start

    elapsed = elapsed_ns / 1_000_000_000
    traded_quantity = sum(trade.quantity for trade in trades)

    # Correctness checks.
    assert len(trades) == count, (
        f"Expected {count} trades, got {len(trades)}"
    )

    assert traded_quantity == count * 10, (
        f"Unexpected traded quantity: {traded_quantity}"
    )

    assert len(engine.order_book._asks) == 0, (
        "Some resting asks remain after the sweep"
    )

    assert incoming_order.remaining_quantity == 0

    return {
        "orders": count,
        "trades": len(trades),
        "traded_quantity": traded_quantity,
        "elapsed": elapsed,
        "throughput": count / elapsed,
        "average_trade_latency_ms": (
            elapsed_ns / count / 1_000_000
        ),
    }


def save_results(results: list[dict]) -> None:
    """Append deep-book benchmark results to CSV."""
    fields = [
        "run_date",
        "scenario",
        "resting_orders",
        "repetition",
        "trades",
        "traded_quantity",
        "elapsed_seconds",
        "throughput_trades_per_sec",
        "average_trade_latency_ms",
    ]

    file_exists = (
        RESULTS_FILE.exists()
        and RESULTS_FILE.stat().st_size > 0
    )

    with RESULTS_FILE.open(
        "a", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)

        if not file_exists:
            writer.writeheader()

        for result in results:
            writer.writerow({
                "run_date": result["run_date"],
                "scenario": "deep_order_book_sweep",
                "resting_orders": result["orders"],
                "repetition": result["repetition"],
                "trades": result["trades"],
                "traded_quantity": result["traded_quantity"],
                "elapsed_seconds": result["elapsed"],
                "throughput_trades_per_sec": result["throughput"],
                "average_trade_latency_ms": (
                    result["average_trade_latency_ms"]
                ),
            })


def main() -> None:
    print("\nCHRONOSMATCH - DEEP ORDER BOOK BENCHMARK")
    print("=" * 75)

    all_results = []

    for count in SIZES:
        print(f"\nResting orders: {count}")
        print("Preparing warm-up...")

        run_once(count)

        repetitions = []

        for repetition in range(1, REPETITIONS + 1):
            result = run_once(count)

            result["run_date"] = datetime.now().isoformat(
                timespec="seconds"
            )
            result["repetition"] = repetition

            repetitions.append(result)
            all_results.append(result)

        avg_throughput = statistics.mean(
            r["throughput"] for r in repetitions
        )

        avg_latency = statistics.mean(
            r["average_trade_latency_ms"]
            for r in repetitions
        )

        print(f"Trades per run: {count}")
        print(
            f"Average throughput: "
            f"{avg_throughput:,.2f} trades/sec"
        )
        print(
            f"Average latency per trade: "
            f"{avg_latency:.6f} ms"
        )

    save_results(all_results)

    print("\nDeep-book benchmark completed.")
    print(f"Results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
