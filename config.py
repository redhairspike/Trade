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
}

OPERATORS = [">", "<", ">=", "<=", "crosses_above", "crosses_below"]

FUNDAMENTAL_FIELDS = {
    "PE": {"yfinance_key": "trailingPE", "label": "本益比"},
    "PB": {"yfinance_key": "priceToBook", "label": "股價淨值比"},
    "DividendYield": {"yfinance_key": "dividendYield", "label": "殖利率"},
    "ROE": {"yfinance_key": "returnOnEquity", "label": "ROE"},
    "RevenueGrowth": {"yfinance_key": "revenueGrowth", "label": "營收成長率"},
    "EPS": {"yfinance_key": "trailingEps", "label": "EPS"},
}

SP500_SAMPLE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "BAC", "XOM",
    "ADBE", "CRM", "NFLX", "CSCO", "PFE", "TMO", "ABT", "KO", "PEP",
    "AVGO", "COST", "MRK",
]
