# Merton–Altman Energy Credit Risk Engine — Final Report

*Structural and Accounting-Based Credit Risk Assessment of Major Indian Oil & Gas Companies*

**Disclaimer**: educational/portfolio research project. Not investment advice, not a credit rating, not a substitute for professional credit analysis. See "Limitations" below and `docs/limitations.md` for the full treatment.

---

## Executive Summary

This project builds and runs a full corporate credit-risk research pipeline on seven major Indian energy companies — ONGC, Indian Oil Corporation (IOC), Bharat Petroleum (BPCL), Hindustan Petroleum (HPCL), GAIL, Oil India, and Reliance Industries (as a diversified benchmark) — combining a market-based structural model (Merton, 1974) and an accounting-based statistical model (Altman Z''-Score, Emerging Markets variant, 1995), supported by a full financial ratio engine, five-year trend analysis, energy-sector stress testing, a rule-based early-warning system, and a project-defined composite credit score.

Using real FY2021–FY2025 audited financial data and a 14-Aug-2026 market snapshot, all seven Merton solves converge cleanly (residuals < 1e-8) and all 28 behavioural sanity checks pass. **GAIL ranks strongest** on the composite Energy Credit Score (84.4/100) and is robustly ranked #1 under every alternative weighting scheme tested; **HPCL ranks weakest** (43.5/100) and is robustly ranked #7 under every scheme. The most consequential finding, however, is not the ranking itself but the **persistent disagreement between the two models for the three refiners (IOC, BPCL, HPCL) and for Reliance**: Merton (market-based) rates them meaningfully better than Altman (accounting-based), a gap traced directly to FY2023's thin-to-negative refining margins during the government fuel under-recovery period versus the market's more forward-looking, currently-benign pricing of these stocks. Sensitivity analysis shows equity volatility — not debt or equity-value levels — is the single largest driver of Merton DD across every company, a finding with direct implications for how much weight to place on the model's current-snapshot volatility input.

## Industry Context

Oil & gas companies combine capital intensity, meaningful leverage, large fixed-asset bases, working-capital swings, and direct commodity-price exposure — the sector is genuinely credit-risk-relevant, not just conveniently large. Upstream (ONGC, Oil India) is long crude/gas prices; downstream (IOC, BPCL, HPCL) is exposed to refining margins and inventory-driven working capital, not the absolute oil price; GAIL (gas transmission) is closer to a regulated utility, exposed mainly to throughput volumes; Reliance is a diversified conglomerate where oil & gas (O2C) is one segment among several. See `docs/methodology.md` §2 for the full discussion.

## Research Question

*How resilient are major Indian oil and gas companies to financial and market shocks, and what do structural and accounting-based credit models indicate about their credit risk?*

## Data

FY2021–FY2025 consolidated financial statements (Screener.in, aggregating audited BSE/NSE filings), a 14-Aug-2026 market snapshot (price, market cap, 1-year trailing volatility; Screener.in/Tickertape.in), and India 10-year G-Sec yields at each fiscal year-end (FRED series INDIRLTLT01STM, OECD-sourced). Full source log: `data/metadata/data_dictionary.md`. Documented data gaps (balance-sheet granularity, historical daily-return volatility) are listed in full in `docs/limitations.md` — none were fabricated or silently patched.

## Methodology

Full detail in `docs/methodology.md`. In brief: Altman Z''-Score (Emerging Markets, 1995 — explicitly modified, chosen to avoid penalising capital intensity) provides the accounting view; the Merton structural model (solved via `scipy.optimize.root`, convergence explicitly validated) provides the market view; a financial ratio engine (liquidity, leverage, debt-servicing, profitability, cash-flow, working-capital) supports both; the two models are compared via a tiered agreement/disagreement framework rather than blended into one score.

## Merton Model — Results

