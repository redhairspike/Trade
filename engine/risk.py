from engine.order import Position
import pandas as pd


def check_stop_loss(position: Position, current_bar: pd.Series) -> bool:
    """Check if stop-loss is hit for current bar."""
    if position.stop_loss is None:
        return False
    if position.side == "long":
        return current_bar["Low"] <= position.stop_loss
    else:  # short
        return current_bar["High"] >= position.stop_loss


def check_take_profit(position: Position, current_bar: pd.Series) -> bool:
    """Check if take-profit is hit for current bar."""
    if position.take_profit is None:
        return False
    if position.side == "long":
        return current_bar["High"] >= position.take_profit
    else:  # short
        return current_bar["Low"] <= position.take_profit


def calculate_stop_loss_price(
    entry_price: float,
    side: str,
    stop_loss_pct: float,
) -> float:
    """Calculate stop-loss price from percentage."""
    if side == "long":
        return entry_price * (1 - stop_loss_pct)
    else:
        return entry_price * (1 + stop_loss_pct)


def calculate_take_profit_price(
    entry_price: float,
    side: str,
    take_profit_pct: float,
) -> float:
    """Calculate take-profit price from percentage."""
    if side == "long":
        return entry_price * (1 + take_profit_pct)
    else:
        return entry_price * (1 - take_profit_pct)


def calculate_position_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float | None = None,
) -> float:
    """Calculate position size based on fixed-fractional risk.

    If stop_price is given, sizes the position so that the max loss
    equals capital * risk_pct. Otherwise, allocates capital * risk_pct
    worth of shares.
    """
    if stop_price is not None and stop_price != entry_price:
        risk_per_share = abs(entry_price - stop_price)
        max_risk = capital * risk_pct
        return max_risk / risk_per_share
    else:
        return (capital * risk_pct) / entry_price
