"""Asynchronous mock market-order generator."""

import asyncio
import random
from collections.abc import AsyncIterator

from .models import Order, OrderSide


class MarketSimulator:
    """Generate a stream of realistic mock BUY and SELL orders."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)
        self._next_order_id = 1
        self._timestamp = 0

    def _generate_order(self) -> Order:
        """Generate one mock market order."""
        side = self._random.choice([OrderSide.BUY, OrderSide.SELL])
        price = self._random.randint(95, 105)
        quantity = self._random.randint(1, 100)

        order = Order(
            order_id=f"SIM-{self._next_order_id}",
            side=side,
            price=price,
            quantity=quantity,
            timestamp=self._timestamp,
        )

        self._next_order_id += 1
        self._timestamp += 1

        return order

    async def generate_orders(
        self,
        count: int | None = None,
    ) -> AsyncIterator[Order]:
        """Asynchronously generate mock orders."""
        generated = 0

        while count is None or generated < count:
            yield self._generate_order()
            generated += 1
            await asyncio.sleep(0)