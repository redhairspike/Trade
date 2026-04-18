"""
Taiwan stock fundamental data from official open APIs.
Sources:
  - TWSE (上市): openapi.twse.com.tw
  - TPEx (上櫃): www.tpex.org.tw/openapi
  - MOPS 毛利率: mopsov.twse.com.tw/mops/web/ajax_t163sb09 (per-stock POST)

Bulk endpoints (PE/PB/Yield, quarterly fin, monthly revenue) fetch all
companies in one request.  MOPS gross margin is fetched per-stock and
called only for the filtered result set to keep latency acceptable.
"""
import datetime
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

# ── Endpoints ────────────────────────────────────────────────────────────────
_TWSE_PE   = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_d"
_TPEX_PE   = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis"
_TWSE_FIN  = "https://openapi.twse.com.tw/v1/opendata/t187ap14_L"
_TPEX_FIN  = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap14_O"
_TWSE_REV  = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
_TPEX_REV  = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O"


def _get(url: str, timeout: int = 15) -> list:
    resp = requests.get(url, timeout=timeout,
                        headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


# ── PE / PB / Yield ──────────────────────────────────────────────────────────

def _fetch_twse_pe() -> pd.DataFrame:
    """TWSE 本益比、殖利率、股價淨值比 (每日更新)."""
    data = _get(_TWSE_PE)
    rows = []
    for r in data:
        code = r.get("Code", "").strip()
        if not code:
            continue
        rows.append({
            "Symbol": f"{code}.TW",
            "Name":   r.get("Name", "").strip(),
            "PE":     _to_float(r.get("PEratio")),
            "PB":     _to_float(r.get("PBratio")),
            "DividendYield": _to_float(r.get("DividendYield")),
        })
    return pd.DataFrame(rows)


def _fetch_tpex_pe() -> pd.DataFrame:
    """TPEx 本益比、殖利率、股價淨值比 (每日更新)."""
    data = _get(_TPEX_PE)
    rows = []
    for r in data:
        code = (r.get("SecuritiesCompanyCode") or "").strip()
        if not code:
            continue
        rows.append({
            "Symbol": f"{code}.TWO",
            "Name":   (r.get("CompanyName") or "").strip(),
            "PE":     _to_float(r.get("PriceEarningRatio")),
            "PB":     _to_float(r.get("PriceBookRatio")),
            "DividendYield": _to_float(r.get("YieldRatio")),
        })
    return pd.DataFrame(rows)


# ── Quarterly Financials ─────────────────────────────────────────────────────

def _parse_fin(data: list, code_key: str, name_key: str, suffix: str) -> pd.DataFrame:
    """Parse quarterly financials JSON into a tidy DataFrame."""
    rows = []
    for r in data:
        code = (r.get(code_key) or "").strip()
        if not code:
            continue
        yr  = _to_int(r.get("年度") or r.get("Year"))
        qtr = _to_int(r.get("季別") or r.get("季別"))
        rev = _to_float(r.get("營業收入"))
        oi  = _to_float(r.get("營業利益"))
        ni  = _to_float(r.get("稅後淨利"))
        eps = _to_float(r.get("基本每股盈餘(元)") or r.get("基本每股盈餘"))
        rows.append({
            "Symbol": f"{code}.{suffix}",
            "Name":   (r.get(name_key) or "").strip(),
            "yr": yr, "qtr": qtr,
            "Revenue": rev, "OperatingIncome": oi,
            "NetIncome": ni, "EPS": eps,
        })
    return pd.DataFrame(rows)


def _fetch_twse_fin() -> pd.DataFrame:
    data = _get(_TWSE_FIN)
    return _parse_fin(data, "公司代號", "公司名稱", "TW")


def _fetch_tpex_fin() -> pd.DataFrame:
    data = _get(_TPEX_FIN)
    return _parse_fin(data, "SecuritiesCompanyCode", "CompanyName", "TWO")


def _compute_fin_metrics(fin: pd.DataFrame) -> pd.DataFrame:
    """
    From quarterly financials, compute per-company:
      OperatingMargin, NetMargin (current quarter)
      OperatingMarginYOY, NetMarginYOY, NetIncomeYOY (vs same quarter last year)
    """
    if fin.empty:
        return pd.DataFrame()

    fin = fin.dropna(subset=["yr", "qtr"])
    fin["yr"]  = fin["yr"].astype(int)
    fin["qtr"] = fin["qtr"].astype(int)

    results = []
    for symbol, grp in fin.groupby("Symbol"):
        grp = grp.sort_values(["yr", "qtr"], ascending=False)
        cur = grp.iloc[0]

        # Current margins
        rev0 = cur["Revenue"]
        om   = _safe_pct(cur["OperatingIncome"], rev0)
        nm   = _safe_pct(cur["NetIncome"], rev0)

        # Find same quarter last year
        prev = grp[(grp["yr"] == cur["yr"] - 1) & (grp["qtr"] == cur["qtr"])]
        om_yoy = nm_yoy = ni_yoy = None
        if not prev.empty:
            p = prev.iloc[0]
            rev1 = p["Revenue"]
            om1  = _safe_pct(p["OperatingIncome"], rev1)
            nm1  = _safe_pct(p["NetIncome"], rev1)
            if om is not None and om1 is not None:
                om_yoy = round(om - om1, 2)
            if nm is not None and nm1 is not None:
                nm_yoy = round(nm - nm1, 2)
            ni0, ni1 = cur["NetIncome"], p["NetIncome"]
            if ni1 and ni1 != 0:
                ni_yoy = round((ni0 - ni1) / abs(ni1) * 100, 2)

        results.append({
            "Symbol": symbol,
            "Name":   cur["Name"],
            "EPS":    round(cur["EPS"], 2) if cur["EPS"] is not None else None,
            "OperatingMargin":    round(om, 2)   if om    is not None else None,
            "NetMargin":          round(nm, 2)   if nm    is not None else None,
            "OperatingMarginYOY": om_yoy,
            "NetMarginYOY":       nm_yoy,
            "NetIncomeYOY":       ni_yoy,
        })
    return pd.DataFrame(results)


# ── Monthly Revenue ───────────────────────────────────────────────────────────

def _parse_rev(data: list, code_key: str, suffix: str) -> pd.DataFrame:
    rows = []
    for r in data:
        code = (r.get(code_key) or "").strip()
        if not code:
            continue
        rows.append({
            "Symbol":        f"{code}.{suffix}",
            # 去年同月增減 (%) — revenue YOY vs same month last year
            "RevenueGrowth": _to_float(
                r.get("營業收入-去年同月增減(%)") or r.get("去年同月增減(%)")
            ),
            # 累計前期比較增減 (%) — cumulative YTD YOY
            "RevenueGrowthYTD": _to_float(
                r.get("累計營業收入-前期比較增減(%)") or r.get("前期比較增減(%)")
            ),
        })
    return pd.DataFrame(rows)


def _fetch_twse_rev() -> pd.DataFrame:
    data = _get(_TWSE_REV)
    return _parse_rev(data, "公司代號", "TW")


def _fetch_tpex_rev() -> pd.DataFrame:
    data = _get(_TPEX_REV)
    return _parse_rev(data, "公司代號", "TWO")


# ── Public API ────────────────────────────────────────────────────────────────

def get_tw_fundamentals(market: str = "twse") -> pd.DataFrame:
    """
    Fetch and merge fundamental data for all Taiwan stocks.

    Args:
        market: "twse" | "tpex" | "all"

    Returns:
        DataFrame with columns:
          Symbol, Name, PE, PB, DividendYield, EPS,
          OperatingMargin (%), NetMargin (%),
          RevenueGrowth (% YOY), RevenueGrowthYTD (%),
          OperatingMarginYOY (pp), NetMarginYOY (pp), NetIncomeYOY (%),
          ThreeRatesUp (1/0)
    """
    parts_pe, parts_fin, parts_rev = [], [], []

    if market in ("twse", "all"):
        try:
            parts_pe.append(_fetch_twse_pe())
        except Exception as e:
            print(f"[tw_fundamental] TWSE PE error: {e}")
        try:
            raw = _fetch_twse_fin()
            parts_fin.append(_compute_fin_metrics(raw))
        except Exception as e:
            print(f"[tw_fundamental] TWSE fin error: {e}")
        try:
            parts_rev.append(_fetch_twse_rev())
        except Exception as e:
            print(f"[tw_fundamental] TWSE rev error: {e}")

    if market in ("tpex", "all"):
        try:
            parts_pe.append(_fetch_tpex_pe())
        except Exception as e:
            print(f"[tw_fundamental] TPEx PE error: {e}")
        try:
            raw = _fetch_tpex_fin()
            parts_fin.append(_compute_fin_metrics(raw))
        except Exception as e:
            print(f"[tw_fundamental] TPEx fin error: {e}")
        try:
            parts_rev.append(_fetch_tpex_rev())
        except Exception as e:
            print(f"[tw_fundamental] TPEx rev error: {e}")

    if not parts_pe:
        return pd.DataFrame()

    pe_df  = pd.concat(parts_pe,  ignore_index=True)
    fin_df = pd.concat(parts_fin, ignore_index=True) if parts_fin else pd.DataFrame()
    rev_df = pd.concat(parts_rev, ignore_index=True) if parts_rev else pd.DataFrame()

    # Merge on Symbol
    df = pe_df
    if not fin_df.empty:
        df = df.merge(
            fin_df[["Symbol", "EPS", "OperatingMargin", "NetMargin",
                    "OperatingMarginYOY", "NetMarginYOY", "NetIncomeYOY"]],
            on="Symbol", how="left"
        )
    if not rev_df.empty:
        df = df.merge(
            rev_df[["Symbol", "RevenueGrowth", "RevenueGrowthYTD"]],
            on="Symbol", how="left"
        )

    # 三率三升: 月營收年增率 > 0 AND 營業利益率年增 > 0 AND 淨利率年增 > 0
    # (GrossMarginYOY filled in later via enrich_with_gross_margin if requested)
    df["GrossMargin"]    = None
    df["GrossMarginYOY"] = None
    df["ThreeRatesUp"]   = df.apply(_calc_three_rates, axis=1)

    return df


def enrich_with_gross_margin(df: pd.DataFrame, max_workers: int = 10) -> pd.DataFrame:
    """
    Enrich filtered results with gross margin and YOY margin data.

    For .TW / .TWO symbols: uses FinMind TaiwanStockFinancialStatements
    (quarterly data, latest quarter vs same quarter last year).
    For other symbols: falls back to yfinance annual financials.

    Adds / updates columns:
      GrossMargin (%), GrossMarginYOY (pp), OperatingMarginYOY (pp),
      NetMarginYOY (pp), GrossMarginYOY_Q (pp), OperatingMarginYOY_Q (pp),
      NetMarginYOY_Q (pp), ThreeRatesUp, ThreeRatesUp_Q
    """
    import datetime
    import yfinance as yf
    from config import FINMIND_TOKEN

    if df.empty:
        return df

    _ENRICH_COLS = (
        "GrossMargin", "GrossMarginYOY", "OperatingMarginYOY", "NetMarginYOY",
        "GrossMarginYOY_Q", "OperatingMarginYOY_Q", "NetMarginYOY_Q",
    )
    start_date = (datetime.date.today() - datetime.timedelta(days=760)).strftime("%Y-%m-%d")

    # ── FinMind (Taiwan stocks) ──────────────────────────────────────────────

    def _fetch_finmind(sym: str) -> dict:
        out = {"Symbol": sym, **{c: None for c in _ENRICH_COLS}}
        stock_id = sym.split(".")[0]
        try:
            resp = requests.get(
                "https://api.finmindtrade.com/api/v4/data",
                params={
                    "dataset": "TaiwanStockFinancialStatements",
                    "data_id": stock_id,
                    "start_date": start_date,
                    "token": FINMIND_TOKEN,
                },
                timeout=20,
            )
            payload = resp.json()
            if payload.get("status") != 200 or not payload.get("data"):
                return out

            key_types = {
                "Revenue", "GrossProfit", "OperatingIncome",
                "TotalConsolidatedProfitForThePeriod",
            }
            rows = [r for r in payload["data"] if r["type"] in key_types]
            if not rows:
                return out

            fin = (
                pd.DataFrame(rows)
                .pivot_table(index="date", columns="type", values="value", aggfunc="last")
            )
            fin.index = pd.to_datetime(fin.index)
            fin = fin.sort_index()

            if len(fin) < 2:
                return out

            # Most recent quarter
            latest = fin.iloc[-1]
            latest_date = fin.index[-1]

            # Find same quarter last year (within 46 days)
            target = latest_date - pd.DateOffset(years=1)
            diffs  = (fin.index - target).map(abs)
            prior_iloc = diffs.argmin()
            if diffs[prior_iloc].days > 46:
                return out
            prior = fin.iloc[prior_iloc]

            def _margin(profit_col, rev_col, row):
                try:
                    r = float(row.get(rev_col, 0) or 0)
                    if r == 0:
                        return None
                    return float(row.get(profit_col, 0) or 0) / r * 100
                except Exception:
                    return None

            gm_cur  = _margin("GrossProfit",  "Revenue", latest)
            gm_prev = _margin("GrossProfit",  "Revenue", prior)
            om_cur  = _margin("OperatingIncome", "Revenue", latest)
            om_prev = _margin("OperatingIncome", "Revenue", prior)
            nm_cur  = _margin("TotalConsolidatedProfitForThePeriod", "Revenue", latest)
            nm_prev = _margin("TotalConsolidatedProfitForThePeriod", "Revenue", prior)

            if gm_cur is not None:
                out["GrossMargin"] = round(gm_cur, 2)
            if gm_cur is not None and gm_prev is not None:
                yoy = round(gm_cur - gm_prev, 2)
                out["GrossMarginYOY"] = yoy
                out["GrossMarginYOY_Q"] = yoy
            if om_cur is not None and om_prev is not None:
                yoy = round(om_cur - om_prev, 2)
                out["OperatingMarginYOY"] = yoy
                out["OperatingMarginYOY_Q"] = yoy
            if nm_cur is not None and nm_prev is not None:
                yoy = round(nm_cur - nm_prev, 2)
                out["NetMarginYOY"] = yoy
                out["NetMarginYOY_Q"] = yoy
        except Exception:
            pass
        return out

    # ── yfinance (non-Taiwan stocks) ─────────────────────────────────────────

    def _fetch_yfinance(sym: str) -> dict:
        out = {"Symbol": sym, **{c: None for c in _ENRICH_COLS}}
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            gm_cur = info.get("grossMargins")
            if gm_cur is not None:
                out["GrossMargin"] = round(gm_cur * 100, 2)

            fin = ticker.financials
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
                        out["GrossMarginYOY"] = round((gm0 - gm1) * 100, 2)
                if rev_row and op_row:
                    rev, op = fin.loc[rev_row], fin.loc[op_row]
                    om0 = _safe_div(op.iloc[0], rev.iloc[0])
                    om1 = _safe_div(op.iloc[1], rev.iloc[1])
                    if om0 is not None and om1 is not None:
                        out["OperatingMarginYOY"] = round((om0 - om1) * 100, 2)
                if rev_row and ni_row:
                    rev, ni = fin.loc[rev_row], fin.loc[ni_row]
                    nm0 = _safe_div(ni.iloc[0], rev.iloc[0])
                    nm1 = _safe_div(ni.iloc[1], rev.iloc[1])
                    if nm0 is not None and nm1 is not None:
                        out["NetMarginYOY"] = round((nm0 - nm1) * 100, 2)
        except Exception:
            pass
        return out

    # ── Dispatch ─────────────────────────────────────────────────────────────

    symbols = df["Symbol"].tolist()
    tw_syms    = [s for s in symbols if s.endswith(".TW") or s.endswith(".TWO")]
    other_syms = [s for s in symbols if s not in tw_syms]

    results: dict = {}

    def _run(fn, syms):
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(fn, sym): sym for sym in syms}
            for fut in as_completed(futures):
                r = fut.result()
                results[r["Symbol"]] = r

    _run(_fetch_finmind, tw_syms)
    _run(_fetch_yfinance, other_syms)

    df = df.copy()
    for col in _ENRICH_COLS:
        df[col] = df["Symbol"].map(lambda s, c=col: results.get(s, {}).get(c))

    df["ThreeRatesUp"]   = df.apply(_calc_three_rates_full, axis=1)
    df["ThreeRatesUp_Q"] = df.apply(_calc_three_rates_full_q, axis=1)
    return df


