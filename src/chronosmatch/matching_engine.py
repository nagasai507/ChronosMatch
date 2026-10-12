
"""Matching engine for order execution and trade recording."""

from .models import Order, OrderSide, Trade
from .order_book import OrderBook


class MatchingEngine:
    """Accept orders, execute compatible orders and record trades."""

    def __init__(self, order_book: OrderBook | None = None) -> None:
        self.order_book = order_book if order_book is not None else OrderBook()
        self.trades: list[Trade] = []
        self._next_trade_id = 1

    def submit_order(self, order: Order) -> list[Trade]:
        """Match an incoming order, record trades and store any remainder."""
        created_trades: list[Trade] = []

        while order.remaining_quantity > 0:
            if order.side == OrderSide.BUY:
                resting_order = self.order_book.get_best_ask()

                if resting_order is None or order.price < resting_order.price:
                    break

                buy_order = order
                sell_order = resting_order
            else:
                resting_order = self.order_book.get_best_bid()

                if resting_order is None or order.price > resting_order.price:
                    break

                buy_order = resting_order
                sell_order = order

            matched_quantity = min(
                order.remaining_quantity,
                resting_order.remaining_quantity,
            )

            trade = Trade(
                trade_id=f"T{self._next_trade_id}",
                buy_order_id=buy_order.order_id,
                sell_order_id=sell_order.order_id,
                price=resting_order.price,
                quantity=matched_quantity,
                timestamp=order.timestamp,
            )

            self._next_trade_id += 1
            created_trades.append(trade)
            self.trades.append(trade)

            order.remaining_quantity -= matched_quantity
            resting_order.remaining_quantity -= matched_quantity

            if resting_order.remaining_quantity == 0:
                self.order_book.remove_order(resting_order.order_id)

        if order.remaining_quantity > 0:
            self.order_book.add_order(order)

        return created_trades