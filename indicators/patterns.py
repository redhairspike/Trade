import pandas as pd
import numpy as np
from indicators.base import register


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_pivots(highs: np.ndarray, lows: np.ndarray, order: int):
    """Find local swing highs and swing lows, return as sorted zigzag list.

    Each element: (index, price, type)  where type = 'H' or 'L'.
    """
    n = len(highs)
    swing_highs = []
    swing_lows = []

    for i in range(order, n - order):
        # Swing high: highest within ±order bars
        if all(highs[i] >= highs[i - j] for j in range(1, order + 1)) and \
           all(highs[i] >= highs[i + j] for j in range(1, order + 1)):
            swing_highs.append((i, float(highs[i]), "H"))

        # Swing low: lowest within ±order bars
        if all(lows[i] <= lows[i - j] for j in range(1, order + 1)) and \
           all(lows[i] <= lows[i + j] for j in range(1, order + 1)):
            swing_lows.append((i, float(lows[i]), "L"))

    # Merge and sort by index
    all_pivots = sorted(swing_highs + swing_lows, key=lambda x: x[0])

    # Build alternating zigzag (remove consecutive same-type pivots)
    if not all_pivots:
        return []

    zigzag = [all_pivots[0]]
    for p in all_pivots[1:]:
        if p[2] == zigzag[-1][2]:
            # Same type: keep the more extreme one
            if p[2] == "H" and p[1] > zigzag[-1][1]:
                zigzag[-1] = p
            elif p[2] == "L" and p[1] < zigzag[-1][1]:
                zigzag[-1] = p
        else:
            zigzag.append(p)

    return zigzag


# ---------------------------------------------------------------------------
# Double Top (M頭)
# ---------------------------------------------------------------------------

@register("DoubleTop", {"order": 10, "tolerance_pct": 3, "min_bars": 10})
def double_top(
    df: pd.DataFrame,
    order: int = 10,
    tolerance_pct: int = 3,
    min_bars: int = 10,
) -> pd.DataFrame:
    """Double Top (M頭) 偵測。

    掃描價格的局部極值，找出 M 頭形態並在跌破頸線時發出信號。

    Args:
        order: 局部極值判斷嚴格度（前後各 order 根 K 棒）
        tolerance_pct: 兩峰價差容許百分比 (以形態高度為基準)
        min_bars: 兩峰最少間隔 K 棒數

    Output columns:
        DT_signal:   1 = M頭確認（跌破頸線），0 = 無信號
        DT_neckline: 頸線價位（Trough 價格）
        DT_target:   目標價（頸線 - 形態高度）
    """
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    n = len(df)

    dt_signal = np.zeros(n)
    dt_neckline = np.full(n, np.nan)
    dt_target = np.full(n, np.nan)

    zigzag = _find_pivots(highs, lows, order)

    tol_ratio = tolerance_pct / 100.0

    # Scan zigzag for H-L-H pattern (Peak1, Trough, Peak2)
    patterns = []
    for i in range(len(zigzag) - 2):
        p1 = zigzag[i]
        trough = zigzag[i + 1]
        p2 = zigzag[i + 2]

        # Must be H-L-H
        if p1[2] != "H" or trough[2] != "L" or p2[2] != "H":
            continue

        # Minimum bar separation
        if p2[0] - p1[0] < min_bars:
            continue

        avg_peak = (p1[1] + p2[1]) / 2
        height = avg_peak - trough[1]

        # Minimum height filter (at least 1% of price)
        if height < avg_peak * 0.01:
            continue

        # Two peaks approximately equal
        if abs(p1[1] - p2[1]) > height * tol_ratio:
            continue

        patterns.append({
            "peak1_idx": p1[0],
            "peak1_price": p1[1],
            "trough_idx": trough[0],
            "trough_price": trough[1],
            "peak2_idx": p2[0],
            "peak2_price": p2[1],
            "height": height,
            "neckline": trough[1],
            "target": trough[1] - height,
        })

    # For each bar after Peak2, check if close breaks below neckline
    for pat in patterns:
        confirmed = False
        for j in range(pat["peak2_idx"] + 1, n):
            if confirmed:
                break
            if closes[j] < pat["neckline"]:
                # Breakout confirmed on this bar
                dt_signal[j] = 1
                dt_neckline[j] = pat["neckline"]
                dt_target[j] = pat["target"]
                confirmed = True

    return pd.DataFrame({
        "DT_signal": dt_signal,
        "DT_neckline": dt_neckline,
        "DT_target": dt_target,
    }, index=df.index)


# ---------------------------------------------------------------------------
# Double Bottom (W底)
# ---------------------------------------------------------------------------

@register("DoubleBottom", {"order": 10, "tolerance_pct": 3, "min_bars": 10})
def double_bottom(
    df: pd.DataFrame,
    order: int = 10,
    tolerance_pct: int = 3,
    min_bars: int = 10,
) -> pd.DataFrame:
    """Double Bottom (W底) 偵測。

    掃描價格的局部極值，找出 W 底形態並在突破頸線時發出信號。

    Args:
        order: 局部極值判斷嚴格度（前後各 order 根 K 棒）
        tolerance_pct: 兩谷價差容許百分比 (以形態高度為基準)
        min_bars: 兩谷最少間隔 K 棒數

    Output columns:
        DB_signal:   1 = W底確認（突破頸線），0 = 無信號
        DB_neckline: 頸線價位（Peak 價格）
        DB_target:   目標價（頸線 + 形態高度）
    """
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    n = len(df)

    db_signal = np.zeros(n)
    db_neckline = np.full(n, np.nan)
    db_target = np.full(n, np.nan)

    zigzag = _find_pivots(highs, lows, order)

    tol_ratio = tolerance_pct / 100.0

    # Scan zigzag for L-H-L pattern (Valley1, Peak, Valley2)
    patterns = []
    for i in range(len(zigzag) - 2):
        v1 = zigzag[i]
        peak = zigzag[i + 1]
        v2 = zigzag[i + 2]

        # Must be L-H-L
        if v1[2] != "L" or peak[2] != "H" or v2[2] != "L":
            continue

        # Minimum bar separation
        if v2[0] - v1[0] < min_bars:
            continue

        avg_valley = (v1[1] + v2[1]) / 2
        height = peak[1] - avg_valley

        # Minimum height filter (at least 1% of price)
        if height < avg_valley * 0.01:
            continue

        # Two valleys approximately equal
        if abs(v1[1] - v2[1]) > height * tol_ratio:
            continue

        patterns.append({
            "valley1_idx": v1[0],
            "valley1_price": v1[1],
            "peak_idx": peak[0],
            "peak_price": peak[1],
            "valley2_idx": v2[0],
            "valley2_price": v2[1],
            "height": height,
            "neckline": peak[1],
            "target": peak[1] + height,
        })

    # For each bar after Valley2, check if close breaks above neckline
    for pat in patterns:
        confirmed = False
        for j in range(pat["valley2_idx"] + 1, n):
            if confirmed:
                break
            if closes[j] > pat["neckline"]:
                # Breakout confirmed on this bar
                db_signal[j] = 1
                db_neckline[j] = pat["neckline"]
                db_target[j] = pat["target"]
                confirmed = True

    return pd.DataFrame({
        "DB_signal": db_signal,
        "DB_neckline": db_neckline,
        "DB_target": db_target,
    }, index=df.index)
