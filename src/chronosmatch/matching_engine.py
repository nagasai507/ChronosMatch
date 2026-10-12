
"""Price-time-priority matching engine for ChronosMatch."""

from .models import Order, OrderSide, Trade
from .order_book import OrderBook


class MatchingEngine:
    """Match incoming orders against resting orders in the order book."""

    def __init__(self, order_book: OrderBook | None = None) -> None:
        self.order_book = order_book if order_book is not None else OrderBook()
        self.trades: list[Trade] = []
        self._next_trade_id = 1

    def submit_order(self, order: Order) -> list[Trade]:
        """Submit an order and return the trades created by this submission."""
        if not isinstance(order, Order):
            raise TypeError("order must be an Order instance")

        if order.remaining_quantity is None:
            order.remaining_quantity = order.quantity

        if order.remaining_quantity == 0:
            return []

        created_trades: list[Trade] = []

        while order.remaining_quantity > 0:
            if order.side == OrderSide.BUY:
                resting_order = self.order_book.get_best_ask()

                if resting_order is None or order.price < resting_order.price:
                    break

            elif order.side == OrderSide.SELL:
                resting_order = self.order_book.get_best_bid()

                if resting_order is None or order.price > resting_order.price:
                    break

            else:
                raise ValueError(f"Unsupported order side: {order.side!r}")

            if resting_order.remaining_quantity is None:
                resting_order.remaining_quantity = resting_order.quantity

            if resting_order.remaining_quantity <= 0:
                self.order_book.remove_order(resting_order.order_id)
                continue

            executed_quantity = min(
                order.remaining_quantity,
                resting_order.remaining_quantity,
            )

            execution_price = resting_order.price

            if order.side == OrderSide.BUY:
                buy_order_id = order.order_id
                sell_order_id = resting_order.order_id
            else:
                buy_order_id = resting_order.order_id
                sell_order_id = order.order_id

            trade = Trade(
                trade_id=str(self._next_trade_id),
                buy_order_id=buy_order_id,
                sell_order_id=sell_order_id,
                price=execution_price,
                quantity=executed_quantity,
                timestamp=order.timestamp,
            )
            self._next_trade_id += 1

            order.remaining_quantity -= executed_quantity
            resting_order.remaining_quantity -= executed_quantity

            created_trades.append(trade)
            self.trades.append(trade)

            if resting_order.remaining_quantity == 0:
                self.order_book.remove_order(resting_order.order_id)

        if order.remaining_quantity > 0:
            self.order_book.add_order(order)

        return created_trades
