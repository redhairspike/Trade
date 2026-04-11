import pandas as pd
import numpy as np
from strategy.signal import Signal, Rule, MAFilter
from indicators.base import compute


# Internal column names for filter MAs (prefixed to avoid collision)
_FILTER_POS_COL = "_filter_ma_pos"
_FILTER_DIR_COL = "_filter_ma_dir"


class Strategy:
    def __init__(
        self,
        signal: Signal,
        stop_loss_pct: float | None = None,
        take_profit_pct: float | None = None,
        position_size_pct: float = 1.0,
    ):
        self.signal = signal
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.position_size_pct = position_size_pct

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all needed indicators and attach columns to df."""
        df = df.copy()
        all_rules = self.signal.entry_rules + self.signal.exit_rules
        computed = set()

        for rule in all_rules:
            key = (rule.indicator, frozenset(rule.params.items()))
            if key in computed:
                continue
            computed.add(key)

            result = compute(rule.indicator, df, **rule.params)
            if isinstance(result, pd.DataFrame):
                for col in result.columns:
                    df[col] = result[col]
            else:
                col_name = result.name or rule.indicator
                df[col_name] = result

            # If value references another indicator field, compute it too
            if isinstance(rule.value, str) and rule.value not in df.columns:
                # value might be like "EMA" referencing another indicator
                pass

        # Compute MA filter columns
        df = self._compute_ma_filters(df)

        return df

    def _compute_ma_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute MA columns needed by position/direction filters."""
        pos_filter = self.signal.ma_position_filter
        dir_filter = self.signal.ma_direction_filter

        # Position filter MA
        if pos_filter.enabled:
            df[_FILTER_POS_COL] = self._calc_ma(df, pos_filter.ma_type, pos_filter.period)

        # Direction filter MA
        if dir_filter.enabled:
            ma_series = self._calc_ma(df, dir_filter.ma_type, dir_filter.period)
            df[_FILTER_DIR_COL] = ma_series
            # Slope: current MA - previous MA (positive = trending up)
            df[_FILTER_DIR_COL + "_slope"] = ma_series.diff()

        return df

    @staticmethod
    def _calc_ma(df: pd.DataFrame, ma_type: str, period: int) -> pd.Series:
        """Calculate MA or EMA on Close."""
        if ma_type == "EMA":
            return df["Close"].ewm(span=period, adjust=False).mean()
        else:
            return df["Close"].rolling(window=period).mean()

    def _eval_rule(self, rule: Rule, row: pd.Series, prev_row: pd.Series) -> bool:
        """Evaluate a single rule against current and previous bar."""
        field_val = row.get(rule.field)
        if field_val is None or pd.isna(field_val):
            return False

        # Determine comparison value
        if isinstance(rule.value, str) and rule.value in row.index:
            comp_val = row[rule.value]
            prev_comp = prev_row.get(rule.value) if prev_row is not None else None
        else:
            comp_val = float(rule.value)
            prev_comp = comp_val

        if pd.isna(comp_val):
            return False

        prev_field = prev_row.get(rule.field) if prev_row is not None else None

        if rule.operator == ">":
            return field_val > comp_val
        elif rule.operator == "<":
            return field_val < comp_val
        elif rule.operator == ">=":
            return field_val >= comp_val
        elif rule.operator == "<=":
            return field_val <= comp_val
        elif rule.operator == "crosses_above":
            if prev_field is None or pd.isna(prev_field) or prev_comp is None or pd.isna(prev_comp):
                return False
            return prev_field <= prev_comp and field_val > comp_val
        elif rule.operator == "crosses_below":
            if prev_field is None or pd.isna(prev_field) or prev_comp is None or pd.isna(prev_comp):
                return False
            return prev_field >= prev_comp and field_val < comp_val

        return False

    def _check_ma_filters(self, row: pd.Series, prev_row: pd.Series, direction: str) -> bool:
        """Check MA filter conditions. Returns True if filters pass."""
        pos_filter = self.signal.ma_position_filter
        dir_filter = self.signal.ma_direction_filter

        # Position filter: Close vs MA
        if pos_filter.enabled:
            ma_val = row.get(_FILTER_POS_COL)
            if ma_val is None or pd.isna(ma_val):
                return False
            close = row["Close"]
            if direction == "long" and close <= ma_val:
                return False  # 做多需要收盤價在 MA 之上
            if direction == "short" and close >= ma_val:
                return False  # 做空需要收盤價在 MA 之下

        # Direction filter: MA slope
        if dir_filter.enabled:
            slope = row.get(_FILTER_DIR_COL + "_slope")
            if slope is None or pd.isna(slope):
                return False
            if direction == "long" and slope <= 0:
                return False  # 做多需要 MA 方向上彎
            if direction == "short" and slope >= 0:
                return False  # 做空需要 MA 方向下彎

        return True

    def check_entry(self, row: pd.Series, prev_row: pd.Series) -> str | None:
        """Check if entry conditions are met. Returns 'long', 'short', or None."""
        if not self.signal.entry_rules:
            return None

        direction = self.signal.direction

        # Check MA filters first (gate conditions)
        if not self._check_ma_filters(row, prev_row, direction):
            return None

        # All entry rules must be true (AND logic)
        if all(self._eval_rule(r, row, prev_row) for r in self.signal.entry_rules):
            return direction
        return None

    def check_exit(self, row: pd.Series, prev_row: pd.Series, position_side: str) -> bool:
        """Check if exit conditions are met. Any rule triggers exit (OR logic)."""
        if not self.signal.exit_rules:
            return False
        return any(self._eval_rule(r, row, prev_row) for r in self.signal.exit_rules)
