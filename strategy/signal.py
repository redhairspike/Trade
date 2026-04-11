from dataclasses import dataclass, field


@dataclass
class Rule:
    indicator: str          # e.g. "RSI"
    params: dict            # e.g. {"period": 14}
    field: str              # output column name, e.g. "RSI", "MACD_line"
    operator: str           # ">", "<", ">=", "<=", "crosses_above", "crosses_below"
    value: float | str      # threshold number OR another column name


@dataclass
class MAFilter:
    """MA-based entry filter (gate condition)."""
    enabled: bool = False
    period: int = 20
    ma_type: str = "MA"     # "MA" or "EMA"


@dataclass
class Signal:
    direction: str          # "long" or "short"
    entry_rules: list[Rule] = field(default_factory=list)
    exit_rules: list[Rule] = field(default_factory=list)
    ma_position_filter: MAFilter = field(default_factory=MAFilter)   # price vs MA
    ma_direction_filter: MAFilter = field(default_factory=MAFilter)  # MA slope