| Company | E (₹Cr) | σ_E | D (₹Cr, FY25) | V (₹Cr, solved) | σ_V (solved) | Merton DD | Model-implied risk-neutral PD |
|---|---|---|---|---|---|---|---|
| ONGC | 297,398 | 23.63% | 187,817 | 472,938 | 14.86% | 6.60 | ~0.0000% |
| IOC | 196,850 | 26.93% | 152,271 | 339,168 | 15.63% | 5.48 | ~0.0000% |
| BPCL | 138,594 | 29.58% | 61,101 | 195,701 | 20.95% | 5.77 | ~0.0000% |
| HPCL | 79,474 | 34.99% | 70,558 | 145,420 | 19.12% | 4.04 | 0.0027% |
| GAIL | 114,998 | 25.51% | 21,595 | 135,181 | 21.70% | 8.65 | ~0.0000% |
| OIL | 76,207 | 30.94% | 30,645 | 104,849 | 22.49% | 5.66 | ~0.0000% |
| RELIANCE | 1,772,762 | 20.82% | 374,313 | 2,122,608 | 17.39% | 10.28 | ~0.0000% |

All model-implied default probabilities here are **risk-neutral**, computed under the stated Merton assumptions — they are not real-world default forecasts and are not comparable to a credit rating (see `docs/assumptions.md` §8). All solves converged with residual error below 1e-8 relative to E; see `outputs/tables/` and Cell 16 of the notebook for the full numerical validation.

## Altman Z''-Score — Results (FY2025) and Five-Year Trend

| Company | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 | Trend |
|---|---|---|---|---|---|---|
| ONGC | 4.95 | 5.60 | 5.93 | 6.22 | 5.92 | **Improving** |
| IOC | 5.05 | 5.39 | 5.01 | 5.78 | 5.13 | Stable |
| BPCL | 5.52 | 4.78 | 4.48 | 6.19 | 5.61 | **Improving** |
| HPCL | 4.71 | 4.07 | 3.05 | 4.57 | 4.48 | Stable (weakest throughout; distress-zone touch in FY2023) |
| GAIL | 7.11 | 8.01 | 6.85 | 7.26 | 7.49 | Stable (consistently Safe Zone) |
| OIL | 5.85 | 6.56 | 7.17 | 6.63 | 5.99 | Stable |
| RELIANCE | 6.16 | 6.00 | 5.61 | 5.26 | 4.86 | **Deteriorating** |

HPCL's FY2023 operating **loss** (₹−7,192 Cr EBITDA) during the Russia-Ukraine crude-price spike / fuel under-recovery period is the single sharpest data point in the dataset and drives its Distress Zone touch that year. Reliance's steady Altman decline (6.16 → 4.86) despite its dominant Merton DD is a genuine, real finding — see "Reliance Comparability" below.

## Financial Ratio Analysis (FY2025 snapshot)

| Company | Debt/EBITDA | Interest Coverage (EBIT/Int) | Current Ratio (proxy) | FCF/Debt |
|---|---|---|---|---|
| ONGC | 2.11x | 3.69x | 0.92x | 26.7% |
| IOC | 4.23x | 2.07x | 0.96x | 0.05% |
| BPCL | 2.41x | 5.05x | 1.01x | 14.0% |
| HPCL | 4.29x | 3.06x | 0.87x | 6.8% |
| GAIL | 1.40x | 15.69x | 0.91x | 36.2% |
| OIL | 2.75x | 8.27x | 0.82x | −5.3% |
| RELIANCE | 2.26x | 4.63x | 0.61x | 11.0% |

IOC's near-zero FCF/Debt and elevated Debt/EBITDA in FY2025 are the primary drivers of its Red early-warning flag (see below) — a real, data-driven result of a thin-margin year, not an artifact of the model.

## Peer Comparison and Model Disagreement

