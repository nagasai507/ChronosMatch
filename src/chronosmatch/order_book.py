"""Order-book interface for live orders."""

from .models import Order, OrderSide


class OrderBook:
    """Container and priority access layer for live orders."""

    def __init__(self) -> None:
        self._bids: list[Order] = []
        self._asks: list[Order] = []

    def add_order(self, order: Order) -> None:
        """Add an order to the appropriate side."""
        if order.remaining_quantity <= 0:
            return

        if order.side == OrderSide.BUY:
            self._bids.append(order)
            self._bids.sort(
                key=lambda o: (-o.price, o.timestamp)
            )
        elif order.side == OrderSide.SELL:
            self._asks.append(order)
            self._asks.sort(
                key=lambda o: (o.price, o.timestamp)
            )

    def get_best_bid(self) -> Order | None:
        """Return the highest-priority live buy order."""
        for order in self._bids:
            if order.remaining_quantity > 0:
                return order
        return None

    def get_best_ask(self) -> Order | None:
        """Return the highest-priority live sell order."""
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