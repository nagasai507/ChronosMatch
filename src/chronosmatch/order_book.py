"""Order-book interface. Implementation owner: Member 2.

Required behavior:
- keep buy and sell orders separate;
- best bid is the highest-priced live buy order;
- best ask is the lowest-priced live sell order;
- at equal prices, older accepted orders have priority (FIFO);
- never expose orders whose remaining quantity is zero.
"""

from .models import Order


class OrderBook:
    """Container and priority access layer for live orders."""

    def __init__(self) -> None:
        self._bids: list[Order] = []
        self._asks: list[Order] = []

    def add_order(self, order: Order) -> None:
        """Add an unmatched order to the appropriate side."""
        raise NotImplementedError("Member 2: implement OrderBook.add_order")

    def get_best_bid(self) -> Order | None:
        """Return the highest-priority live buy order, or None if there is no bid."""
        raise NotImplementedError("Member 2: implement OrderBook.get_best_bid")

    def get_best_ask(self) -> Order | None:
        """Return the highest-priority live sell order, or None if there is no ask."""
        raise NotImplementedError("Member 2: implement OrderBook.get_best_ask")

    def remove_order(self, order_id: str) -> bool:
        """Remove a live order by ID; return True if it was found."""
        raise NotImplementedError("Member 2: implement OrderBook.remove_order")
