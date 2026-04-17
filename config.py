DEFAULT_INITIAL_CAPITAL = 1_000_000
DEFAULT_COMMISSION_RATE = 0.001      # 0.1%
DEFAULT_SLIPPAGE_RATE = 0.0005       # 0.05%
DEFAULT_RISK_FREE_RATE = 0.02        # 2% annual
TRADING_DAYS_PER_YEAR = 252

INDICATOR_DEFAULTS = {
    "MA": {"period": 20},
    "EMA": {"period": 20},
    "RSI": {"period": 14},
    "MACD": {"fast": 12, "slow": 26, "signal": 9},
    "KD": {"k_period": 14, "d_period": 3},
    "Bollinger": {"period": 20, "std_dev": 2.0},
    "ATR": {"period": 14},
    "Pivot": {"pivot_type": 1},
    "SRLevel": {"order": 5, "merge_pct": 1},
    "DoubleTop": {"order": 10, "tolerance_pct": 3, "min_bars": 10},
    "DoubleBottom": {"order": 10, "tolerance_pct": 3, "min_bars": 10},
}

OPERATORS = [">", "<", ">=", "<=", "crosses_above", "crosses_below"]

FUNDAMENTAL_FIELDS = {
    # 估值
    "PE":                       {"yfinance_key": "trailingPE",               "label": "本益比 (PE)",           "group": "估值"},
    "PB":                       {"yfinance_key": "priceToBook",              "label": "股價淨值比 (PB)",        "group": "估值"},
    "DividendYield":            {"yfinance_key": "dividendYield",            "label": "殖利率 (%)",             "group": "估值"},
    "MarketCap":                {"yfinance_key": "marketCap",                "label": "市值 (億)",              "group": "估值"},
    # 獲利能力（當期）
    "EPS":                      {"yfinance_key": "trailingEps",              "label": "EPS",                    "group": "獲利能力"},
    "ROE":                      {"yfinance_key": "returnOnEquity",           "label": "ROE (%)",                "group": "獲利能力"},
    "GrossMargin":              {"yfinance_key": "grossMargins",             "label": "毛利率 (%)",             "group": "獲利能力"},
    "OperatingMargin":          {"yfinance_key": "operatingMargins",         "label": "營業利益率 (%)",         "group": "獲利能力"},
    "NetMargin":                {"yfinance_key": "profitMargins",            "label": "淨利率 (%)",             "group": "獲利能力"},
    # YOY 年增率（全年）
    "RevenueGrowth":            {"yfinance_key": "revenueGrowth",            "label": "營收年增率 YOY (%)",        "group": "YOY 年增率"},
    "EarningsGrowth":           {"yfinance_key": "earningsGrowth",           "label": "獲利年增率 YOY (%)",        "group": "YOY 年增率"},
    "GrossMarginYOY":           {"yfinance_key": None,                       "label": "毛利率年增 YOY (pp)",       "group": "YOY 年增率"},
    "OperatingMarginYOY":       {"yfinance_key": None,                       "label": "營益率年增 YOY (pp)",       "group": "YOY 年增率"},
    "NetMarginYOY":             {"yfinance_key": None,                       "label": "淨利率年增 YOY (pp)",       "group": "YOY 年增率"},
    "NetIncomeYOY":             {"yfinance_key": None,                       "label": "淨利年增率 YOY (%)",        "group": "YOY 年增率"},
    "ThreeRatesUp":             {"yfinance_key": None,                       "label": "三率三升 年(1=是 0=否)",    "group": "YOY 年增率"},
    # YOY 年增率（單季）
    "RevenueYOY_Q":             {"yfinance_key": "quarterlyRevenueGrowth",   "label": "單季營收年增 YOY (%)",      "group": "YOY 單季"},
    "EarningsYOY_Q":            {"yfinance_key": "quarterlyEarningsGrowth",  "label": "單季獲利年增 YOY (%)",      "group": "YOY 單季"},
    "GrossMarginYOY_Q":         {"yfinance_key": None,                       "label": "單季毛利率年增 YOY (pp)",   "group": "YOY 單季"},
    "OperatingMarginYOY_Q":     {"yfinance_key": None,                       "label": "單季營益率年增 YOY (pp)",   "group": "YOY 單季"},
    "NetMarginYOY_Q":           {"yfinance_key": None,                       "label": "單季淨利率年增 YOY (pp)",   "group": "YOY 單季"},
    "ThreeRatesUp_Q":           {"yfinance_key": None,                       "label": "三率三升 季(1=是 0=否)",    "group": "YOY 單季"},
}

SP500_SAMPLE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "BAC", "XOM",
    "ADBE", "CRM", "NFLX", "CSCO", "PFE", "TMO", "ABT", "KO", "PEP",
    "AVGO", "COST", "MRK",
]
