"""
altman_model.py
================
Accounting-based credit risk: Altman Z''-Score (Emerging Markets model).

WHICH ALTMAN FORMULATION, AND WHY (Section 14 requirement)
------------------------------------------------------------
Three Altman formulations exist:
  Z  (1968) - original, for PUBLICLY TRADED MANUFACTURERS. Uses X5 = Sales/
              Total Assets (asset turnover), which is a manufacturing-specific
              variable and penalises capital-intensive, low-turnover
              businesses (refiners, upstream E&P) that are not distressed,
              merely capital-heavy.
  Z' (1983) - adaptation for PRIVATE firms / non-manufacturers, uses BOOK
              value of equity in X4 (no market price needed).
  Z''(1995) - adaptation for EMERGING MARKET industrials/non-manufacturers.
              Drops X5 (Sales/TA) entirely and adds a constant (+3.25) so the
              score aligns to the same D-rated-bond = 0 anchor as the other
              variants. This is the Altman formulation Anthropic/academic
              literature generally recommends for large listed EM industrial
              and energy companies precisely because it does not penalise
              capital intensity via asset turnover.

DECISION: this project uses the Altman Z''-Score (Emerging Markets, Altman
1995) - a MODIFIED Altman model, explicitly labeled as such throughout. It is
NOT the original 1968 manufacturing Z-score and is never referred to as such.

    Z'' = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4

    X1 = Working Capital / Total Assets            (liquidity)
    X2 = Retained Earnings / Total Assets           (cumulative profitability)
    X3 = EBIT / Total Assets                        (operating profitability)
    X4 = Book Value of Equity / Total Liabilities   (leverage, book-based,
                                                       per Altman 1995 - kept
                                                       book-based to avoid
                                                       injecting day-to-day
                                                       market noise into an
                                                       ACCOUNTING-based score)

PROXIES USED (documented; see data_dictionary.md / limitations.md):
  - X1 numerator (Working Capital) = other_assets - other_liabilities (proxy
    for current assets - current liabilities; see financial_ratios.py).
  - X2 numerator (Retained Earnings) = reserves & surplus (Indian company
    accounts do not always separately break out "retained earnings" from
    total reserves in the summary view used; reserves is the standard proxy).
  - "Total Liabilities" in X4 means liabilities to OUTSIDE parties
    (Borrowings + Other Liabilities), i.e. Total Assets minus Total Equity -
    NOT the balance-sheet total (which equals Total Assets). This is a
    common point of confusion and is made explicit here.

INTERPRETATION ZONES (Altman 1995 Z''-EM, as commonly cited in credit
literature; this project adopts them as the stated convention - not claimed
to be a universal industry standard):
    Z'' > 5.85            -> "Safe Zone"    (low probability of distress)
    4.50 <= Z'' <= 5.85    -> "Grey Zone"    (some risk of distress)
    Z'' < 4.50             -> "Distress Zone" (higher risk of distress)

SUPPLEMENTARY (NOT part of the official score): since all seven companies are
publicly traded, we also report X4_market = Market Value of Equity / Total
Liabilities alongside the book-based X4, as requested by the project brief
(Section 15). This is shown for diagnostic purposes only, to see how far
book and market leverage views diverge - it does NOT feed into the reported
Z'' figure, to avoid presenting an ad hoc, non-standard hybrid score as if
it were "the Altman model."
"""

from __future__ import annotations
import pandas as pd
import numpy as np

Z_SAFE = 5.85
Z_DISTRESS = 4.50


def compute_altman(fin: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    df = fin.copy()

    total_assets = df["total_liabilities"]  # balance-sheet total (both sides)
    external_liabilities = df["borrowings"] + df["other_liabilities"]  # Altman's "Total Liabilities"
    working_capital = df["other_assets"] - df["other_liabilities"]
    retained_earnings_proxy = df["reserves"]
    ebit = df["operating_profit"] - df["depreciation"]
    book_equity = df["equity_capital"] + df["reserves"]

    df["x1_wc_ta"] = working_capital / total_assets
    df["x2_re_ta"] = retained_earnings_proxy / total_assets
    df["x3_ebit_ta"] = ebit / total_assets
    df["x4_bve_tl"] = book_equity / external_liabilities

    df["altman_z_em"] = 3.25 + 6.56 * df["x1_wc_ta"] + 3.26 * df["x2_re_ta"] + 6.72 * df["x3_ebit_ta"] + 1.05 * df["x4_bve_tl"]

    def zone(z):
        if pd.isna(z):
            return "N/A"
        if z > Z_SAFE:
            return "Safe Zone"
        if z >= Z_DISTRESS:
            return "Grey Zone"
        return "Distress Zone"

    df["altman_zone"] = df["altman_z_em"].apply(zone)

    # Supplementary market-based X4 (latest snapshot only, since it's the only
    # point-in-time market value we have - see docs/assumptions.md)
    mkt_latest = market[["company", "market_cap_cr"]].rename(columns={"market_cap_cr": "market_equity_cr"})
    df = df.merge(mkt_latest, on="company", how="left")
    df["x4_market_mve_tl"] = np.where(
        df["fy"] == df["fy"].max(),
        df["market_equity_cr"] / external_liabilities,
        np.nan,
    )
    df = df.drop(columns=["market_equity_cr"])

    return df


def five_year_trend(altman_df: pd.DataFrame) -> pd.DataFrame:
    piv = altman_df.pivot(index="company", columns="fy", values="altman_z_em")
    piv["change_fy21_fy25"] = piv[2025] - piv[2021]
    piv["slope_per_year"] = piv[[2021, 2022, 2023, 2024, 2025]].apply(
        lambda row: np.polyfit([2021, 2022, 2023, 2024, 2025], row.values, 1)[0], axis=1
    )

    def classify(slope):
        if slope > 0.15:
            return "Improving"
        if slope < -0.15:
            return "Deteriorating"
        return "Stable"

    piv["trend_classification"] = piv["slope_per_year"].apply(classify)
    return piv.reset_index()


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_cleaning import run_pipeline
    fin, mkt, rfr, universe = run_pipeline()
    altman = compute_altman(fin, mkt)
    out = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "altman_scores.csv")
    altman.to_csv(out, index=False)
    print(altman[["company", "fy", "altman_z_em", "altman_zone"]].to_string())
    print("\n5-year trend:")
    print(five_year_trend(altman)[["company", 2021, 2025, "change_fy21_fy25", "trend_classification"]].to_string())
