import pandas as pd
import yfinance as yf
import requests
import io
import time
from datetime import datetime, timedelta


class DataDownloader:
    """Download historical price data from multiple sources."""

    @staticmethod
    def from_yfinance(
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Download OHLCV data via yfinance.

        Supports: US stocks (AAPL), TW stocks (2330.TW), futures (ES=F, NQ=F),
        crypto (BTC-USD), indices (^GSPC), etc.
        """
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval)
        if df.empty:
            raise ValueError(f"yfinance: 無法取得 {symbol} 的資料")
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index.name = "Date"
        df = df.dropna()
        return df

    @staticmethod
    def from_twse(
        stock_id: str,
        year: int,
        month: int,
    ) -> pd.DataFrame:
        """Download monthly OHLCV data from TWSE (台灣證券交易所).

        Only supports TWSE-listed stocks (上市股票).
        """
        date_str = f"{year}{month:02d}01"
        url = (
            f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
            f"?response=json&date={date_str}&stockNo={stock_id}"
        )
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "zh-TW,zh;q=0.9",
        }

        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("stat") != "OK" or "data" not in data:
            raise ValueError(f"TWSE: 無法取得 {stock_id} {year}/{month} 的資料")

        rows = []
        for row in data["data"]:
            # row: [日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數]
            try:
                # Convert ROC date (民國) to AD date
                date_parts = row[0].split("/")
                ad_year = int(date_parts[0]) + 1911
                date = datetime(ad_year, int(date_parts[1]), int(date_parts[2]))

                # Remove commas from numbers
                open_p = float(row[3].replace(",", ""))
                high = float(row[4].replace(",", ""))
                low = float(row[5].replace(",", ""))
                close = float(row[6].replace(",", ""))
                volume = int(row[1].replace(",", ""))

                rows.append({
                    "Date": date,
                    "Open": open_p,
                    "High": high,
                    "Low": low,
                    "Close": close,
                    "Volume": volume,
                })
            except (ValueError, IndexError):
                continue

        if not rows:
            raise ValueError(f"TWSE: {stock_id} {year}/{month} 無有效資料")

        df = pd.DataFrame(rows)
        df = df.set_index("Date")
        df = df.sort_index()
        return df

    @staticmethod
    def from_tpex(
        stock_id: str,
        year: int,
        month: int,
    ) -> pd.DataFrame:
        """Download monthly OHLCV data from TPEx (櫃買中心).

        Only supports OTC stocks (上櫃股票).
        """
        roc_year = year - 1911
        url = (
            f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info"
            f"/st43_result.php?l=zh-tw&d={roc_year}/{month:02d}/01&stkno={stock_id}"
        )
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "zh-TW,zh;q=0.9",
        }

        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "aaData" not in data or not data["aaData"]:
            raise ValueError(f"TPEx: 無法取得 {stock_id} {year}/{month} 的資料")

        rows = []
        for row in data["aaData"]:
            # row: [日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數]
            try:
                date_parts = row[0].split("/")
                ad_year = int(date_parts[0]) + 1911
                date = datetime(ad_year, int(date_parts[1]), int(date_parts[2]))

                open_p = float(str(row[3]).replace(",", ""))
                high = float(str(row[4]).replace(",", ""))
                low = float(str(row[5]).replace(",", ""))
                close = float(str(row[6]).replace(",", ""))
                volume = int(str(row[1]).replace(",", ""))

                rows.append({
                    "Date": date,
                    "Open": open_p,
                    "High": high,
                    "Low": low,
                    "Close": close,
                    "Volume": volume,
                })
            except (ValueError, IndexError):
                continue

        if not rows:
            raise ValueError(f"TPEx: {stock_id} {year}/{month} 無有效資料")

        df = pd.DataFrame(rows)
        df = df.set_index("Date")
        df = df.sort_index()
        return df

    @staticmethod
    def download_tw_range(
        stock_id: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        market: str = "twse",
    ) -> pd.DataFrame:
        """Download multiple months of TW stock data and combine.

        Args:
            market: "twse" for 上市, "tpex" for 上櫃
        """
        fetch_func = DataDownloader.from_twse if market == "twse" else DataDownloader.from_tpex
        all_dfs = []

        y, m = start_year, start_month
        while (y, m) <= (end_year, end_month):
            try:
                df = fetch_func(stock_id, y, m)
                all_dfs.append(df)
            except Exception:
                pass  # Skip months with no data

            # Rate limit to avoid being blocked
            time.sleep(0.5)

            m += 1
            if m > 12:
                m = 1
                y += 1

        if not all_dfs:
            raise ValueError(f"無法取得 {stock_id} 在指定期間的資料")

        result = pd.concat(all_dfs)
        result = result.sort_index()
        result = result[~result.index.duplicated(keep="first")]
        return result

    @staticmethod
    def to_csv(df: pd.DataFrame) -> str:
        """Convert DataFrame to CSV string for download."""
        return df.to_csv()

    @staticmethod
    def get_symbol_info(symbol: str) -> dict:
        """Get basic info for a symbol via yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "name": info.get("shortName", symbol),
                "type": info.get("quoteType", "Unknown"),
                "currency": info.get("currency", ""),
                "exchange": info.get("exchange", ""),
            }
        except Exception:
            return {"name": symbol, "type": "Unknown", "currency": "", "exchange": ""}


# Common futures symbols for reference
FUTURES_SYMBOLS = {
    "ES=F": "S&P 500 E-mini",
    "NQ=F": "Nasdaq 100 E-mini",
    "YM=F": "Dow Jones E-mini",
    "RTY=F": "Russell 2000 E-mini",
    "GC=F": "黃金期貨",
    "SI=F": "白銀期貨",
    "CL=F": "原油期貨 (WTI)",
    "NG=F": "天然氣期貨",
    "ZB=F": "美國國債期貨",
    "6E=F": "歐元期貨",
    "6J=F": "日圓期貨",
    "BTC-USD": "比特幣",
    "ETH-USD": "以太幣",
}

TW_POPULAR_STOCKS = {
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "2882": "國泰金",
    "2881": "富邦金",
    "1301": "台塑",
    "2308": "台達電",
    "2412": "中華電",
    "2886": "兆豐金",
    "3711": "日月光投控",
}
