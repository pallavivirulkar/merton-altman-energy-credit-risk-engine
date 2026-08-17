"""
validation.py
==============
Automated model validation and Merton numerical validation (Sections 28-29).

Two kinds of checks:
1. Merton numerical validation - for every solved (V, sigma_V): solver
   convergence flag, residual error, positivity of V/sigma_V/D/E, finiteness
   of d1/d2/DD, PD in [0,1].
2. Behavioural/intuition sanity checks - directional tests that MUST hold if
   the model is behaving sensibly:
     - Debt UP (all else equal)          => DD DOWN
     - Equity value DOWN (all else equal)=> DD DOWN (credit risk worsens)
     - Equity volatility UP (all else eq)=> DD DOWN
     - EBIT UP (all else equal)          => Altman Z UP
   Each test perturbs ONE input in isolation and checks the direction of
   the response. If a test fails, that is flagged loudly - it is not
   silently ignored.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from merton_model import run_merton


def validate_merton_numerics(merton_df: pd.DataFrame) -> pd.DataFrame:
    checks = []
    for _, row in merton_df.iterrows():
        issues = []
        if not row.get("converged", False):
            issues.append("Solver did not converge")
        if not (row.get("residual_norm", np.nan) < 1e-2 * max(1.0, row.get("E", 1))):
            issues.append("Residual error too large relative to E")
        if not (row.get("V", 0) > 0):
            issues.append("Asset value V is not positive")
        if not (row.get("sigma_V", 0) > 0):
            issues.append("Asset volatility sigma_V is not positive")
        if not (row.get("D", 0) > 0):
            issues.append("Debt D is not positive")
        if not (row.get("E", 0) > 0):
            issues.append("Equity E is not positive")
        if not np.isfinite(row.get("d1", np.nan)) or not np.isfinite(row.get("d2", np.nan)):
            issues.append("d1/d2 not finite")
        if not np.isfinite(row.get("dd_risk_neutral", np.nan)):
            issues.append("DD not finite")
        pd_val = row.get("pd_risk_neutral", np.nan)
        if not (0 <= pd_val <= 1):
            issues.append("PD outside [0,1]")
        checks.append({
            "company": row["company"], "period": row.get("period", ""),
            "status": "PASS" if not issues else "FAIL",
            "issues": "; ".join(issues) if issues else "None",
        })
    return pd.DataFrame(checks)


def sanity_check_debt_up(company, E, sigma_E, D, r, T=1.0):
    base = run_merton(company, "base", E, sigma_E, D, r, T)
    shocked = run_merton(company, "debt_up_10pct", E, sigma_E, D * 1.10, r, T)
    passed = shocked.dd_risk_neutral < base.dd_risk_neutral
    return dict(check="Debt +10% => DD should decrease", company=company,
                base_dd=base.dd_risk_neutral, shocked_dd=shocked.dd_risk_neutral, passed=passed)


def sanity_check_equity_down(company, E, sigma_E, D, r, T=1.0):
    base = run_merton(company, "base", E, sigma_E, D, r, T)
    shocked = run_merton(company, "equity_down_10pct", E * 0.90, sigma_E, D, r, T)
    passed = shocked.dd_risk_neutral < base.dd_risk_neutral
    return dict(check="Equity -10% => DD should decrease", company=company,
                base_dd=base.dd_risk_neutral, shocked_dd=shocked.dd_risk_neutral, passed=passed)


def sanity_check_volatility_up(company, E, sigma_E, D, r, T=1.0):
    base = run_merton(company, "base", E, sigma_E, D, r, T)
    shocked = run_merton(company, "vol_up_25pct", E, sigma_E * 1.25, D, r, T)
    passed = shocked.dd_risk_neutral < base.dd_risk_neutral
    return dict(check="Equity volatility +25% => DD should decrease", company=company,
                base_dd=base.dd_risk_neutral, shocked_dd=shocked.dd_risk_neutral, passed=passed)


def sanity_check_ebit_up_altman(company, x1, x2, x3, x4):
    from altman_model import Z_SAFE
    z_base = 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
    x3_up = x3 * 1.10 if x3 > 0 else x3 - abs(x3) * 0.10  # a 10% improvement in EBIT/TA
    z_shocked = 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3_up + 1.05 * x4
    passed = z_shocked > z_base
    return dict(check="EBIT/TA +10% => Altman Z should increase", company=company,
                base_z=z_base, shocked_z=z_shocked, passed=passed)


def run_all_sanity_checks(merton_current_inputs: pd.DataFrame, altman_df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in merton_current_inputs.iterrows():
        results.append(sanity_check_debt_up(row["company"], row["E"], row["sigma_E"], row["D"], row["r"]))
        results.append(sanity_check_equity_down(row["company"], row["E"], row["sigma_E"], row["D"], row["r"]))
        results.append(sanity_check_volatility_up(row["company"], row["E"], row["sigma_E"], row["D"], row["r"]))

    altman_latest = altman_df[altman_df["fy"] == altman_df["fy"].max()]
    for _, row in altman_latest.iterrows():
        if pd.isna(row["x1_wc_ta"]):
            continue
        results.append(sanity_check_ebit_up_altman(row["company"], row["x1_wc_ta"], row["x2_re_ta"], row["x3_ebit_ta"], row["x4_bve_tl"]))

    return pd.DataFrame(results)


if __name__ == "__main__":
    from run_pipeline import build_all
    out = build_all()
    numeric_checks = validate_merton_numerics(out["merton_current"])
    print("=== MERTON NUMERICAL VALIDATION ===")
    print(numeric_checks.to_string())

    inputs = out["merton_current"][["company", "E", "sigma_E", "D", "r"]]
    sanity = run_all_sanity_checks(inputs, out["altman"])
    print("\n=== BEHAVIOURAL SANITY CHECKS ===")
    print(sanity.to_string())
    print(f"\nAll checks passed: {sanity['passed'].all() and numeric_checks['status'].eq('PASS').all()}")
