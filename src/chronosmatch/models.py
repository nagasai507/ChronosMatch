"""Shared data contracts for the ChronosMatch modules."""

from dataclasses import dataclass
from enum import Enum


class OrderSide(str, Enum):
    """Side of an order in the book."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(slots=True)
class Order:
    """An order submitted to the simulated matching engine.

    Prices are integer ticks, not floats, to avoid floating-point comparisons.
    Quantities are integer units. The engine may update remaining_quantity.
    """

    order_id: str
    side: OrderSide
    price: int
    quantity: int
    timestamp: int = 0
    remaining_quantity: int | None = None

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValueError("order_id must not be empty")
        if not isinstance(self.side, OrderSide):
            raise TypeError("side must be an OrderSide value")
        if not isinstance(self.price, int) or isinstance(self.price, bool):
            raise TypeError("price must be an integer")
        if self.price <= 0:
            raise ValueError("price must be a positive integer tick")
        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool):
            raise TypeError("quantity must be an integer")
        if self.quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        if self.timestamp < 0:
            raise ValueError("timestamp must not be negative")
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
        if not 0 <= self.remaining_quantity <= self.quantity:
            raise ValueError("remaining_quantity must be between zero and quantity")


@dataclass(frozen=True, slots=True)
class Trade:
    """A completed execution between one buy order and one sell order."""

    trade_id: str
    buy_order_id: str
    sell_order_id: str
    price: int
    quantity: int
    timestamp: int = 0

    def __post_init__(self) -> None:
        if not self.trade_id.strip():
            raise ValueError("trade_id must not be empty")
        if not self.buy_order_id.strip() or not self.sell_order_id.strip():
            raise ValueError("trade order IDs must not be empty")
        if not isinstance(self.price, int) or isinstance(self.price, bool):
            raise TypeError("trade price must be an integer")
        if self.price <= 0:
            raise ValueError("trade price must be positive")
        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool):
            raise TypeError("trade quantity must be an integer")
        if self.quantity <= 0:
            raise ValueError("trade quantity must be positive")
        if self.timestamp < 0:
            raise ValueError("timestamp must not be negative")
