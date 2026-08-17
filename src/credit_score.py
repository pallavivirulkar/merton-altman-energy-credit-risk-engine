"""
credit_score.py
================
PROJECT-DEFINED SCORING METHODOLOGY - Energy Corporate Credit Score (0-100)

This is explicitly a project-defined composite, NOT an industry-standard
credit score and NOT equivalent to a CRISIL/ICRA/Moody's/S&P rating. It is
built transparently from the two core models plus supporting ratios so a
reader can trace exactly how the number was built (Section 21).

Dimensions and INITIAL weights (documented, testable - see sensitivity()):
    Structural Risk (Merton DD)            30%
    Accounting/Financial Health (Altman Z) 30%
    Debt Servicing (Debt/EBITDA + ICR)     20%
    Liquidity (Current Ratio, proxy)       10%
    Cash Flow Quality (FCF/Debt, CFO/Debt) 10%

Each raw metric is mapped to a 0-100 sub-score using a documented, capped
LINEAR anchor scale (not peer-relative min-max, so the score retains some
absolute meaning and is not purely a beauty contest among 7 companies).
Anchors were chosen from the observed range of this project's own data
(e.g. DD=10 as the top anchor, since the strongest observed company,
Reliance, prints DD~10.3) - this is disclosed, not hidden.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def _clip_linear(x, lo_val, hi_val, invert=False):
    if pd.isna(x):
        return np.nan
    score = (x - lo_val) / (hi_val - lo_val) * 100
    if invert:
        score = 100 - score
    return float(np.clip(score, 0, 100))


DEFAULT_WEIGHTS = dict(structural=0.30, accounting=0.30, debt_service=0.20, liquidity=0.10, cash_flow=0.10)


def compute_credit_score(merton_dd, altman_z, debt_to_ebitda, interest_coverage,
                          current_ratio, fcf_to_debt, cfo_to_debt, weights=None) -> dict:
    weights = weights or DEFAULT_WEIGHTS

    structural_score = _clip_linear(merton_dd, 0, 10.0)
    accounting_score = _clip_linear(altman_z, 0, 8.15)
    debt_ebitda_score = _clip_linear(debt_to_ebitda, 0, 8.0, invert=True)
    icr_score = _clip_linear(interest_coverage, 0, 15.0)
    debt_service_score = np.nanmean([debt_ebitda_score, icr_score])
    liquidity_score = _clip_linear(current_ratio, 0, 2.0)
    fcf_score = _clip_linear(fcf_to_debt, -0.20, 0.50)
    cfo_score = _clip_linear(cfo_to_debt, 0, 0.50)
    cash_flow_score = np.nanmean([fcf_score, cfo_score])

    composite = (
        weights["structural"] * (structural_score if not pd.isna(structural_score) else 0) +
        weights["accounting"] * (accounting_score if not pd.isna(accounting_score) else 0) +
        weights["debt_service"] * (debt_service_score if not pd.isna(debt_service_score) else 0) +
        weights["liquidity"] * (liquidity_score if not pd.isna(liquidity_score) else 0) +
        weights["cash_flow"] * (cash_flow_score if not pd.isna(cash_flow_score) else 0)
    )

    return dict(
        structural_score=structural_score, accounting_score=accounting_score,
        debt_service_score=debt_service_score, liquidity_score=liquidity_score,
        cash_flow_score=cash_flow_score, energy_credit_score=round(composite, 1),
    )


def score_all(comparison: pd.DataFrame, weights=None) -> pd.DataFrame:
    rows = []
    for _, row in comparison.iterrows():
        s = compute_credit_score(
            row["merton_dd"], row["altman_z_em"], row["debt_to_ebitda"],
            row["interest_coverage_ebit"], row["current_ratio_proxy"],
            row["fcf_to_debt"], row.get("cfo_to_debt", np.nan), weights=weights,
        )
        rows.append({"company": row["company"], **s})
    df = pd.DataFrame(rows).sort_values("energy_credit_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def sensitivity_to_weights(comparison: pd.DataFrame) -> pd.DataFrame:
    """Section 21: test sensitivity of the composite score/ranking to the
    chosen weights. Compares the default weighting against an equal-weight
    scheme and a 'market-heavy' (Merton-dominant) scheme."""
    schemes = {
        "default (30/30/20/10/10)": DEFAULT_WEIGHTS,
        "equal_weight (20/20/20/20/20)": dict(structural=0.20, accounting=0.20, debt_service=0.20, liquidity=0.20, cash_flow=0.20),
        "market_heavy (50/15/15/10/10)": dict(structural=0.50, accounting=0.15, debt_service=0.15, liquidity=0.10, cash_flow=0.10),
        "accounting_heavy (15/50/15/10/10)": dict(structural=0.15, accounting=0.50, debt_service=0.15, liquidity=0.10, cash_flow=0.10),
    }
    out = None
    for name, w in schemes.items():
        s = score_all(comparison, weights=w)[["company", "energy_credit_score", "rank"]]
        s = s.rename(columns={"energy_credit_score": f"score_{name}", "rank": f"rank_{name}"})
        out = s if out is None else out.merge(s, on="company")
    return out


if __name__ == "__main__":
    from run_pipeline import build_all
    out = build_all()
    scored = score_all(out["comparison"])
    print(scored.to_string())
    print("\n=== WEIGHT SENSITIVITY ===")
    print(sensitivity_to_weights(out["comparison"]).to_string())
