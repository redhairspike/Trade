import io
import requests
import pandas as pd
import yfinance as yf
from config import FUNDAMENTAL_FIELDS


def format_tw_symbol(code: str) -> str:
    """Ensure a Taiwan stock code has .TW or .TWO suffix.

    If the input already contains a dot, return as-is.
    Codes on TPEx (上櫃) typically end with .TWO; TWSE (上市) with .TW.
    We default to .TW unless explicitly specified.
    """
    code = code.strip()
    if "." in code:
        return code
    return f"{code}.TW"


def get_twse_stock_list() -> pd.DataFrame:
    """Fetch all TWSE 上市 companies. Returns DataFrame with Symbol (.TW), Name."""
    try:
        url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rows = []
        for item in data:
            code = item.get("公司代號", "").strip()
            name = item.get("公司簡稱", "").strip()
            if code and name and code.isdigit():
                rows.append({"Symbol": f"{code}.TW", "Name": name})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["Symbol", "Name"])


def get_tpex_stock_list() -> pd.DataFrame:
    """Fetch all TPEx 上櫃 companies. Returns DataFrame with Symbol (.TWO), Name."""
    try:
        url = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rows = []
        for item in data:
            code = (item.get("SecuritiesCompanyCode") or item.get("公司代號", "")).strip()
            name = (item.get("CompanyAbbreviation") or item.get("公司簡稱", "")).strip()
            if code and name and code.isdigit():
                rows.append({"Symbol": f"{code}.TWO", "Name": name})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["Symbol", "Name"])


# Keep backward-compatible alias
def get_tw_stock_list() -> pd.DataFrame:
    return get_twse_stock_list()


