"""
run_pipeline.py
================
Master orchestrator: runs the full data -> ratios -> Altman -> Merton ->
comparison -> ranking -> credit score pipeline and writes all processed
tables to data/processed/ and outputs/tables/.

MERTON DATA TIMING (documented decision - see docs/assumptions.md)
---------------------------------------------------------------------
Primary Merton analysis ("current"):
    E, sigma_E   -> current snapshot (14-Aug-2026 market data)
    D            -> FY2025 borrowings (most recent audited balance sheet)
    r            -> current India 10Y G-Sec yield (14-Aug-2026, 6.76%)
    T            -> 1 year
This is the fully-rigorous, primary cross-sectional analysis.

Historical decomposition ("FY2021-FY2024, leverage-only view"):
    E, sigma_E   -> HELD CONSTANT at current snapshot values (documented
                    limitation: historical daily-return volatility / historical
                    market cap could not be retrieved - see limitations.md)
    D            -> that fiscal year's REAL, audited borrowings (varies)
    r            -> that fiscal year's REAL risk-free rate (varies)
    T            -> 1 year
This isolates the leverage-driven component of Distance-to-Default across
FY2021-FY2025 and is labeled "illustrative / leverage-only" everywhere it is
used. It is a legitimate, honest decomposition - NOT a claim about what
market conditions actually were in 2021-2024.
"""
from __future__ import annotations
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from data_cleaning import run_pipeline as clean_pipeline
from financial_ratios import compute_ratios
from altman_model import compute_altman, five_year_trend as altman_trend
from merton_model import run_merton

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROC_DIR = os.path.join(REPO_ROOT, "data", "processed")
TABLES_DIR = os.path.join(REPO_ROOT, "outputs", "tables")
CURRENT_RF_RATE = 0.0676  # TradingEconomics, 14-Aug-2026, cross-checked vs FRED series level
ERP = 0.07  # India total ERP, ~Jan-2026 vintage estimate (Damodaran-style), see assumptions.md


def build_all():
    os.makedirs(TABLES_DIR, exist_ok=True)
    fin, mkt, rfr, universe = clean_pipeline()
    ratios = compute_ratios(fin)
    altman = compute_altman(fin, mkt)

    # ---------------- MERTON: current snapshot (primary) ----------------
    fin25 = fin[fin["fy"] == 2025].set_index("company")
    mkt_idx = mkt.set_index("company")
    merton_current_rows = []
    for company in mkt_idx.index:
        merton_current_rows.append(dict(
            company=company, period="current_FY2025_debt",
            E=mkt_idx.loc[company, "market_cap_cr"],
            sigma_E=mkt_idx.loc[company, "volatility_1y_pct"] / 100.0,
            D=fin25.loc[company, "borrowings"],
            r=CURRENT_RF_RATE,
        ))
    merton_current = pd.DataFrame([
        {**{"company": r["company"], "period": r["period"]}, **run_merton(r["company"], r["period"], r["E"], r["sigma_E"], r["D"], r["r"], 1.0, ERP).__dict__}
        for r in merton_current_rows
    ])
    merton_current = merton_current.loc[:, ~merton_current.columns.duplicated()]

    # ---------------- MERTON: historical leverage-only decomposition ----------------
    rfr_idx = rfr.set_index("fy")
    hist_rows = []
    for _, row in fin.iterrows():
        company, fy = row["company"], row["fy"]
        hist_rows.append(dict(
            company=company, period=f"FY{fy}_leverage_only",
            E=mkt_idx.loc[company, "market_cap_cr"],
            sigma_E=mkt_idx.loc[company, "volatility_1y_pct"] / 100.0,
            D=row["borrowings"],
            r=rfr_idx.loc[fy, "rate_pct"] / 100.0,
            fy=fy,
        ))
    merton_hist = pd.DataFrame([
        {**{"company": r["company"], "period": r["period"], "fy": r["fy"]},
         **run_merton(r["company"], r["period"], r["E"], r["sigma_E"], r["D"], r["r"], 1.0, ERP).__dict__}
        for r in hist_rows
    ])
    merton_hist = merton_hist.loc[:, ~merton_hist.columns.duplicated()]

    merton_current.to_csv(os.path.join(PROC_DIR, "merton_current.csv"), index=False)
    merton_hist.to_csv(os.path.join(PROC_DIR, "merton_historical_leverage_only.csv"), index=False)
    ratios.to_csv(os.path.join(PROC_DIR, "financial_ratios.csv"), index=False)
    altman.to_csv(os.path.join(PROC_DIR, "altman_scores.csv"), index=False)
    altman_trend(altman).to_csv(os.path.join(PROC_DIR, "altman_5yr_trend.csv"), index=False)

    # ---------------- MODEL COMPARISON TABLE (current / FY2025) ----------------
    altman25 = altman[altman["fy"] == 2025][["company", "altman_z_em", "altman_zone"]]
    ratios25 = ratios[ratios["fy"] == 2025][["company", "debt_to_ebitda", "interest_coverage_ebit", "current_ratio_proxy", "fcf_to_debt"]]
    mc = merton_current[["company", "dd_risk_neutral", "pd_risk_neutral", "converged"]].rename(
        columns={"dd_risk_neutral": "merton_dd", "pd_risk_neutral": "merton_pd"})

    comparison = mc.merge(altman25, on="company").merge(ratios25, on="company").merge(
        universe[["company", "name", "business_model", "peer_group"]], on="company")

    def merton_tier(dd):
        if pd.isna(dd):
            return "N/A"
        if dd >= 5.0:
            return "Low Risk"
        if dd >= 3.0:
            return "Moderate Risk"
        return "Elevated Risk"

    def altman_tier(zone):
        return {"Safe Zone": "Low Risk", "Grey Zone": "Moderate Risk", "Distress Zone": "Elevated Risk"}.get(zone, "N/A")

    comparison["merton_tier"] = comparison["merton_dd"].apply(merton_tier)
    comparison["altman_tier"] = comparison["altman_zone"].apply(altman_tier)

    def signal(row):
        if row["merton_tier"] == row["altman_tier"]:
            return f"Agreement - {row['merton_tier']}"
        return f"Disagreement (Merton: {row['merton_tier']} / Altman: {row['altman_tier']})"

    comparison["overall_signal"] = comparison.apply(signal, axis=1)
    comparison = comparison[[
        "company", "name", "business_model", "peer_group", "merton_dd", "merton_pd",
        "altman_z_em", "altman_zone", "debt_to_ebitda", "interest_coverage_ebit",
        "current_ratio_proxy", "fcf_to_debt", "merton_tier", "altman_tier", "overall_signal",
    ]].sort_values("merton_dd", ascending=False)
    comparison.to_csv(os.path.join(TABLES_DIR, "model_comparison.csv"), index=False)

    return dict(fin=fin, mkt=mkt, rfr=rfr, universe=universe, ratios=ratios, altman=altman,
                merton_current=merton_current, merton_hist=merton_hist, comparison=comparison)


if __name__ == "__main__":
    out = build_all()
    print("=== MERTON CURRENT (primary) ===")
    print(out["merton_current"][["company", "E", "sigma_E", "D", "r", "V", "sigma_V", "dd_risk_neutral", "pd_risk_neutral", "converged"]].to_string())
    print("\n=== MODEL COMPARISON ===")
    print(out["comparison"].to_string())
