import pandas as pd

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize an OHLCV DataFrame."""
    if df is None or df.empty:
        raise ValueError("DataFrame is empty")

    # Normalize column names (case-insensitive matching)
    col_map = {}
    for col in df.columns:
        for req in REQUIRED_COLUMNS:
            if col.lower() == req.lower():
                col_map[col] = req
    df = df.rename(columns=col_map)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df.index.name = "Date"
        else:
            try:
                df.index = pd.to_datetime(df.index)
                df.index.name = "Date"
            except Exception:
                raise ValueError("Cannot parse date index")

    # Keep only required columns, convert to float
    df = df[REQUIRED_COLUMNS].copy()
    for col in REQUIRED_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()
    df = df.sort_index()

    if df.empty:
        raise ValueError("No valid data after cleaning")

    return df
