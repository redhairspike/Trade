import pandas as pd
from indicators.base import register


@register("MA", {"period": 20})
def ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Simple Moving Average."""
    result = df["Close"].rolling(window=period).mean()
    result.name = "MA"
    return result


@register("EMA", {"period": 20})
def ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Exponential Moving Average."""
    result = df["Close"].ewm(span=period, adjust=False).mean()
    result.name = "EMA"
    return result
