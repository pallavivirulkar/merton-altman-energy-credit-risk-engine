# Assumptions

Every assumption in this project is documented here or in the referenced module docstring. Nothing is a hidden default.

## 1. Company universe & peer groups
Two peer groups are used throughout: **Pure/Predominantly Energy** (ONGC, IOC, BPCL, HPCL, GAIL, Oil India) and **Diversified Benchmark** (Reliance Industries). Reliance is shown alongside the peer group in every comparison but its rankings and scores are always accompanied by the comparability caveat (see `docs/limitations.md` and Cell 34 of the notebook).

## 2. Analysis period and date conventions
- Fiscal year = Indian financial year, 1 April–31 March. "FY2025" = year ended 31 March 2025.
- Financial-statement data: FY2021–FY2025, consolidated statements, sourced 16-Aug-2026.
- Market data (price, market cap, volatility): single snapshot as of 14-Aug-2026 (retrieved 16-Aug-2026).
- Risk-free rate: fiscal year-end (31 March) values for FY2021–FY2025, plus a live 14-Aug-2026 value for the primary current-snapshot Merton run.
- **These dates are deliberately not the same** (audited FY2025 balance sheet vs. Aug-2026 market snapshot). This is standard practice (a company's most recent audited balance sheet is always somewhat older than "today"), and is documented here so the mismatch is never a surprise. See "Merton data timing" below.

## 3. Debt definition (Merton default point, D)
D = **Total Borrowings** (short-term + long-term combined), as reported on the consolidated balance sheet. The accessible data source does not split borrowings by maturity, so a KMV-style "short-term debt + 0.5 × long-term debt" default point could not be constructed; this is disclosed as a simplification. Total Borrowings was chosen over Total Liabilities because trade payables, provisions and other operating liabilities are not credit obligations in the same sense as financial debt, and including them would substantially overstate the default threshold (Section 10 of the project brief explicitly warns against this).

## 4. Risk-free rate
India 10-year government bond yield (FRED series `INDIRLTLT01STM`, OECD-sourced), monthly, evaluated at each fiscal year-end (March) for the historical series, and a live 14-Aug-2026 quote (TradingEconomics, cross-checked against the FRED series level) for the current-snapshot Merton run.

## 5. Time horizon
T = 1 year for the primary analysis (standard Merton-KMV convention for corporate credit risk). Sensitivity to T = 2 and T = 3 years is tested explicitly (see `src/sensitivity_analysis.py`, Cell 30).

## 6. Merton data timing (important - read before interpreting results)
**Primary ("current") Merton run:**
- E, σ_E → 14-Aug-2026 snapshot (market cap, 1-year trailing volatility)
- D → FY2025 (31-Mar-2025) audited Total Borrowings — the most recent audited figure available
- r → 14-Aug-2026 risk-free rate
- T → 1 year

This mixes a live market snapshot with the latest audited balance sheet — exactly what a credit analyst does in practice (the balance sheet is always somewhat stale relative to the market), and is the fully-rigorous, non-fabricated, primary cross-sectional analysis used for peer ranking, the credit score, and stress testing.

**Historical FY2021–FY2024 "leverage-only" Merton decomposition:**
- E, σ_E → HELD CONSTANT at the 14-Aug-2026 snapshot values
- D → that year's REAL, audited Total Borrowings (varies year to year)
- r → that year's REAL fiscal year-end risk-free rate (varies year to year)
- T → 1 year

This is explicitly labeled "leverage-only" everywhere it appears. It answers "if today's market pricing of the company had applied, how would the company's changing debt load alone have moved its Distance-to-Default over FY2021–FY2025?" It is **not** a claim about what the company's actual market value or volatility were in, say, March 2022. See `docs/limitations.md` for why full historical market data could not be retrieved, and why this decomposition is the honest alternative to fabricating historical price/volatility series.

## 7. Volatility & historical market data methodology
1-year trailing equity volatility (as of 14-Aug-2026) was retrieved from a market-data vendor (Tickertape) for each company. This is used as the primary volatility input. Full 5-year daily-return series (which would allow a textbook independent annualised volatility for each fiscal year) could not be retrieved through the tools available in this session — see `docs/limitations.md`, "Historical market data" for exactly what was attempted. The sensitivity analysis (±10/25/50% shocks to σ_E) is partly designed to compensate for this: it shows how much Merton DD would move if the true historical volatility had actually differed from today's level by a material amount, which turns out to be the single largest driver of DD movement of all the inputs tested (see Cell 30 / `outputs/charts/12_sensitivity_heatmap.png`).

## 8. Physical vs. risk-neutral default probability
The headline Merton output is the **risk-neutral** distance-to-default and default probability (uses r as the assumed asset drift — the correct drift under the option-pricing / Black-Scholes measure used to derive the model). As a clearly-labeled supplementary exercise, a "physical" DD/PD is also computed using μ = r + ERP, where ERP (India total equity risk premium) ≈ 7.0% is a documented, sourced estimate (Damodaran-style methodology, ~Jan-2026 vintage, via incwert.com assessment citing sovereign default-spread and historical-premium approaches). This does **not** estimate a firm-specific beta on assets and is explicitly a simplification, not a rigorous physical-measure estimate.

## 9. Altman Z''-Score formulation
The Altman **Z''-Score (Emerging Markets, Altman 1995)** is used — chosen because it does not penalise capital intensity via an asset-turnover term (unlike the original 1968 manufacturing Z-score) and is designed for EM industrials. X4 (leverage term) uses **book value of equity**, per the original Z'' specification, to keep the score a purely accounting-based measure (deliberately separate from the market-based Merton model — see project brief Section 7). A supplementary market-based X4 (Market Value of Equity / Total Liabilities) is shown for diagnostic purposes only, using the current market snapshot, and does not feed into the reported Z'' figure. Interpretation zones (Safe > 5.85, Grey 4.50–5.85, Distress < 4.50) are this project's adopted convention based on commonly cited Z''-EM literature, not a universal industry standard.

## 10. Balance-sheet proxies for working capital
"Other Assets" and "Other Liabilities" (the residual, non-fixed/non-investment/non-borrowing buckets on the balance sheet) are used as proxies for Current Assets and Current Liabilities respectively, since a fully classified (current/non-current) balance sheet was not retrievable. Documented fully in `docs/limitations.md` and `src/financial_ratios.py`.

## 11. Early Warning System thresholds
Project-defined, documented in `src/early_warning.py`: Debt/EBITDA > 3.5x, Interest Coverage < 3.0x, FCF/Debt < 5%, Current Ratio (proxy) < 1.0x, Merton DD < 3.0, Merton risk-neutral PD > 1.0%, Altman Z'' < 4.50 (Distress Zone), equity volatility > 35%. These are reasonable, disclosed conventions calibrated to the observed range of this project's own data - not regulatory or rating-agency thresholds.

## 12. Custom Energy Corporate Credit Score
Explicitly project-defined (Section 21), weights: Structural/Merton 30%, Accounting/Altman 30%, Debt Servicing 20%, Liquidity 10%, Cash Flow Quality 10%. Sensitivity to these weights is tested against three alternative schemes in `src/credit_score.py::sensitivity_to_weights()`.

## 13. Business-model stress severity multipliers
Section 24 asks for differentiated stress assumptions by business model. This project applies documented multipliers to a common percentage shock (Upstream ×1.30, Refining/Marketing ×1.10, Gas Transmission ×0.60, Diversified ×0.50) reflecting each model's typical operating leverage to an energy-price shock. These are project-defined assumptions for illustrative differentiation, not empirically estimated elasticities.
