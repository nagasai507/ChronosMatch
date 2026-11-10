
"""Order-book interface for live orders."""

from .models import Order, OrderSide


class OrderBook:
    """Container and priority access layer for live orders."""

    def __init__(self) -> None:
        self._bids: list[Order] = []
        self._asks: list[Order] = []

    def add_order(self, order: Order) -> None:
        """Insert an order while preserving price-time priority."""
        if order.remaining_quantity <= 0:
            return

        if order.side == OrderSide.BUY:
            orders = self._bids
            key = (-order.price, order.timestamp)

        elif order.side == OrderSide.SELL:
            orders = self._asks
            key = (order.price, order.timestamp)

        else:
            return

        # Find the correct insertion position using binary search.
        low = 0
        high = len(orders)

        while low < high:
            mid = (low + high) // 2
            current = orders[mid]

            if order.side == OrderSide.BUY:
                current_key = (-current.price, current.timestamp)
            else:
                current_key = (current.price, current.timestamp)

            if current_key <= key:
                low = mid + 1
            else:
                high = mid

        # Insert without sorting the entire list.
        orders.insert(low, order)

    def get_best_bid(self) -> Order | None:
        """Return the highest-priority live buy order."""
        for order in self._bids:
            if order.remaining_quantity > 0:
                return order
        return None

    def get_best_ask(self) -> Order | None:
        """Return the lowest-priority live sell order."""
        for order in self._asks:
            if order.remaining_quantity > 0:
                return order
        return None

    def remove_order(self, order_id: str) -> bool:
        """Remove an order by ID; return True if found."""
        for orders in (self._bids, self._asks):
            for index, order in enumerate(orders):
                if order.order_id == order_id:
                    orders.pop(index)
                    return True
        return False
