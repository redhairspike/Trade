import pandas as pd
import numpy as np
from indicators.base import register


@register("Bollinger", {"period": 20, "std_dev": 2.0})
def bbands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bands."""
    middle = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return pd.DataFrame({
        "BB_upper": upper,
        "BB_middle": middle,
        "BB_lower": lower,
    }, index=df.index)


@register("ATR", {"period": 14})
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    result = true_range.rolling(window=period).mean()
    result.name = "ATR"
    return result
