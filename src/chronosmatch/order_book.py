"""Order-book interface. Implementation owner: Member 2."""

from .models import Order, OrderSide


class OrderBook:
    """Container and priority access layer for live orders."""

    def __init__(self) -> None:
        self._bids: list[Order] = []
        self._asks: list[Order] = []

    def add_order(self, order: Order) -> None:
        """Add an unmatched order to the appropriate side."""
        if order.remaining_quantity <= 0:
            return

        if order.side == OrderSide.BUY:
            self._bids.append(order)
        elif order.side == OrderSide.SELL:
            self._asks.append(order)

    def get_best_bid(self) -> Order | None:
        """Return the highest-priority live buy order."""
        live_bids = [
            order for order in self._bids
            if order.remaining_quantity > 0
        ]

        if not live_bids:
            return None

        return min(
            live_bids,
            key=lambda order: (-order.price, order.timestamp)
        )

    def get_best_ask(self) -> Order | None:
        """Return the highest-priority live sell order."""
        live_asks = [
            order for order in self._asks
            if order.remaining_quantity > 0
        ]

        if not live_asks:
            return None

        return min(
            live_asks,
            key=lambda order: (order.price, order.timestamp)
        )

    def remove_order(self, order_id: str) -> bool:
        """Remove a live order by ID; return True if found."""
        for orders in (self._bids, self._asks):
            for index, order in enumerate(orders):
                if order.order_id == order_id:
                    orders.pop(index)
                    return True

        return False