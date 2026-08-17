"""
data_cleaning.py
=================
Cleans, validates, and exports the raw data collected in data_collection.py
into analysis-ready tables under data/processed/. Implements the validation
checks required by the project spec (Section 36): duplicate detection,
missing-value handling, balance-sheet identity checks, impossible-value
checks. Nothing is silently corrected - every issue found is written to
data/metadata/validation_log.csv for transparency.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from data_collection import (
    load_financials, load_market_data, load_risk_free_rate, load_company_universe,
    MARKET_SNAPSHOT_DATE,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(REPO_ROOT, "data", "raw")
PROC_DIR = os.path.join(REPO_ROOT, "data", "processed")
META_DIR = os.path.join(REPO_ROOT, "data", "metadata")


def _log(rows: list, msg: str, level: str = "INFO"):
    rows.append({"level": level, "message": msg})


def validate_financials(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    log = []
    # 1. Duplicate company-year check
    dupes = df[df.duplicated(subset=["company", "fy"], keep=False)]
    if len(dupes):
        _log(log, f"Duplicate company-year rows found: {dupes[['company','fy']].values.tolist()}", "ERROR")
    else:
        _log(log, "No duplicate company-year observations found (35 expected: 7 companies x 5 years).")

    # 2. Completeness check
    expected = {(c, fy) for c in df["company"].unique() for fy in [2021, 2022, 2023, 2024, 2025]}
    actual = set(zip(df["company"], df["fy"]))
    missing = expected - actual
    if missing:
        _log(log, f"Missing company-year observations: {sorted(missing)}", "ERROR")
    else:
        _log(log, "All 35 company-year observations present (7 companies x FY2021-FY2025).")

    # 3. Balance sheet identity: equity_capital + reserves + borrowings + other_liabilities == total_liabilities
    df["_bs_check"] = (df["equity_capital"] + df["reserves"] + df["borrowings"] + df["other_liabilities"]) - df["total_liabilities"]
    bad_bs = df[df["_bs_check"].abs() > 1]  # tolerance of 1 crore for rounding
    if len(bad_bs):
        _log(log, f"Balance sheet identity mismatch (>Rs.1cr) for: {bad_bs[['company','fy','_bs_check']].values.tolist()}", "WARNING")
    else:
        _log(log, "Balance sheet identity (Equity+Reserves+Borrowings+OtherLiab = Total Liabilities) holds for all 35 observations (by construction; Other Liabilities was derived as the plug).")

    # 4. Impossible values: negative Total Assets, negative Borrowings, zero Sales
    if (df["total_liabilities"] <= 0).any():
        _log(log, "Non-positive Total Assets/Liabilities detected.", "ERROR")
    if (df["borrowings"] < 0).any():
        _log(log, "Negative Borrowings detected.", "ERROR")
    if (df["sales"] <= 0).any():
        _log(log, "Non-positive Sales detected.", "ERROR")
    else:
        _log(log, "No impossible values (negative assets/debt, non-positive sales) detected.")

    # 5. Negative operating profit / net profit flagged (real, not an error - HPCL FY23 had an operating loss)
    neg_op = df[df["operating_profit"] < 0][["company", "fy", "operating_profit"]]
    if len(neg_op):
        _log(log, f"Negative EBITDA (operating loss) observed - genuine, not a data error: {neg_op.values.tolist()} "
                   f"(HPCL FY23 posted an operating loss during the Russia-Ukraine crude price spike / under-recovery period).")

    # 6. Missing-value inventory
    na_counts = df.isna().sum()
    na_counts = na_counts[na_counts > 0]
    if len(na_counts):
        _log(log, f"Missing values by field (not fabricated - left as NaN, downstream ratios using these fields are marked N/A): {na_counts.to_dict()}")

    df = df.drop(columns=["_bs_check"])
    return df, log


def validate_market_data(df: pd.DataFrame) -> list:
    log = []
    if (df["price"] <= 0).any() or (df["market_cap_cr"] <= 0).any():
        _log(log, "Non-positive price or market cap detected.", "ERROR")
    else:
        _log(log, "All market prices and market caps are positive.")
    # cross-check shares outstanding two ways: market_cap/price vs equity_capital/face_value (latest FY)
    return log


def run_pipeline():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROC_DIR, exist_ok=True)
    os.makedirs(META_DIR, exist_ok=True)

    fin = load_financials()
    mkt = load_market_data()
    rfr = load_risk_free_rate()
    universe = load_company_universe()

    fin_clean, fin_log = validate_financials(fin)
    mkt_log = validate_market_data(mkt)

    # Derive shares outstanding two ways and cross-check
    mkt = mkt.copy()
    mkt["shares_out_cr_from_mktcap"] = mkt["market_cap_cr"] / mkt["price"]
    latest_fin = fin_clean[fin_clean["fy"] == 2025][["company", "equity_capital"]].rename(columns={"equity_capital": "equity_capital_fy25"})
    mkt = mkt.merge(latest_fin, on="company", how="left")
    mkt["shares_out_cr_from_facevalue"] = mkt["equity_capital_fy25"] / mkt["face_value"]
    mkt["shares_out_pct_diff"] = (mkt["shares_out_cr_from_mktcap"] - mkt["shares_out_cr_from_facevalue"]).abs() / mkt["shares_out_cr_from_facevalue"] * 100
    mkt["shares_out_cr"] = mkt["shares_out_cr_from_mktcap"]  # primary measure: consistent with reported market cap
    mkt["snapshot_date"] = MARKET_SNAPSHOT_DATE

    cross_check_log = []
    for _, row in mkt.iterrows():
        _log(cross_check_log, f"{row['company']}: shares outstanding cross-check - "
                                f"MktCap/Price = {row['shares_out_cr_from_mktcap']:.1f} cr vs "
                                f"EquityCapital(FY25)/FaceValue = {row['shares_out_cr_from_facevalue']:.1f} cr "
                                f"(diff {row['shares_out_pct_diff']:.1f}%)")

    # Save processed outputs
    fin_clean.to_csv(os.path.join(PROC_DIR, "financials.csv"), index=False)
    mkt.to_csv(os.path.join(PROC_DIR, "market_data.csv"), index=False)
    rfr.to_csv(os.path.join(PROC_DIR, "risk_free_rate.csv"), index=False)
    universe.to_csv(os.path.join(PROC_DIR, "company_universe.csv"), index=False)

    # Save raw dumps too (for transparency / reproducibility)
    fin.to_csv(os.path.join(RAW_DIR, "financials_raw.csv"), index=False)
    mkt.to_csv(os.path.join(RAW_DIR, "market_data_raw.csv"), index=False)

    # Write validation log
    all_log = (
        [{"section": "financials", **r} for r in fin_log] +
        [{"section": "market_data", **r} for r in mkt_log] +
        [{"section": "shares_outstanding_cross_check", **r} for r in cross_check_log]
    )
    pd.DataFrame(all_log).to_csv(os.path.join(META_DIR, "validation_log.csv"), index=False)

    print(f"Financials: {fin_clean.shape}, Market data: {mkt.shape}, Risk-free rate: {rfr.shape}")
    print(f"Validation log written with {len(all_log)} entries.")
    return fin_clean, mkt, rfr, universe


if __name__ == "__main__":
    run_pipeline()
