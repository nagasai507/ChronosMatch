
"""Repeatable insertion benchmark for the ChronosMatch matching engine."""

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


def create_orders(count: int) -> list[Order]:
    """Prepare non-crossing orders outside the timed section."""
    orders = []

    for i in range(count):
        if i % 2 == 0:
            side, price = OrderSide.BUY, 90 + (i % 10)
        else:
            side, price = OrderSide.SELL, 110 + (i % 10)

        orders.append(
            Order(
                order_id=f"BENCH-{i}",
                side=side,
                price=price,
                quantity=10,
                timestamp=i,
            )
        )

    return orders


def percentile(values: list[int], percent: float) -> float:
    """Return nearest-rank percentile in milliseconds."""
    ordered = sorted(values)
    index = max(0, math.ceil(percent * len(ordered)) - 1)
    return ordered[index] / 1_000_000


def run_once(count: int) -> dict:
    """Run one complete insertion benchmark."""
    engine = MatchingEngine()
    orders = create_orders(count)
    latencies = []
    total_trades = 0

    start_all = time.perf_counter_ns()

    for order in orders:
        start = time.perf_counter_ns()
        trades = engine.submit_order(order)
        end = time.perf_counter_ns()

        latencies.append(end - start)
        total_trades += len(trades)

    elapsed = (
        time.perf_counter_ns() - start_all
    ) / 1_000_000_000

    # Correctness checks for the non-crossing workload.
    assert total_trades == 0, (
        "Unexpected trade in non-crossing workload"
    )

    assert (
        len(engine.order_book._bids)
        + len(engine.order_book._asks)
        == count
    ), "Some orders were not retained in the order book"

    assert all(
        order.remaining_quantity == 10
        for order in orders
    ), "Unexpected order quantity change"

    return {
        "orders": count,
        "elapsed": elapsed,
        "throughput": count / elapsed,
        "average_latency": statistics.mean(latencies) / 1_000_000,
        "p50_latency": percentile(latencies, 0.50),
        "p95_latency": percentile(latencies, 0.95),
        "p99_latency": percentile(latencies, 0.99),
        "trades": total_trades,
    }


def save_results(results: list[dict]) -> None:
    """Append benchmark repetitions to a CSV file."""

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ChronosMatch insertion benchmark"
    )

    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[1000, 2500, 5000],
        help="Order counts to benchmark"
    )

    args = parser.parse_args()

    for count in args.sizes:
        if count <= 0:
            parser.error(
                "All benchmark sizes must be positive"
            )

    print("\nCHRONOSMATCH - REPEATABLE INSERTION BENCHMARK")
    print("=" * 105)

    all_results = []

    for count in args.sizes:

        print(f"\nOrders: {count}")
        print("Warm-up...")

        # One warm-up run, excluded from measurements.
        run_once(count)

        repetitions = []

        # Five measured runs.
        for repetition in range(1, REPETITIONS + 1):

            result = run_once(count)

            result["run_date"] = datetime.now().isoformat(
                timespec="seconds"
            )

            result["scenario"] = "non_crossing_insertion"
            result["repetition"] = repetition

            repetitions.append(result)
            all_results.append(result)

        avg_throughput = statistics.mean(
            r["throughput"] for r in repetitions
        )

        avg_latency = statistics.mean(
            r["average_latency"] for r in repetitions
        )

        avg_p50 = statistics.mean(
            r["p50_latency"] for r in repetitions
        )

        avg_p95 = statistics.mean(
            r["p95_latency"] for r in repetitions
        )

        avg_p99 = statistics.mean(
            r["p99_latency"] for r in repetitions
        )

        print(
            f"Average throughput: "
            f"{avg_throughput:,.2f} orders/sec"
        )

        print(
            f"Average latency: "
            f"{avg_latency:.6f} ms"
        )

        print(
            f"P50: {avg_p50:.6f} ms | "
            f"P95: {avg_p95:.6f} ms | "
            f"P99: {avg_p99:.6f} ms"
        )

    save_results(all_results)

    print("\nBenchmark completed successfully.")
    print(f"Results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