def _calc_three_rates(row) -> int:
    """三率三升（無毛利率版）: 月營收 + 營益率 + 淨利率 YOY 全升."""
    rg  = row.get("RevenueGrowth")
    omy = row.get("OperatingMarginYOY")
    nmy = row.get("NetMarginYOY")
    if any(v is None for v in (rg, omy, nmy)):
        return 0
    return 1 if (rg > 0 and omy > 0 and nmy > 0) else 0


def _calc_three_rates_full(row) -> int:
    """三率三升（含毛利率，年度版）: 毛利率 + 營益率 + 淨利率 YOY 全升."""
    gmy = row.get("GrossMarginYOY")
    omy = row.get("OperatingMarginYOY")
    nmy = row.get("NetMarginYOY")
    if any(v is None for v in (gmy, omy, nmy)):
        return 0
    return 1 if (gmy > 0 and omy > 0 and nmy > 0) else 0


def _calc_three_rates_full_q(row) -> int:
    """三率三升（含毛利率，單季版）: 毛利率 + 營益率 + 淨利率 單季 YOY 全升."""
    gmy = row.get("GrossMarginYOY_Q")
    omy = row.get("OperatingMarginYOY_Q")
    nmy = row.get("NetMarginYOY_Q")
    if any(v is None for v in (gmy, omy, nmy)):
        return 0
    return 1 if (gmy > 0 and omy > 0 and nmy > 0) else 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        s = str(val).replace(",", "").strip()
        if s in ("", "-", "N/A", "--"):
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


def _to_int(val) -> int | None:
    f = _to_float(val)
    return int(f) if f is not None else None


def _safe_pct(numerator, denominator) -> float | None:
    try:
        n, d = float(numerator), float(denominator)
        if d == 0:
            return None
        return round(n / d * 100, 4)
    except (TypeError, ValueError):
        return None


def _find_row(fin: pd.DataFrame, candidates: list) -> str | None:
    """Return first matching index label in fin.index from candidates list."""
    for c in candidates:
        if c in fin.index:
            return c
    return None


def _safe_div(a, b) -> float | None:
    try:
        fa, fb = float(a), float(b)
        return fa / fb if fb != 0 else None
    except (TypeError, ValueError):
        return None
