from dataclasses import dataclass
from datetime import datetime


@dataclass
class Order:
    timestamp: datetime
    side: str               # "buy" or "sell"
    quantity: float
    order_type: str = "market"
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass
class Fill:
    timestamp: datetime
    side: str
    price: float
    quantity: float
    commission: float


@dataclass
class Position:
    side: str               # "long" or "short"
    entry_fill: Fill
    quantity: float
    stop_loss: float | None = None
    take_profit: float | None = None


class Trade:
    """Represents a completed trade (entry + exit)."""

    def __init__(self, entry_fill: Fill, exit_fill: Fill, side: str):
        self.entry_fill = entry_fill
        self.exit_fill = exit_fill
        self.side = side
        qty = entry_fill.quantity
        if side == "long":
            self.pnl = (exit_fill.price - entry_fill.price) * qty - entry_fill.commission - exit_fill.commission
        else:
            self.pnl = (entry_fill.price - exit_fill.price) * qty - entry_fill.commission - exit_fill.commission
        cost = entry_fill.price * qty
        self.return_pct = self.pnl / cost if cost != 0 else 0.0

    @property
    def quantity(self) -> float:
        return self.entry_fill.quantity
