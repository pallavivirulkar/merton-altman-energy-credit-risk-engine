"""
early_warning.py
=================
Rule-based Early Warning System. Monitors 8 indicators and flags exactly
which metric(s) triggered a warning (Section 27). Thresholds are project-
defined, documented conventions (not regulatory or rating-agency standards).

Thresholds (project-defined - see docs/assumptions.md):
    Debt/EBITDA        > 3.5x         -> triggered
    Interest Coverage   < 3.0x         -> triggered
    FCF/Debt            < 0.05 (5%)    -> triggered
    Current Ratio(proxy)< 1.0x         -> triggered
    Merton DD           < 3.0          -> triggered  (this project's
                                           "Elevated Risk" tier boundary)
    Merton PD (risk-neutral) > 1.0%    -> triggered
    Altman Z''          < 4.50         -> triggered  (Distress Zone)
    Equity volatility    > 35%          -> triggered  (top of observed range)

Classification:
    0 triggers  -> Green   (no warning)
    1 trigger   -> Yellow
    2-3 triggers-> Orange
    4+ triggers -> Red
"""
from __future__ import annotations
import pandas as pd

THRESHOLDS = {
    "debt_to_ebitda": (">", 3.5),
    "interest_coverage_ebit": ("<", 3.0),
    "fcf_to_debt": ("<", 0.05),
    "current_ratio_proxy": ("<", 1.0),
    "merton_dd": ("<", 3.0),
    "merton_pd": (">", 0.01),
    "altman_z_em": ("<", 4.50),
    "volatility_1y": (">", 0.35),
}


def evaluate(row: dict) -> dict:
    triggered = []
    for metric, (direction, threshold) in THRESHOLDS.items():
        val = row.get(metric)
        if val is None or pd.isna(val):
            continue
        if direction == ">" and val > threshold:
            triggered.append(f"{metric} = {val:.3g} (threshold > {threshold})")
        elif direction == "<" and val < threshold:
            triggered.append(f"{metric} = {val:.3g} (threshold < {threshold})")

    n = len(triggered)
    if n == 0:
        level = "Green"
    elif n == 1:
        level = "Yellow"
    elif n <= 3:
        level = "Orange"
    else:
        level = "Red"

    return {"warning_level": level, "n_triggers": n, "triggered_metrics": "; ".join(triggered) if triggered else "None"}


def run_early_warning(comparison: pd.DataFrame, ratios25: pd.DataFrame, mkt: pd.DataFrame) -> pd.DataFrame:
    df = comparison.merge(ratios25[["company", "fcf_to_debt"]], on="company", how="left", suffixes=("", "_r"))
    df = df.merge(mkt[["company", "volatility_1y_pct"]], on="company", how="left")
    df["volatility_1y"] = df["volatility_1y_pct"] / 100.0

    results = []
    for _, row in df.iterrows():
        r = evaluate(row.to_dict())
        results.append({"company": row["company"], **r})
    out = pd.DataFrame(results)
    return df.merge(out, on="company")


if __name__ == "__main__":
    from run_pipeline import build_all
    out = build_all()
    ratios25 = out["ratios"][out["ratios"]["fy"] == 2025]
    ew = run_early_warning(out["comparison"], ratios25, out["mkt"])
    print(ew[["company", "warning_level", "n_triggers", "triggered_metrics"]].to_string())
