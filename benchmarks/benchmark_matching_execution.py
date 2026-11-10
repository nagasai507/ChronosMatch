
"""Repeatable matching execution benchmark for ChronosMatch."""

import argparse
import csv
import math
import statistics
import time
from datetime import datetime
from pathlib import Path

from chronosmatch.matching_engine import MatchingEngine
from chronosmatch.models import Order, OrderSide


RESULTS_FILE = Path(__file__).with_name("benchmark_results_v2.csv")
REPETITIONS = 5
ORDER_QUANTITY = 10


def percentile(values: list[int], percent: float) -> float:
    """Return nearest-rank percentile in milliseconds."""
    ordered = sorted(values)
    index = max(0, math.ceil(percent * len(ordered)) - 1)
    return ordered[index] / 1_000_000


def run_matching_benchmark(count: int) -> dict:
    """Submit alternating crossing orders and measure execution latency."""

    engine = MatchingEngine()
    latencies = []
    total_trades = 0
    total_traded_quantity = 0

    start_all = time.perf_counter_ns()

    for i in range(count):

        if i % 2 == 0:
            side = OrderSide.BUY
            price = 101
        else:
            side = OrderSide.SELL
            price = 100

        order = Order(
            order_id=f"MATCH-{count}-{i}",
            side=side,
            price=price,
            quantity=ORDER_QUANTITY,
            timestamp=i,
        )

        start = time.perf_counter_ns()
        trades = engine.submit_order(order)
        end = time.perf_counter_ns()

        latencies.append(end - start)
        total_trades += len(trades)

        total_traded_quantity += sum(
            trade.quantity for trade in trades
        )

    elapsed = (
        time.perf_counter_ns() - start_all
    ) / 1_000_000_000

    # Correctness checks:
    # Every two orders should create one trade.
    expected_trades = count // 2

    # Each trade should execute ORDER_QUANTITY units.
    expected_quantity = expected_trades * ORDER_QUANTITY

    assert total_trades == expected_trades, (
        f"Expected {expected_trades} trades, "
        f"but got {total_trades}"
    )

    assert total_traded_quantity == expected_quantity, (
        f"Expected traded quantity {expected_quantity}, "
        f"but got {total_traded_quantity}"
    )

    assert all(
        order.remaining_quantity == 0
        for order in []
    ), "Unexpected remaining quantity"

    return {
        "orders": count,
        "elapsed": elapsed,
        "throughput": count / elapsed if elapsed else 0,
        "average_latency": statistics.mean(latencies) / 1_000_000,
        "p50_latency": percentile(latencies, 0.50),
        "p95_latency": percentile(latencies, 0.95),
        "p99_latency": percentile(latencies, 0.99),
        "trades": total_trades,
        "traded_quantity": total_traded_quantity,
    }


def save_results(results: list[dict]) -> None:
    """Append matching benchmark repetitions to the shared V2 CSV."""

    fields = [
        "run_date",
        "scenario",
        "orders",
        "repetition",
        "elapsed_seconds",
        "throughput_orders_per_sec",
        "average_latency_ms",
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "trades",
    ]

    file_exists = (
        RESULTS_FILE.exists()
        and RESULTS_FILE.stat().st_size > 0
    )

    with RESULTS_FILE.open(
        "a", newline="", encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        if not file_exists:
            writer.writeheader()

        for result in results:

            row = {
                "run_date": result["run_date"],
                "scenario": result["scenario"],
                "orders": result["orders"],
                "repetition": result["repetition"],
                "elapsed_seconds": result["elapsed"],
                "throughput_orders_per_sec": result["throughput"],
                "average_latency_ms": result["average_latency"],
                "p50_latency_ms": result["p50_latency"],
                "p95_latency_ms": result["p95_latency"],
                "p99_latency_ms": result["p99_latency"],
                "trades": result["trades"],
            }

            writer.writerow(row)

    print(f"\nResults saved to: {RESULTS_FILE}")


def main() -> None:

    parser = argparse.ArgumentParser(
        description="ChronosMatch matching execution benchmark"
    )

    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[1000, 2500, 5000],
    )

    args = parser.parse_args()

    for count in args.sizes:
        if count <= 0:
            parser.error(
                "All benchmark sizes must be positive"
            )

    print("\nCHRONOSMATCH - REPEATABLE MATCHING EXECUTION BENCHMARK")
    print("=" * 105)

    all_results = []

    for count in args.sizes:

        print(f"\nOrders: {count}")
        print("Warm-up...")

        # Warm-up is excluded from measured results.
        run_matching_benchmark(count)

        repetitions = []

        for repetition in range(1, REPETITIONS + 1):

            result = run_matching_benchmark(count)

            result["run_date"] = datetime.now().isoformat(
                timespec="seconds"
            )

            result["scenario"] = "matching_execution"
            result["repetition"] = repetition

            repetitions.append(result)
            all_results.append(result)

        print(
            f"Average throughput: "
            f"{statistics.mean(r['throughput'] for r in repetitions):,.2f} orders/sec"
        )

        print(
            f"Average latency: "
            f"{statistics.mean(r['average_latency'] for r in repetitions):.6f} ms"
        )

        print(
            f"P50: {statistics.mean(r['p50_latency'] for r in repetitions):.6f} ms | "
            f"P95: {statistics.mean(r['p95_latency'] for r in repetitions):.6f} ms | "
            f"P99: {statistics.mean(r['p99_latency'] for r in repetitions):.6f} ms"
        )

        print(
            f"Trades per run: {repetitions[0]['trades']} | "
            f"Traded quantity: {repetitions[0]['traded_quantity']}"
        )

    save_results(all_results)

    print("\nMatching execution benchmark completed successfully.")


if __name__ == "__main__":
    main()
