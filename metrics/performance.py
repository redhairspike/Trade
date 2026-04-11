import numpy as np
import pandas as pd
from engine.order import Trade
from config import TRADING_DAYS_PER_YEAR, DEFAULT_RISK_FREE_RATE


def compute_metrics(
    equity_curve: pd.DataFrame,
    trades: list[Trade],
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> dict:
    """Compute all performance metrics from equity curve and trades."""
    metrics = {}

    if equity_curve.empty or "equity" not in equity_curve.columns:
        return _empty_metrics()

    equity = equity_curve["equity"]

    # Returns
    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    n_days = len(equity)
    annualized_return = (1 + total_return) ** (TRADING_DAYS_PER_YEAR / max(n_days, 1)) - 1

    # Daily returns
    daily_returns = equity.pct_change().dropna()

    # Sharpe ratio (annualized)
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        daily_rf = (1 + risk_free_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        excess = daily_returns - daily_rf
        sharpe = excess.mean() / excess.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        sharpe = 0.0

    # Max drawdown
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_drawdown = drawdown.min()

    # Max drawdown duration (in bars)
    in_dd = equity < cummax
    if in_dd.any():
        dd_groups = (~in_dd).cumsum()
        dd_lengths = in_dd.groupby(dd_groups).sum()
        max_dd_duration = int(dd_lengths.max()) if len(dd_lengths) > 0 else 0
    else:
        max_dd_duration = 0

    # Trade statistics
    trade_count = len(trades)
    if trade_count > 0:
        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        win_rate = len(wins) / trade_count
        avg_trade_return = np.mean([t.return_pct for t in trades])
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        long_count = sum(1 for t in trades if t.side == "long")
        short_count = sum(1 for t in trades if t.side == "short")
    else:
        win_rate = 0.0
        avg_trade_return = 0.0
        profit_factor = 0.0
        long_count = 0
        short_count = 0

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "max_drawdown_duration": max_dd_duration,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trade_count": trade_count,
        "avg_trade_return": avg_trade_return,
        "long_count": long_count,
        "short_count": short_count,
    }


def _empty_metrics() -> dict:
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_duration": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "trade_count": 0,
        "avg_trade_return": 0.0,
        "long_count": 0,
        "short_count": 0,
    }
