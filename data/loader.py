import pandas as pd
import yfinance as yf
from data.schema import validate


class DataLoader:
    @staticmethod
    def from_yfinance(
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Download OHLCV data from yfinance and return validated DataFrame."""
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval)
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")
        return validate(df)

    @staticmethod
    def from_csv(
        filepath: str,
        date_col: str = "Date",
        col_map: dict | None = None,
        encoding: str = "utf-8",
    ) -> pd.DataFrame:
        """Read OHLCV data from CSV file and return validated DataFrame."""
        try:
            df = pd.read_csv(filepath, encoding=encoding)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="big5")

        if col_map:
            df = df.rename(columns=col_map)

        if date_col != "Date" and date_col in df.columns:
            df = df.rename(columns={date_col: "Date"})

        return validate(df)

    @staticmethod
    def from_csv_content(
        content: str,
        date_col: str = "Date",
        col_map: dict | None = None,
    ) -> pd.DataFrame:
        """Read OHLCV data from CSV string content (for Dash upload)."""
        import io
        df = pd.read_csv(io.StringIO(content))
        if col_map:
            df = df.rename(columns=col_map)
        if date_col != "Date" and date_col in df.columns:
            df = df.rename(columns={date_col: "Date"})
        return validate(df)
