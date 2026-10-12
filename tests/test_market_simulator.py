import asyncio

from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.models import OrderSide


def test_generates_requested_number_of_orders():
    async def run_test():
        simulator = MarketSimulator(seed=42)

        orders = [
            order
            async for order in simulator.generate_orders(count=10)
        ]

        assert len(orders) == 10

    asyncio.run(run_test())


def test_generated_orders_have_valid_fields():
    async def run_test():
        simulator = MarketSimulator(seed=42)

        orders = [
            order
            async for order in simulator.generate_orders(count=20)
        ]

        assert all(order.order_id.startswith("SIM-") for order in orders)
        assert all(order.side in (OrderSide.BUY, OrderSide.SELL) for order in orders)
        assert all(95 <= order.price <= 105 for order in orders)
        assert all(1 <= order.quantity <= 100 for order in orders)

    asyncio.run(run_test())


def test_generated_order_ids_are_unique():
    async def run_test():
        simulator = MarketSimulator(seed=42)

        orders = [
            order
            async for order in simulator.generate_orders(count=100)
        ]

        order_ids = [order.order_id for order in orders]

        assert len(order_ids) == len(set(order_ids))

    asyncio.run(run_test())


def test_timestamps_are_increasing():
    async def run_test():
        simulator = MarketSimulator(seed=42)

        orders = [
            order
            async for order in simulator.generate_orders(count=10)
        ]

        timestamps = [order.timestamp for order in orders]

        assert timestamps == list(range(10))

    asyncio.run(run_test())