| Company | Merton DD | Altman Z'' | Merton Tier | Altman Tier | Signal |
|---|---|---|---|---|---|
| GAIL | 8.65 | 7.49 | Low Risk | Low Risk | **Agreement** |
| ONGC | 6.60 | 5.92 | Low Risk | Low Risk | **Agreement** |
| OIL | 5.66 | 5.99 | Low Risk | Low Risk | **Agreement** |
| RELIANCE | 10.28 | 4.86 | Low Risk | Moderate Risk | **Disagreement** |
| BPCL | 5.77 | 5.61 | Low Risk | Moderate Risk | **Disagreement** |
| IOC | 5.48 | 5.13 | Low Risk | Moderate Risk | **Disagreement** |
| HPCL | 4.04 | 4.48 | Moderate Risk | Elevated Risk | **Disagreement** |

**What each model is capturing where they disagree**: for the refiners and Reliance, Merton's inputs (current, relatively low equity volatility; large, currently-priced market capitalisation) reflect the market's *current, forward-looking* view — investors are pricing in a return to normalised refining margins. Altman's inputs are trailing accounting figures still weighed down by FY2023's under-recovery-driven margin collapse. Neither model is "wrong" — they are measuring different things over different time windows. This is the single most important interpretive insight of the project (see `docs/methodology.md` §7): **the disagreement is information, not noise.**

## Peer Ranking and Custom Credit Score

The project-defined Energy Corporate Credit Score (Structural 30% / Accounting 30% / Debt Servicing 20% / Liquidity 10% / Cash Flow 10%) produces:

| Rank | Company | Score /100 |
|---|---|---|
| 1 | GAIL | 84.4 |
| 2 | RELIANCE* | 65.6 |
| 3 | ONGC | 62.7 |
| 4 | BPCL | 58.3 |
| 5 | OIL | 57.3 |
| 6 | IOC | 49.0 |
| 7 | HPCL | 43.5 |

*Reliance's rank reflects its diversified-benchmark caveat; see below.

Weight-sensitivity testing (equal-weight, market-heavy, accounting-heavy schemes) confirms **GAIL's #1 rank and HPCL's #7 rank are robust to reweighting** — every scheme tested agrees on both endpoints. Reliance's rank is the least stable (#2 under default/market-heavy weighting, #3 under equal weighting, #5 under accounting-heavy weighting), which is itself informative: its ranking is largely a function of how much weight one places on market-based versus accounting-based signals.

## Stress Testing

**Isolated shocks** (profitability, debt, equity, each in isolation) are well-absorbed by all seven companies individually — see `outputs/tables/` and Cells 24-26 of the notebook.

**Combined Bear Case** (EBITDA −25%, Debt +25%, Equity −30%, Equity volatility +50%, simultaneously):

| Company | DD (base) | DD (bear) | Δ DD | Debt/EBITDA (bear) | Interest Coverage (bear) |
|---|---|---|---|---|---|
| ONGC | 6.60 | 3.78 | −2.82 | 3.52x | 2.16x |
| IOC | 5.48 | 3.16 | −2.31 | 7.04x | 1.10x |
| BPCL | 5.77 | 3.23 | −2.55 | 4.01x | 3.28x |
| HPCL | 4.04 | 2.32 | −1.72 | 7.15x | 1.84x |
| GAIL | 8.65 | 4.77 | −3.88 | 2.34x | 10.49x |
| OIL | 5.66 | 3.14 | −2.51 | 4.58x | 5.66x |
| RELIANCE | 10.28 | 5.71 | −4.57 | 3.77x | 2.93x |

Under this correlated bear case, HPCL is pushed into Elevated Risk territory (DD 2.32) and IOC/BPCL/OIL move to the edge of Moderate Risk. **Reverse stress testing** confirms this: individually, six of seven companies do NOT cross into Elevated Risk (DD < 3.0) even under a 95% equity-value collapse or a +300% debt increase tested in isolation — only HPCL does (at roughly a 90% equity decline held in isolation). This tells a coherent story: **single-factor shocks are well-absorbed by this peer group's current balance sheets and market pricing; it is correlated, multi-factor stress (a genuine crisis, where profitability, leverage and market pricing all deteriorate together) that meaningfully threatens credit quality** — exactly the dynamic a combined bear case is designed to surface and isolated scenarios are not.

## Sensitivity Analysis

