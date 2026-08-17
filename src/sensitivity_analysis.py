"""
sensitivity_analysis.py
========================
Section 30: sensitivity of Merton DD to each input assumption, in isolation.
Produces a long-format table suitable for heatmaps (see visualization.py).

Perturbations tested: equity volatility (sigma_E), Debt (D), Equity value (E)
each at +/-10%, +/-25%, +/-50%; risk-free rate (r) over a realistic range
(+/-100bp, +/-200bp); time horizon T in {1, 2, 3} years.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from merton_model import run_merton

PCT_SHOCKS = [-0.50, -0.25, -0.10, 0.0, 0.10, 0.25, 0.50]
RATE_SHOCKS_BP = [-200, -100, 0, 100, 200]
HORIZONS = [1, 2, 3]


def sensitivity_table(merton_inputs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, base in merton_inputs.iterrows():
        company, E0, sigma0, D0, r0 = base["company"], base["E"], base["sigma_E"], base["D"], base["r"]
        base_res = run_merton(company, "base", E0, sigma0, D0, r0, 1.0)

        for shock in PCT_SHOCKS:
            res = run_merton(company, f"sigmaE {shock:+.0%}", E0, sigma0 * (1 + shock), D0, r0, 1.0)
            rows.append(dict(company=company, driver="Equity Volatility", shock=shock, dd=res.dd_risk_neutral, converged=res.converged))

        for shock in PCT_SHOCKS:
            res = run_merton(company, f"D {shock:+.0%}", E0, sigma0, D0 * (1 + shock), r0, 1.0)
            rows.append(dict(company=company, driver="Debt", shock=shock, dd=res.dd_risk_neutral, converged=res.converged))

        for shock in PCT_SHOCKS:
            res = run_merton(company, f"E {shock:+.0%}", E0 * (1 + shock), sigma0, D0, r0, 1.0)
            rows.append(dict(company=company, driver="Equity Value", shock=shock, dd=res.dd_risk_neutral, converged=res.converged))

        for bp in RATE_SHOCKS_BP:
            res = run_merton(company, f"r {bp:+d}bp", E0, sigma0, D0, r0 + bp / 10000, 1.0)
            rows.append(dict(company=company, driver="Risk-Free Rate", shock=bp / 10000, dd=res.dd_risk_neutral, converged=res.converged))

        for T in HORIZONS:
            res = run_merton(company, f"T={T}y", E0, sigma0, D0, r0, float(T))
            rows.append(dict(company=company, driver="Time Horizon", shock=T, dd=res.dd_risk_neutral, converged=res.converged))

    df = pd.DataFrame(rows)
    base_dd = merton_inputs.set_index("company").apply(
        lambda r: run_merton(r.name, "base", r["E"], r["sigma_E"], r["D"], r["r"], 1.0).dd_risk_neutral, axis=1)
    df["base_dd"] = df["company"].map(base_dd)
    df["dd_change_from_base"] = df["dd"] - df["base_dd"]
    return df


def most_impactful_driver(sens_df: pd.DataFrame) -> pd.DataFrame:
    """For each company, rank drivers by the RANGE of DD produced across the
    +/-50% (or equivalent) shock band - answers 'which assumption matters most'."""
    pct_drivers = sens_df[sens_df["driver"].isin(["Equity Volatility", "Debt", "Equity Value"])]
    rng = pct_drivers.groupby(["company", "driver"])["dd"].agg(lambda s: s.max() - s.min()).reset_index()
    rng = rng.rename(columns={"dd": "dd_range_across_shocks"})
    rng["rank_within_company"] = rng.groupby("company")["dd_range_across_shocks"].rank(ascending=False)
    return rng.sort_values(["company", "rank_within_company"])


if __name__ == "__main__":
    from run_pipeline import build_all
    out = build_all()
    inputs = out["merton_current"][["company", "E", "sigma_E", "D", "r"]]
    sens = sensitivity_table(inputs)
    sens.to_csv(os.path.join(os.path.dirname(__file__), "..", "data", "processed", "sensitivity_analysis.csv"), index=False)
    print(sens[sens["company"] == "HPCL"].to_string())
    print("\n=== MOST IMPACTFUL DRIVER PER COMPANY ===")
    print(most_impactful_driver(sens).to_string())
