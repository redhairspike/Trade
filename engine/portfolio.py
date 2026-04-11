import pandas as pd
from engine.order import Order, Fill, Position, Trade
from engine.risk import (
    check_stop_loss,
    check_take_profit,
    calculate_stop_loss_price,
    calculate_take_profit_price,
)


class Portfolio:
    def __init__(
        self,
        initial_capital: float,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.position: Position | None = None
        self.trades: list[Trade] = []
        self.equity_curve: list[dict] = []

    def execute_order(self, order: Order, current_bar: pd.Series) -> Fill:
        """Execute an order with slippage and commission."""
        base_price = current_bar["Open"]

        # Apply slippage
        if order.side == "buy":
            fill_price = base_price * (1 + self.slippage_rate)
        else:
            fill_price = base_price * (1 - self.slippage_rate)

        commission = fill_price * order.quantity * self.commission_rate

        fill = Fill(
            timestamp=order.timestamp,
            side=order.side,
            price=fill_price,
            quantity=order.quantity,
            commission=commission,
        )

        if order.side == "buy":
            self.cash -= fill_price * order.quantity + commission
        else:
            self.cash += fill_price * order.quantity - commission

        return fill

    def open_position(
        self,
        fill: Fill,
        side: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ):
        """Open a new position from a fill."""
        self.position = Position(
            side=side,
            entry_fill=fill,
            quantity=fill.quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    def close_position(self, current_bar: pd.Series, exit_price: float | None = None) -> Trade:
        """Close the current position and record trade."""
        pos = self.position
        exit_side = "sell" if pos.side == "long" else "buy"

        price = exit_price or current_bar["Open"]
        if exit_side == "sell":
            fill_price = price * (1 - self.slippage_rate)
        else:
            fill_price = price * (1 + self.slippage_rate)

        commission = fill_price * pos.quantity * self.commission_rate

        exit_fill = Fill(
            timestamp=current_bar.name,
            side=exit_side,
            price=fill_price,
            quantity=pos.quantity,
            commission=commission,
        )

        if exit_side == "sell":
            self.cash += fill_price * pos.quantity - commission
        else:
            self.cash -= fill_price * pos.quantity + commission

        trade = Trade(
            entry_fill=pos.entry_fill,
            exit_fill=exit_fill,
            side=pos.side,
        )
        self.trades.append(trade)
        self.position = None
        return trade

    def update_equity(self, timestamp, current_price: float):
        """Record current equity value."""
        equity = self.cash
        if self.position is not None:
            if self.position.side == "long":
                equity += current_price * self.position.quantity
            else:
                # Short: profit when price drops
                entry_val = self.position.entry_fill.price * self.position.quantity
                current_val = current_price * self.position.quantity
                equity += entry_val + (entry_val - current_val)
        self.equity_curve.append({"date": timestamp, "equity": equity})

    def check_risk(self, current_bar: pd.Series) -> str | None:
        """Check stop-loss and take-profit on open position.

        Returns 'stop_loss', 'take_profit', or None.
        """
        if self.position is None:
            return None
        if check_stop_loss(self.position, current_bar):
            return "stop_loss"
        if check_take_profit(self.position, current_bar):
            return "take_profit"
        return None