def get_fundamentals(symbol: str) -> dict | None:
    """Get fundamental data for a single symbol via yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        # yfinance returns an almost-empty dict for invalid symbols
        if not info or (
            info.get("regularMarketPrice") is None
            and info.get("currentPrice") is None
            and info.get("previousClose") is None
        ):
            return None

        result = {"Symbol": symbol, "Name": info.get("shortName", symbol)}

        # Fields from info dict
        for field_name, field_cfg in FUNDAMENTAL_FIELDS.items():
            key = field_cfg["yfinance_key"]
            if key is None:
                continue  # computed below
            val = info.get(key)
            # Ratios → percentage
            if field_name in ("DividendYield", "ROE", "GrossMargin", "OperatingMargin",
                              "NetMargin", "RevenueGrowth", "EarningsGrowth",
                              "RevenueYOY_Q", "EarningsYOY_Q") and val is not None:
                val = round(val * 100, 2)
            elif field_name == "MarketCap" and val is not None:
                val = round(val / 1e8, 1)
            result[field_name] = val

        # Computed YOY fields — annual financials
        result["GrossMarginYOY"] = None
        result["OperatingMarginYOY"] = None
        result["NetMarginYOY"] = None
        result["NetIncomeYOY"] = None
        try:
            fin = ticker.financials  # annual, columns = dates descending
            if fin is not None and not fin.empty and fin.shape[1] >= 2:
                rev_row = _find_row(fin, ["Total Revenue", "Revenue"])
                gp_row  = _find_row(fin, ["Gross Profit"])
                op_row  = _find_row(fin, ["Operating Income", "Operating Profit", "EBIT"])
                ni_row  = _find_row(fin, ["Net Income", "Net Income Common Stockholders"])
                if rev_row and gp_row:
                    rev, gp = fin.loc[rev_row], fin.loc[gp_row]
                    gm0 = _safe_div(gp.iloc[0], rev.iloc[0])
                    gm1 = _safe_div(gp.iloc[1], rev.iloc[1])
                    if gm0 is not None and gm1 is not None:
                        result["GrossMarginYOY"] = round((gm0 - gm1) * 100, 2)
                if rev_row and op_row:
                    rev, op = fin.loc[rev_row], fin.loc[op_row]
                    om0 = _safe_div(op.iloc[0], rev.iloc[0])
                    om1 = _safe_div(op.iloc[1], rev.iloc[1])
                    if om0 is not None and om1 is not None:
                        result["OperatingMarginYOY"] = round((om0 - om1) * 100, 2)
                if rev_row and ni_row:
                    rev, ni = fin.loc[rev_row], fin.loc[ni_row]
                    nm0 = _safe_div(ni.iloc[0], rev.iloc[0])
                    nm1 = _safe_div(ni.iloc[1], rev.iloc[1])
                    if nm0 is not None and nm1 is not None:
                        result["NetMarginYOY"] = round((nm0 - nm1) * 100, 2)
                    ni0, ni1 = ni.iloc[0], ni.iloc[1]
                    if ni1 and ni1 != 0:
                        result["NetIncomeYOY"] = round((ni0 - ni1) / abs(ni1) * 100, 2)
        except Exception:
            pass

        # 三率三升 (annual): 毛利率 + 營業利益率 + 淨利率 YOY 全部 > 0
        gmy  = result.get("GrossMarginYOY")
        omy  = result.get("OperatingMarginYOY")
        nmy  = result.get("NetMarginYOY")
        result["ThreeRatesUp"] = (
            1 if (gmy is not None and omy is not None and nmy is not None
                  and gmy > 0 and omy > 0 and nmy > 0)
            else 0
        )

        # Computed YOY fields — quarterly financials
        result["GrossMarginYOY_Q"] = None
        result["OperatingMarginYOY_Q"] = None
        result["NetMarginYOY_Q"] = None
        try:
            qfin = ticker.quarterly_financials  # columns = dates descending
            if qfin is not None and not qfin.empty and qfin.shape[1] >= 5:
                # Compare most recent quarter (col 0) vs same quarter last year (col 4)
                rev_row = _find_row(qfin, ["Total Revenue", "Revenue"])
                gp_row  = _find_row(qfin, ["Gross Profit"])
                op_row  = _find_row(qfin, ["Operating Income", "Operating Profit", "EBIT"])
                ni_row  = _find_row(qfin, ["Net Income", "Net Income Common Stockholders"])
                if rev_row and gp_row:
                    rev, gp = qfin.loc[rev_row], qfin.loc[gp_row]
                    gm0 = _safe_div(gp.iloc[0], rev.iloc[0])
                    gm4 = _safe_div(gp.iloc[4], rev.iloc[4])
                    if gm0 is not None and gm4 is not None:
                        result["GrossMarginYOY_Q"] = round((gm0 - gm4) * 100, 2)
                if rev_row and op_row:
                    rev, op = qfin.loc[rev_row], qfin.loc[op_row]
                    om0 = _safe_div(op.iloc[0], rev.iloc[0])
                    om4 = _safe_div(op.iloc[4], rev.iloc[4])
                    if om0 is not None and om4 is not None:
                        result["OperatingMarginYOY_Q"] = round((om0 - om4) * 100, 2)
                if rev_row and ni_row:
                    rev, ni = qfin.loc[rev_row], qfin.loc[ni_row]
                    nm0 = _safe_div(ni.iloc[0], rev.iloc[0])
                    nm4 = _safe_div(ni.iloc[4], rev.iloc[4])
                    if nm0 is not None and nm4 is not None:
                        result["NetMarginYOY_Q"] = round((nm0 - nm4) * 100, 2)
        except Exception:
            pass

        # 三率三升 (單季)
        gmy_q = result.get("GrossMarginYOY_Q")
        omy_q = result.get("OperatingMarginYOY_Q")
        nmy_q = result.get("NetMarginYOY_Q")
        result["ThreeRatesUp_Q"] = (
            1 if (gmy_q is not None and omy_q is not None and nmy_q is not None
                  and gmy_q > 0 and omy_q > 0 and nmy_q > 0)
            else 0
        )

        return result
    except Exception:
        return None


def _find_row(df: "pd.DataFrame", candidates: list) -> str | None:
    """Return the first matching index label from a list of candidates."""
    for c in candidates:
        if c in df.index:
            return c
    return None


def _safe_div(a, b) -> float | None:
    try:
        if b and b != 0:
            return float(a) / float(b)
    except Exception:
        pass
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
    return pd.DataFrame(rows)


def load_fundamentals_csv(
    filepath: str = None,
    content: str = None,
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """Load fundamental data from CSV file or string content."""
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
