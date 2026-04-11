import pandas as pd
from typing import Callable

INDICATOR_REGISTRY: dict[str, dict] = {}


def register(name: str, params: dict):
    """Decorator to register an indicator function.

    Args:
        name: Display name (e.g. "RSI")
        params: Default parameters dict (e.g. {"period": 14})
    """
    def decorator(func: Callable):
        INDICATOR_REGISTRY[name] = {
            "func": func,
            "params": params,
        }
        return func
    return decorator


def compute(name: str, df: pd.DataFrame, **kwargs) -> pd.Series | pd.DataFrame:
    """Compute an indicator by name with given parameters."""
    if name not in INDICATOR_REGISTRY:
        raise ValueError(f"Unknown indicator: {name}")
    entry = INDICATOR_REGISTRY[name]
    params = {**entry["params"], **kwargs}
    return entry["func"](df, **params)


def get_indicator_names() -> list[str]:
    """Return list of all registered indicator names."""
    return list(INDICATOR_REGISTRY.keys())


def get_indicator_params(name: str) -> dict:
    """Return default parameters for an indicator."""
    if name not in INDICATOR_REGISTRY:
        raise ValueError(f"Unknown indicator: {name}")
    return INDICATOR_REGISTRY[name]["params"].copy()


def get_indicator_fields(name: str, df: pd.DataFrame = None, **kwargs) -> list[str]:
    """Return output column names for an indicator."""
    if df is None:
        # Return expected field names based on convention
        field_map = {
            "MA": ["MA"],
            "EMA": ["EMA"],
            "RSI": ["RSI"],
            "MACD": ["MACD_line", "MACD_signal", "MACD_hist"],
            "KD": ["K", "D"],
            "Bollinger": ["BB_upper", "BB_middle", "BB_lower"],
            "ATR": ["ATR"],
            "Pivot": ["Pivot_P", "Pivot_R1", "Pivot_S1", "Pivot_R2", "Pivot_S2", "Pivot_R3", "Pivot_S3"],
            "SRLevel": ["SR_resistance", "SR_support"],
        }
        return field_map.get(name, [name])

    result = compute(name, df, **kwargs)
    if isinstance(result, pd.DataFrame):
        return list(result.columns)
    return [result.name or name]
