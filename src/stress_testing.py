"""
stress_testing.py
==================
Energy-sector stress testing engine. All scenarios are clearly labeled
SCENARIO ASSUMPTIONS, not forecasts (Section 23). Propagates shocks through
EBITDA/EBIT -> interest coverage, Debt/EBITDA, FCF/Debt, Merton DD/PD, and
the custom credit score.

Business-model-specific severity multipliers (Section 24): the SAME
percentage input shock is applied to all companies for comparability, but
where the brief calls for differentiated assumptions (upstream = pure
commodity-price pass-through; refiners = margin + working-capital; gas
transmission = volume/utilisation; diversified = simplified consolidated)
we apply a documented severity multiplier reflecting each business model's
typical operating leverage to a given macro shock. This is a project-defined
assumption, not an empirical estimate - see docs/assumptions.md.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from merton_model import run_merton

# Business-model severity multipliers applied to a common "oil/energy shock"
# (documented project assumption - NOT an empirical elasticity estimate)
BUSINESS_MODEL_MULTIPLIER = {
    "Upstream (E&P)": 1.30,                       # highest direct commodity-price pass-through
    "Refining & Marketing (Downstream)": 1.10,     # margin + inventory/working-capital sensitivity
    "Gas Transmission & Distribution": 0.60,       # regulated tariff, volume-driven, lower price pass-through
    "Diversified (O2C, Retail, Digital)": 0.50,    # only part of the business (O2C) is energy-price sensitive
}


def apply_profitability_shock(fin_fy: pd.DataFrame, shock_pct: float, universe: pd.DataFrame,
                                differentiated: bool = False) -> pd.DataFrame:
    """shock_pct: e.g. -0.10 for a 10% EBITDA decline."""
    df = fin_fy.merge(universe[["company", "business_model"]], on="company", how="left")
    if differentiated:
        mult = df["business_model"].map(BUSINESS_MODEL_MULTIPLIER).fillna(1.0)
    else:
        mult = 1.0
    effective_shock = shock_pct * mult
    df["ebitda_stressed"] = df["operating_profit"] * (1 + effective_shock)
    df["ebit_stressed"] = df["ebitda_stressed"] - df["depreciation"]
    df["interest_coverage_stressed"] = df["ebit_stressed"] / df["interest"]
    df["debt_to_ebitda_stressed"] = df["borrowings"] / df["ebitda_stressed"]
    df["fcf_stressed"] = df["fcf"] + (df["ebitda_stressed"] - df["operating_profit"])  # flow shock through FCF 1:1
    df["fcf_to_debt_stressed"] = df["fcf_stressed"] / df["borrowings"]
    df["effective_shock_pct"] = effective_shock
    return df


def apply_debt_shock(fin_fy: pd.DataFrame, shock_pct: float) -> pd.DataFrame:
    df = fin_fy.copy()
    df["debt_stressed"] = df["borrowings"] * (1 + shock_pct)
    df["debt_to_ebitda_stressed"] = df["debt_stressed"] / df["operating_profit"]
    df["debt_to_equity_stressed"] = df["debt_stressed"] / (df["equity_capital"] + df["reserves"])
    return df


def apply_equity_shock(mkt: pd.DataFrame, shock_pct: float) -> pd.DataFrame:
    df = mkt.copy()
    df["market_cap_stressed"] = df["market_cap_cr"] * (1 + shock_pct)
    return df


def merton_under_scenario(company, E, sigma_E, D, r, T=1.0, erp=0.07):
    res = run_merton(company, "scenario", E, sigma_E, D, r, T, erp)
    return res.dd_risk_neutral, res.pd_risk_neutral, res.converged


def run_scenario_suite(fin25: pd.DataFrame, mkt: pd.DataFrame, universe: pd.DataFrame, r: float = 0.0676) -> pd.DataFrame:
    """Runs profitability, debt, and equity shocks (each in isolation) and
    recomputes Merton DD/PD + key ratios for every company. Returns a long
    dataframe: one row per (company, scenario)."""
    rows = []
    mkt_idx = mkt.set_index("company")

    scenarios = (
        [("Profitability -10%", "profitability", -0.10)] +
        [("Profitability -20%", "profitability", -0.20)] +
        [("Profitability -30%", "profitability", -0.30)] +
        [("Debt +10%", "debt", 0.10)] +
        [("Debt +25%", "debt", 0.25)] +
        [("Debt +50%", "debt", 0.50)] +
        [("Equity -10%", "equity", -0.10)] +
        [("Equity -20%", "equity", -0.20)] +
        [("Equity -30%", "equity", -0.30)] +
        [("Equity -40%", "equity", -0.40)]
    )

    for _, row in fin25.iterrows():
        company = row["company"]
        E0 = mkt_idx.loc[company, "market_cap_cr"]
        sigma_E0 = mkt_idx.loc[company, "volatility_1y_pct"] / 100.0
        D0 = row["borrowings"]
        ebitda0 = row["operating_profit"]

        # baseline
        dd0, pd0, conv0 = merton_under_scenario(company, E0, sigma_E0, D0, r)
        rows.append(dict(company=company, scenario="Baseline (FY2025)", dd=dd0, pd_=pd0, converged=conv0,
                          debt_to_ebitda=D0 / ebitda0, interest_coverage=(ebitda0 - row["depreciation"]) / row["interest"]))

        for label, kind, mag in scenarios:
            if kind == "profitability":
                ebitda_s = ebitda0 * (1 + mag)
                ebit_s = ebitda_s - row["depreciation"]
                dd, pd_, conv = merton_under_scenario(company, E0, sigma_E0, D0, r)  # profitability shock doesn't directly move E/D in this isolated test
                rows.append(dict(company=company, scenario=label, dd=dd, pd_=pd_, converged=conv,
                                  debt_to_ebitda=D0 / ebitda_s if ebitda_s != 0 else np.nan,
                                  interest_coverage=ebit_s / row["interest"]))
            elif kind == "debt":
                D_s = D0 * (1 + mag)
                dd, pd_, conv = merton_under_scenario(company, E0, sigma_E0, D_s, r)
                rows.append(dict(company=company, scenario=label, dd=dd, pd_=pd_, converged=conv,
                                  debt_to_ebitda=D_s / ebitda0, interest_coverage=(ebitda0 - row["depreciation"]) / row["interest"]))
            elif kind == "equity":
                E_s = E0 * (1 + mag)
                dd, pd_, conv = merton_under_scenario(company, E_s, sigma_E0, D0, r)
                rows.append(dict(company=company, scenario=label, dd=dd, pd_=pd_, converged=conv,
                                  debt_to_ebitda=D0 / ebitda0, interest_coverage=(ebitda0 - row["depreciation"]) / row["interest"]))
    return pd.DataFrame(rows)


def combined_bear_case(fin25: pd.DataFrame, mkt: pd.DataFrame, r_base: float = 0.0676) -> pd.DataFrame:
    """Section 25: revenue/EBITDA -25%, debt +25%, equity -30%, equity vol +50%."""
    mkt_idx = mkt.set_index("company")
    rows = []
    for _, row in fin25.iterrows():
        company = row["company"]
        E0 = mkt_idx.loc[company, "market_cap_cr"]
        sigma_E0 = mkt_idx.loc[company, "volatility_1y_pct"] / 100.0
        D0 = row["borrowings"]
        ebitda0 = row["operating_profit"]

        dd0, pd0, conv0 = merton_under_scenario(company, E0, sigma_E0, D0, r_base)

        E_bear = E0 * (1 - 0.30)
        sigma_bear = sigma_E0 * 1.50
        D_bear = D0 * 1.25
        ebitda_bear = ebitda0 * (1 - 0.25)
        ebit_bear = ebitda_bear - row["depreciation"]

        dd_bear, pd_bear, conv_bear = merton_under_scenario(company, E_bear, sigma_bear, D_bear, r_base)

        rows.append(dict(
            company=company,
            dd_base=dd0, pd_base=pd0,
            dd_bear=dd_bear, pd_bear=pd_bear,
            debt_to_ebitda_base=D0 / ebitda0, debt_to_ebitda_bear=D_bear / ebitda_bear,
            interest_coverage_base=(ebitda0 - row["depreciation"]) / row["interest"],
            interest_coverage_bear=ebit_bear / row["interest"],
            dd_change=dd_bear - dd0,
        ))
    return pd.DataFrame(rows)


def reverse_stress_test(fin25: pd.DataFrame, mkt: pd.DataFrame, r_base: float = 0.0676,
                          target_dd: float = 3.0, max_equity_decline: float = 0.95,
                          max_debt_increase: float = 3.0) -> pd.DataFrame:
    """For each company, find the approximate equity decline (%) needed,
    holding debt and vol constant, to push Merton DD down to target_dd (the
    Moderate->Elevated Risk boundary, DD=3, per this project's tier
    definitions). Uses bisection over a PLAUSIBLE scenario range only
    (equity decline up to 95%; debt increase up to +300%). If the target is
    not reached within that plausible range, this is reported explicitly as
    "not reached" (structural resilience) rather than extrapolated to an
    implausible multiple, which would misrepresent precision that isn't
    there - see docs/limitations.md."""
    mkt_idx = mkt.set_index("company")
    rows = []
    for _, row in fin25.iterrows():
        company = row["company"]
        E0 = mkt_idx.loc[company, "market_cap_cr"]
        sigma_E0 = mkt_idx.loc[company, "volatility_1y_pct"] / 100.0
        D0 = row["borrowings"]

        # --- equity-decline search ---
        dd_at_max_decline, _, _ = merton_under_scenario(company, E0 * (1 - max_equity_decline), sigma_E0, D0, r_base)
        if dd_at_max_decline > target_dd:
            equity_decline_needed = np.nan
            equity_note = f"Not reached within tested range (up to -{max_equity_decline*100:.0f}% equity); DD at -{max_equity_decline*100:.0f}% is still {dd_at_max_decline:.2f}"
        else:
            lo, hi = -max_equity_decline, 0.0
            for _ in range(40):
                mid = (lo + hi) / 2
                E_test = E0 * (1 + mid)
                dd, _, conv = merton_under_scenario(company, E_test, sigma_E0, D0, r_base)
                if not conv:
                    break
                if dd > target_dd:
                    hi = mid
                else:
                    lo = mid
            equity_decline_needed = mid * 100
            equity_note = "Reached within tested range"

        # --- debt-increase search ---
        dd_at_max_debt, _, _ = merton_under_scenario(company, E0, sigma_E0, D0 * (1 + max_debt_increase), r_base)
        if dd_at_max_debt > target_dd:
            debt_increase_needed = np.nan
            debt_note = f"Not reached within tested range (up to +{max_debt_increase*100:.0f}% debt); DD at +{max_debt_increase*100:.0f}% is still {dd_at_max_debt:.2f}"
        else:
            lo2, hi2 = 0.0, max_debt_increase
            for _ in range(40):
                mid2 = (lo2 + hi2) / 2
                D_test = D0 * (1 + mid2)
                dd2, _, conv2 = merton_under_scenario(company, E0, sigma_E0, D_test, r_base)
                if not conv2:
                    break
                if dd2 > target_dd:
                    lo2 = mid2
                else:
                    hi2 = mid2
            debt_increase_needed = mid2 * 100
            debt_note = "Reached within tested range"

        rows.append(dict(company=company, target_dd=target_dd,
                          equity_decline_needed_pct=equity_decline_needed, equity_note=equity_note,
                          debt_increase_needed_pct=debt_increase_needed, debt_note=debt_note))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from run_pipeline import build_all
    out = build_all()
    fin25 = out["fin"][out["fin"]["fy"] == 2025]

    print("=== SCENARIO SUITE (sample) ===")
    scen = run_scenario_suite(fin25, out["mkt"], out["universe"])
    print(scen[scen["company"] == "HPCL"].to_string())

    print("\n=== COMBINED BEAR CASE ===")
    bear = combined_bear_case(fin25, out["mkt"])
    print(bear.to_string())

    print("\n=== REVERSE STRESS TEST (target DD=3.0) ===")
    rst = reverse_stress_test(fin25, out["mkt"])
    print(rst.to_string())

    print("\n=== DIFFERENTIATED PROFITABILITY SHOCK (-20%, business-model weighted) ===")
    diff = apply_profitability_shock(fin25, -0.20, out["universe"], differentiated=True)
    print(diff[["company", "business_model", "effective_shock_pct", "interest_coverage_stressed", "debt_to_ebitda_stressed"]].to_string())
