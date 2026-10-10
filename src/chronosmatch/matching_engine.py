"""Matching-engine interface. Implementation owner: Member 3."""

from .models import Order, Trade
from .order_book import OrderBook


class MatchingEngine:
    """Accept orders, execute compatible orders and record trades."""

    def __init__(self, order_book: OrderBook | None = None) -> None:
        self.order_book = order_book if order_book is not None else OrderBook()
        self.trades: list[Trade] = []
        self._next_trade_id = 1

    def submit_order(self, order: Order) -> list[Trade]:
        """Submit an order and return trades created by this submission.

        TODO(Member 3): implement price-time matching, partial fills, trade records,
        and adding any remaining quantity to the order book.
        """
        raise NotImplementedError("Member 3: implement MatchingEngine.submit_order")
