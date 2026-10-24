
"""Asynchronous mock market-order generator."""

import asyncio
import random
from collections.abc import AsyncIterator

from .models import Order, OrderSide


class MarketSimulator:
    """Generate a stream of mock BUY and SELL orders."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)
        self._next_order_id = 1
        self._timestamp = 0

    def _generate_order(self) -> Order:
        """Generate one mock order."""
        side = self._random.choice((OrderSide.BUY, OrderSide.SELL))
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
        yield_every: int = 1,
    ) -> AsyncIterator[Order]:
        """Generate orders, periodically yielding to the event loop."""

        if isinstance(yield_every, bool) or not isinstance(yield_every, int):
            raise TypeError("yield_every must be an integer")

        if yield_every <= 0:
            raise ValueError("yield_every must be positive")

        if count is not None:
            if isinstance(count, bool) or not isinstance(count, int):
                raise TypeError("count must be an integer or None")

            if count < 0:
                raise ValueError("count must not be negative")

        generated = 0

        while count is None or generated < count:
            yield self._generate_order()
            generated += 1

            if generated % yield_every == 0:
                await asyncio.sleep(0)