Across every company tested, **equity volatility** produces the largest swing in Merton DD of the three ±10/25/50% shock drivers tested (larger than equivalent-magnitude Debt or Equity Value shocks) — see `outputs/charts/12_sensitivity_heatmap.png`. This is a structural property of the model (DD's denominator scales with σ_V√T) and is the primary reason this project treats the current-snapshot-volatility limitation (see Data/Limitations) as consequential rather than cosmetic.

## Early Warning System

| Company | Level | Triggered metrics |
|---|---|---|
| IOC | 🔴 Red (4 triggers) | Debt/EBITDA > 3.5x, Interest Coverage < 3.0x, FCF/Debt < 5%, Current Ratio (proxy) < 1.0x |
| HPCL | 🟠 Orange (3) | Debt/EBITDA > 3.5x, Current Ratio (proxy) < 1.0x, Altman Z'' < 4.50 |
| OIL | 🟠 Orange (2) | FCF/Debt < 5% (negative, capex year), Current Ratio (proxy) < 1.0x |
| ONGC, GAIL, RELIANCE | 🟡 Yellow (1) | Current Ratio (proxy) < 1.0x only |
| BPCL | 🟢 Green (0) | — |

Note the Yellow flags for ONGC/GAIL/Reliance are driven entirely by the Current Ratio proxy — a known data-granularity limitation (see `docs/limitations.md` §2) — not by leverage, coverage, or market-based deterioration. This is exactly the kind of nuance the "exact metric" design of the early-warning system is meant to surface.

## Reliance Comparability

Reliance's Merton DD (10.28) is the highest in the peer set — driven by its very large market capitalisation relative to debt and the lowest observed equity volatility (20.8%) in the group — while its Altman Z'' (4.86, Grey Zone) is on a clear deteriorating trend (6.16 → 4.86 over FY2021–FY2025), driven by declining ROE/ROCE and a rapidly growing non-debt liability base (retail/telecom build-out). This divergence is a direct illustration of why Reliance is analysed as a diversified benchmark, not folded into the "Pure Energy" peer ranking without qualification: its market profile reflects conglomerate scale and diversification benefits that are not primarily oil & gas credit fundamentals.

## IOC Deep Dive

See `docs/methodology.md` and Cell 35 of the notebook for the full case study. IOC is used as the primary single-company deep dive (disclosed personal connection: the project author previously worked in business development/ESG at IOCL). **The model was not tuned toward any particular conclusion about IOC** — it is the same pipeline, applied identically, that produced GAIL's #1 rank and HPCL's #7 rank. IOC's own result — rank 6 of 7 (Energy Credit Score 49.0), Red early-warning level, and a "Disagreement" model signal (Merton: Low Risk / Altman: Moderate Risk) — is a direct, unbiased output driven by a specific real fact: FY2025 was a thin-margin year for IOC (EBITDA down sharply from FY2024, Debt/EBITDA up to 4.23x, FCF/Debt near zero), even though its five-year Altman trend is merely "Stable" rather than clearly deteriorating, and its market-based Merton DD (5.48) remains comfortably in the Low Risk tier.

## Limitations

Full treatment in `docs/limitations.md`. Headline items: (1) historical (FY2021–FY2024) daily-return equity volatility and historical market capitalisation could not be retrieved via available tools in this environment, so the FY2021–FY2024 Merton trend is an explicitly-labeled "leverage-only" decomposition, not a claim about historical market pricing; (2) balance-sheet granularity limits Current Ratio/Working Capital to a documented proxy; (3) government ownership (6 of 7 companies) implies potential implicit sovereign support that neither model explicitly captures; (4) no supervised ML default classifier is included, because the sample (35 company-years, 0 observed defaults) cannot support one without manufacturing a spurious result — see `docs/methodology.md` §11.

## Conclusion

Across both a market-based structural model and an accounting-based statistical model, GAIL is the most robustly strong credit profile in this peer group and HPCL the most robustly weak, a conclusion that holds under every scoring-weight scheme tested. The more analytically interesting finding, however, is where the two models disagree — the refiners and Reliance — because it isolates exactly the gap between what current market pricing is willing to look past (a bad FY2023) and what trailing accounting metrics are still recovering from. Combined, correlated stress (not isolated single-factor shocks) is what actually threatens credit quality across this peer group, and equity volatility — not debt or market-cap levels — is the single input this project's results are most sensitive to.

---

## Final Project Audit

**1. What was implemented**: the full pipeline specified in the project brief — data collection/cleaning/validation, financial ratio engine, Altman Z''-Score, Merton structural model with numerically validated solver, model comparison with tiered agreement/disagreement classification, peer ranking, project-defined custom credit score with weight-sensitivity testing, five-year trend analysis, rule-based early-warning system, full stress-testing suite (profitability/debt/equity/business-model-differentiated/combined bear case/reverse stress test), sensitivity analysis, 20 charts, a Streamlit+Plotly dashboard, a 50-cell executed Jupyter notebook, an IOC deep dive, a Reliance comparability discussion, and this final report.

**2. What data was actually used**: real, sourced FY2021–FY2025 consolidated financial statements for all 7 companies (Screener.in), a real 14-Aug-2026 market snapshot (Screener.in/Tickertape.in), and real India 10-year G-Sec yields at each fiscal year-end (FRED/OECD). Nothing was fabricated; every gap encountered is documented in `docs/limitations.md` rather than silently filled.

**3. What assumptions were made**: documented exhaustively in `docs/assumptions.md` — debt definition (total borrowings), risk-free rate source, T=1 year horizon, the current-snapshot-vs-historical-leverage-only Merton timing split, the ERP-based "physical PD" supplement, the Altman Z'' formulation choice, balance-sheet proxies, early-warning thresholds, credit-score weights, and stress-severity multipliers.

**4. What calculations were validated**: all 7 Merton solves converge with residuals below 1e-8 relative to equity value; all 28 behavioural sanity checks (debt↑⇒DD↓, equity↓⇒DD↓, volatility↑⇒DD↓, EBIT↑⇒Altman Z↑) pass; balance-sheet identities were checked for all 35 company-year observations (one immaterial ₹2 Cr rounding difference in BPCL FY2025, out of a ₹218,382 Cr balance sheet, logged not silently corrected).

**5. What results were generated**: a full model-comparison table, peer rankings under 4 weighting schemes, a 5-year Altman trend and a leverage-only Merton trend, an early-warning table, a combined bear case and reverse stress test, a sensitivity ranking of input drivers, 20 charts, and an interactive dashboard — all listed above.

**6. What model limitations remain**: historical market-data granularity (see Limitations §1), balance-sheet granularity (§2), the risk-neutral-vs-physical PD distinction (never resolved to a single "true" PD, by design), no explicit sovereign-support adjustment, and no back-tested/validated custom credit score (no historical default events exist in this sample to back-test against).

**7. What the project creator must personally understand before this goes on a resume**: (a) the exact difference between risk-neutral and physical default probability, and why quoting a Merton PD as "the probability of default" would be a factual error; (b) why the Altman Z'' formulation was chosen over the original 1968 Z-Score specifically for this sector; (c) the Current Ratio/Working Capital proxy limitation and its effect on 3 of the 7 companies' Yellow early-warning flags; (d) why GAIL ranks #1 and HPCL ranks #7 in terms of the underlying economics (leverage, margin volatility, interest coverage) — not just the number; (e) that the custom Energy Credit Score is a personal, documented methodology, not an industry standard, and should be described as such in any interview.

**8. What should be improved before publishing to GitHub**: replace the placeholder repository URL in the README clone instructions; consider adding a `LICENSE` file; if continuing this project, prioritise sourcing a licensed market-data feed for true historical daily-return volatility (this project's single largest data limitation) and a fully classified balance sheet to remove the Current Ratio proxy; add unit tests (`pytest`) around `merton_model.py` and `altman_model.py` beyond the current behavioural sanity-check script, formalised as an automated CI-style regression suite.
