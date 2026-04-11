import pandas as pd
import yfinance as yf
from config import FUNDAMENTAL_FIELDS


def get_fundamentals(symbol: str) -> dict | None:
    """Get fundamental data for a single symbol via yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        result = {"Symbol": symbol, "Name": info.get("shortName", symbol)}
        for field_name, field_info in FUNDAMENTAL_FIELDS.items():
            val = info.get(field_info["yfinance_key"])
            result[field_name] = val
        return result
    except Exception:
        return None


def get_fundamentals_batch(symbols: list[str]) -> pd.DataFrame:
    """Get fundamental data for multiple symbols. Returns a DataFrame."""
    rows = []
    for symbol in symbols:
        data = get_fundamentals(symbol)
        if data is not None:
            rows.append(data)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df


def load_fundamentals_csv(
    filepath: str = None,
    content: str = None,
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """Load fundamental data from CSV file or string content.

    Expected columns: Symbol, and any of PE, PB, DividendYield, ROE,
    RevenueGrowth, EPS (or Chinese equivalents).
    """
    import io

    col_aliases = {
        "代碼": "Symbol", "股票代碼": "Symbol",
        "名稱": "Name", "股票名稱": "Name",
        "本益比": "PE", "P/E": "PE",
        "股價淨值比": "PB", "P/B": "PB",
        "殖利率": "DividendYield",
        "股東權益報酬率": "ROE",
        "營收成長率": "RevenueGrowth",
        "每股盈餘": "EPS",
    }

    if content is not None:
        df = pd.read_csv(io.StringIO(content))
    elif filepath is not None:
        try:
            df = pd.read_csv(filepath, encoding=encoding)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="big5")
    else:
        raise ValueError("Must provide filepath or content")

    df = df.rename(columns=col_aliases)

    if "Symbol" not in df.columns:
        raise ValueError("CSV must contain a Symbol column")

    return df
