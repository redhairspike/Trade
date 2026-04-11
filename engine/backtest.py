from dataclasses import dataclass
import pandas as pd
from engine.order import Order, Trade
from engine.portfolio import Portfolio
from engine.risk import calculate_stop_loss_price, calculate_take_profit_price
from strategy.strategy import Strategy
from metrics.performance import compute_metrics


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: list[Trade]
    prepared_df: pd.DataFrame
    metrics: dict


class BacktestEngine:
    def __init__(
        self,
        df: pd.DataFrame,
        strategy: Strategy,
        portfolio: Portfolio,
    ):
        self.df = df
        self.strategy = strategy
        self.portfolio = portfolio

    def run(self) -> BacktestResult:
        """Run the backtest bar by bar."""
        # Step 1: Compute indicators
        prepared_df = self.strategy.prepare(self.df)

        # Step 2: Bar-by-bar loop
        for i in range(1, len(prepared_df)):
            current_bar = prepared_df.iloc[i]
            prev_bar = prepared_df.iloc[i - 1]

            # 2a: Check stop-loss / take-profit
            if self.portfolio.position is not None:
                risk_signal = self.portfolio.check_risk(current_bar)
                if risk_signal == "stop_loss":
                    exit_price = self.portfolio.position.stop_loss
                    self.portfolio.close_position(current_bar, exit_price)
                elif risk_signal == "take_profit":
                    exit_price = self.portfolio.position.take_profit
                    self.portfolio.close_position(current_bar, exit_price)

            # 2b: Check strategy exit signals
            if self.portfolio.position is not None:
                if self.strategy.check_exit(current_bar, prev_bar, self.portfolio.position.side):
                    self.portfolio.close_position(current_bar)

            # 2c: Check strategy entry signals
            if self.portfolio.position is None:
                direction = self.strategy.check_entry(current_bar, prev_bar)
                if direction is not None:
                    self._enter_position(direction, current_bar)

            # 2d: Update equity curve
            self.portfolio.update_equity(current_bar.name, current_bar["Close"])

        # Step 3: Force-close open positions at last bar
        if self.portfolio.position is not None:
            self.portfolio.close_position(prepared_df.iloc[-1])

        # Build results
        equity_df = pd.DataFrame(self.portfolio.equity_curve)
        if not equity_df.empty:
            equity_df = equity_df.set_index("date")

        metrics = compute_metrics(equity_df, self.portfolio.trades)

        return BacktestResult(
            equity_curve=equity_df,
            trades=self.portfolio.trades,
            prepared_df=prepared_df,
            metrics=metrics,
        )

    def _enter_position(self, direction: str, current_bar: pd.Series):
        """Create and execute an entry order."""
        entry_price = current_bar["Open"]

        # Calculate position size
        qty = (self.portfolio.cash * self.strategy.position_size_pct) / entry_price
        if qty <= 0:
            return

        side = "buy" if direction == "long" else "sell"
        order = Order(
            timestamp=current_bar.name,
            side=side,
            quantity=qty,
        )

        fill = self.portfolio.execute_order(order, current_bar)

        # Calculate stop-loss and take-profit prices
        sl_price = None
        tp_price = None
        if self.strategy.stop_loss_pct is not None:
            sl_price = calculate_stop_loss_price(
                fill.price, direction, self.strategy.stop_loss_pct
            )
        if self.strategy.take_profit_pct is not None:
            tp_price = calculate_take_profit_price(
                fill.price, direction, self.strategy.take_profit_pct
            )

        self.portfolio.open_position(fill, direction, sl_price, tp_price)
