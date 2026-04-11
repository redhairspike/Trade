import pandas as pd
import numpy as np
from indicators.base import register


@register("Pivot", {"pivot_type": 1})
def pivot_points(df: pd.DataFrame, pivot_type: int = 1) -> pd.DataFrame:
    """Pivot Points — 用前一根 K 棒的 OHLC 計算當根的樞軸支撐壓力。

    pivot_type:
        1 = Standard (Floor)
        2 = Fibonacci
        3 = Camarilla
        4 = Woodie
    """
    h = df["High"].shift(1)
    l = df["Low"].shift(1)
    c = df["Close"].shift(1)

    if pivot_type == 4:
        # Woodie: 加重收盤價
        p = (h + l + 2 * c) / 4
    else:
        # Standard pivot
        p = (h + l + c) / 3

    rng = h - l  # previous bar range

    if pivot_type == 1:
        # Standard (Floor)
        r1 = 2 * p - l
        s1 = 2 * p - h
        r2 = p + rng
        s2 = p - rng
        r3 = h + 2 * (p - l)
        s3 = l - 2 * (h - p)

    elif pivot_type == 2:
        # Fibonacci
        r1 = p + 0.382 * rng
        s1 = p - 0.382 * rng
        r2 = p + 0.618 * rng
        s2 = p - 0.618 * rng
        r3 = p + rng
        s3 = p - rng

    elif pivot_type == 3:
        # Camarilla
        r1 = c + rng * 1.1 / 12
        s1 = c - rng * 1.1 / 12
        r2 = c + rng * 1.1 / 6
        s2 = c - rng * 1.1 / 6
        r3 = c + rng * 1.1 / 4
        s3 = c - rng * 1.1 / 4

    elif pivot_type == 4:
        # Woodie
        r1 = 2 * p - l
        s1 = 2 * p - h
        r2 = p + rng
        s2 = p - rng
        r3 = h + 2 * (p - l)
        s3 = l - 2 * (h - p)

    else:
        raise ValueError(f"Unknown pivot_type: {pivot_type}. Use 1-4.")

    return pd.DataFrame({
        "Pivot_P": p,
        "Pivot_R1": r1,
        "Pivot_S1": s1,
        "Pivot_R2": r2,
        "Pivot_S2": s2,
        "Pivot_R3": r3,
        "Pivot_S3": s3,
    }, index=df.index)


@register("SRLevel", {"order": 5, "merge_pct": 1})
def sr_levels(df: pd.DataFrame, order: int = 5, merge_pct: int = 1) -> pd.DataFrame:
    """Support/Resistance via Local Extrema Detection.

    在 High 上找局部高點 (壓力)，在 Low 上找局部低點 (支撐)。
    對每根 K 棒，回傳距離收盤價最近的支撐和壓力價位。

    Args:
        order: 前後各幾根 K 棒判斷局部極值 (類似 scipy.find_peaks 的 distance)
        merge_pct: 合併容差百分比，相距 merge_pct% 內的極值合併為一個水平
    """
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    n = len(df)

    # --- 找局部極值 ---
    resistance_indices = _find_local_max(highs, order)
    support_indices = _find_local_min(lows, order)

    # --- 合併相近水平 ---
    merge_ratio = merge_pct / 100.0
    resistance_levels = _merge_levels(highs, resistance_indices, merge_ratio)
    support_levels = _merge_levels(lows, support_indices, merge_ratio)

    # --- 對每根 K 棒找最近支撐壓力 ---
    sr_resistance = np.full(n, np.nan)
    sr_support = np.full(n, np.nan)

    for i in range(n):
        price = closes[i]

        # 只用已出現過的極值 (不偷看未來)
        # Resistance: 離收盤價最近且高於收盤價的水平
        valid_r = [lvl for idx, lvl in resistance_levels if idx <= i and lvl > price]
        if valid_r:
            sr_resistance[i] = min(valid_r, key=lambda x: x - price)

        # Support: 離收盤價最近且低於收盤價的水平
        valid_s = [lvl for idx, lvl in support_levels if idx <= i and lvl < price]
        if valid_s:
            sr_support[i] = max(valid_s, key=lambda x: price - x)

    return pd.DataFrame({
        "SR_resistance": sr_resistance,
        "SR_support": sr_support,
    }, index=df.index)


def _find_local_max(data: np.ndarray, order: int) -> list[int]:
    """找局部最高點的索引。"""
    indices = []
    for i in range(order, len(data) - order):
        if all(data[i] >= data[i - j] for j in range(1, order + 1)) and \
           all(data[i] >= data[i + j] for j in range(1, order + 1)):
            indices.append(i)
    return indices


def _find_local_min(data: np.ndarray, order: int) -> list[int]:
    """找局部最低點的索引。"""
    indices = []
    for i in range(order, len(data) - order):
        if all(data[i] <= data[i - j] for j in range(1, order + 1)) and \
           all(data[i] <= data[i + j] for j in range(1, order + 1)):
            indices.append(i)
    return indices


def _merge_levels(
    prices: np.ndarray, indices: list[int], merge_ratio: float
) -> list[tuple[int, float]]:
    """合併相近的極值水平。回傳 (最早出現的索引, 合併後的價格)。"""
    if not indices:
        return []

    # 按價格排序
    sorted_pairs = sorted([(i, prices[i]) for i in indices], key=lambda x: x[1])

    merged: list[tuple[int, float]] = []
    group_indices = [sorted_pairs[0][0]]
    group_prices = [sorted_pairs[0][1]]

    for j in range(1, len(sorted_pairs)):
        idx, price = sorted_pairs[j]
        avg_price = np.mean(group_prices)

        if abs(price - avg_price) / avg_price <= merge_ratio:
            # 同一組
            group_indices.append(idx)
            group_prices.append(price)
        else:
            # 結算前一組
            merged.append((min(group_indices), float(np.mean(group_prices))))
            group_indices = [idx]
            group_prices = [price]

    # 最後一組
    merged.append((min(group_indices), float(np.mean(group_prices))))
    return merged
