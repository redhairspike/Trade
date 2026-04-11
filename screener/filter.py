from dataclasses import dataclass
import pandas as pd


@dataclass
class FilterRule:
    field: str      # Column name (e.g. "PE", "ROE")
    operator: str   # ">", "<", ">=", "<=", "==", "between"
    value: float    # Threshold value
    value2: float | None = None  # Second value for "between"


def screen(df: pd.DataFrame, rules: list[FilterRule]) -> pd.DataFrame:
    """Apply filter rules to a fundamentals DataFrame.

    All rules are combined with AND logic.
    Returns the filtered DataFrame.
    """
    if df.empty or not rules:
        return df

    mask = pd.Series(True, index=df.index)

    for rule in rules:
        if rule.field not in df.columns:
            continue

        col = pd.to_numeric(df[rule.field], errors="coerce")

        if rule.operator == ">":
            mask &= col > rule.value
        elif rule.operator == "<":
            mask &= col < rule.value
        elif rule.operator == ">=":
            mask &= col >= rule.value
        elif rule.operator == "<=":
            mask &= col <= rule.value
        elif rule.operator == "==":
            mask &= col == rule.value
        elif rule.operator == "between":
            if rule.value2 is not None:
                mask &= (col >= rule.value) & (col <= rule.value2)

    return df[mask].reset_index(drop=True)
