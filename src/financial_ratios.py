"""
financial_ratios.py
====================
Financial Ratio Engine. Computes liquidity, leverage, debt-servicing,
profitability, cash-flow and working-capital ratios for every company-year.

METHODOLOGY NOTES (read before interpreting Current/Quick ratio or CCC)
------------------------------------------------------------------------
Because the accessible data source reports an aggregated (not fully
classified) balance sheet, this module uses explicit, documented proxies:

  Current Assets (proxy)      = other_assets   (residual bucket: inventory,
                                  receivables, cash, loans & advances - for
                                  this sector overwhelmingly current)
  Current Liabilities (proxy) = other_liabilities (residual bucket: trade
                                  payables, statutory dues, short-term
                                  provisions - overwhelmingly current)

These are labeled "(proxy)" in every output column and in the dashboard.
They are NOT a substitute for a true classified balance sheet and will
overstate/understate liquidity ratios to the extent Other Assets/
Other Liabilities contain non-current items (e.g. deferred tax, long-term
provisions). This is flagged as a limitation in docs/limitations.md.

Inventory and Receivables, where needed for the Cash Conversion Cycle, are
backed out from disclosed turnover-day ratios (Debtor Days, Inventory Days)
rather than invented:
  Receivables  = Debtor Days / 365  * Sales
  Inventory    = Inventory Days / 365 * Sales   (Sales used as the turnover
                  base since COGS is not separately disclosed at this
                  granularity - documented simplification)
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def compute_ratios(fin: pd.DataFrame) -> pd.DataFrame:
    df = fin.copy()

    # ---- Core derived P&L items ----
    df["ebitda"] = df["operating_profit"]
    df["ebit"] = df["ebitda"] - df["depreciation"]  # operating EBIT, excl. other income (documented, uniform across all cos)
    df["total_equity"] = df["equity_capital"] + df["reserves"]
    df["total_debt"] = df["borrowings"]
    df["net_debt"] = df["borrowings"] - df.get("cash_and_equivalents", 0)  # cash not separately available -> net_debt ~= gross debt (documented)

    # ---- Liquidity (proxy-based, see module docstring) ----
    df["current_assets_proxy"] = df["other_assets"]
    df["current_liabilities_proxy"] = df["other_liabilities"]
    df["current_ratio_proxy"] = df["current_assets_proxy"] / df["current_liabilities_proxy"]

    df["receivables_est"] = df["debtor_days"] / 365 * df["sales"]
    df["inventory_est"] = df["inventory_days"] / 365 * df["sales"]
    df["quick_assets_proxy"] = df["current_assets_proxy"] - df["inventory_est"]
    df["quick_ratio_proxy"] = df["quick_assets_proxy"] / df["current_liabilities_proxy"]

    # ---- Leverage ----
    df["debt_to_equity"] = df["total_debt"] / df["total_equity"]
    df["debt_to_assets"] = df["total_debt"] / df["total_liabilities"]
    df["debt_to_ebitda"] = df["total_debt"] / df["ebitda"]
    df["net_debt_to_ebitda"] = df["net_debt"] / df["ebitda"]

    # ---- Debt servicing ----
    df["interest_coverage_ebit"] = df["ebit"] / df["interest"]
    df["interest_coverage_ebitda"] = df["ebitda"] / df["interest"]

    # ---- Profitability ----
    df["roa_pct"] = df["net_profit"] / df["total_liabilities"] * 100  # total_liabilities == total_assets
    df["roe_pct"] = df["net_profit"] / df["total_equity"] * 100
    df["ebit_margin_pct"] = df["ebit"] / df["sales"] * 100
    df["ebitda_margin_pct"] = df["ebitda"] / df["sales"] * 100

    # ---- Cash flow ----
    df["cfo_to_pat"] = df["cfo"] / df["net_profit"]
    df["cfo_to_debt"] = df["cfo"] / df["total_debt"]
    df["fcf_to_debt"] = df["fcf"] / df["total_debt"]

    # ---- Working capital ----
    df["payable_est"] = np.where(df["payable_days"].notna(), df["payable_days"] / 365 * df["sales"], np.nan)
    df["cash_conversion_cycle"] = np.where(
        df["payable_days"].notna(),
        df["debtor_days"].fillna(0) + df["inventory_days"].fillna(0) - df["payable_days"],
        np.nan,  # CCC only fully computable where payable_days disclosed (ONGC)
    )
    df["cash_conversion_cycle_partial"] = df["debtor_days"].fillna(np.nan) + df["inventory_days"].fillna(np.nan)  # DSO+DIO only, where CCC not available

    return df


def summarize_latest(ratios: pd.DataFrame, fy: int = 2025) -> pd.DataFrame:
    cols = [
        "company", "fy", "current_ratio_proxy", "quick_ratio_proxy",
        "debt_to_equity", "debt_to_assets", "debt_to_ebitda", "net_debt_to_ebitda",
        "interest_coverage_ebit", "interest_coverage_ebitda",
        "roa_pct", "roe_pct", "ebit_margin_pct", "ebitda_margin_pct",
        "cfo_to_pat", "cfo_to_debt", "fcf_to_debt",
        "debtor_days", "inventory_days", "payable_days", "cash_conversion_cycle",
    ]
    return ratios[ratios["fy"] == fy][cols].reset_index(drop=True)


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_cleaning import run_pipeline
    fin, mkt, rfr, universe = run_pipeline()
    ratios = compute_ratios(fin)
    out = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "financial_ratios.csv")
    ratios.to_csv(out, index=False)
    print(ratios[["company", "fy", "debt_to_ebitda", "interest_coverage_ebit", "current_ratio_proxy", "roe_pct"]].to_string())
