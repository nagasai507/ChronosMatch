# ChronosMatch shared interface contract

This is the agreement between the four workstreams. Read it before coding a module
that imports another member's work. Discuss changes in the team chat first.

## Shared model — Member 1

Module: `src/chronosmatch/models.py`

### `OrderSide`
- `OrderSide.BUY`
- `OrderSide.SELL`

### `Order`
Fields: `order_id: str`, `side: OrderSide`, `price: int`, `quantity: int`,
`timestamp: int = 0`, `remaining_quantity: int | None = None`.

- Prices are integer ticks; do not use floats for price comparisons.
- Quantities are positive integers.
- `remaining_quantity` starts equal to `quantity`.
- The engine may reduce `remaining_quantity` after a fill.

### `Trade`
Fields: `trade_id`, `buy_order_id`, `sell_order_id`, `price`, `quantity`,
and `timestamp`.

## Order book — Member 2

Module: `src/chronosmatch/order_book.py`

Public methods:
- `add_order(order: Order) -> None`
- `get_best_bid() -> Order | None`
- `get_best_ask() -> Order | None`
- `remove_order(order_id: str) -> bool`

Rules:
- Highest buy price has priority; lowest sell price has priority.
- At the same price, preserve FIFO by accepted/sequence order.
- Orders with no remaining quantity must not be returned as best orders.
- The book stores only the unmatched remainder after the engine has tried to match.

## Matching engine — Member 3

Module: `src/chronosmatch/matching_engine.py`

Public method:
- `submit_order(order: Order) -> list[Trade]`

Rules:
- A buy can match the best ask when buy price >= ask price.
- A sell can match the best bid when sell price <= bid price.
- Match at the resting order's price unless the team documents a different rule.
- Each fill reduces both orders' remaining quantities.
- Each fill creates one Trade with positive quantity.
- Add the incoming order to the book only if it has remaining quantity.
- Return only the trades created by this submission.

## Integration and tests — Member 4

- Add unit tests for each module and end-to-end tests for the engine.
- Required scenarios: no match, exact fill, partial fill, one incoming order filling
  multiple resting orders, FIFO at equal prices, best-price selection, invalid input.
- Verify that executed quantity never exceeds either order's quantity.
- Run `pytest` before requesting integration.

## Change process

If an interface needs to change, raise it with the team first, update this document,
then update dependent code and tests in the same reviewed change.
