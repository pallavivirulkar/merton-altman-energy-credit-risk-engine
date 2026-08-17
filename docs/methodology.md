# Methodology

## 1. Overview

This project combines two independent, philosophically different credit-risk models — a market-based structural model (Merton) and an accounting-based statistical model (Altman Z''-Score) — plus a supporting financial ratio engine, and keeps all three visibly separate rather than blending them into one opaque score (project brief Section 7).

```
Financial Statements + Market Data
        |
Data Cleaning & Validation
        |
Financial Ratio Engine  ---------------------\
        |                                     |
Altman Z''-Score (accounting)      Merton Structural Model (market)
        |                                     |
        \--------------  Model Comparison  ---/
                          |
                Peer Benchmarking + Custom Credit Score
                          |
              Energy-Sector Stress Testing + Reverse Stress Test
                          |
                  Early Warning System
                          |
                Dashboard + Final Credit Assessment
```

## 2. Why oil & gas for credit-risk modelling

Oil & gas companies are unusually well suited to structural + accounting credit modelling because:
- **Capital intensity and leverage**: refineries, pipelines and upstream production assets require enormous, long-lived capital investment, typically financed with a meaningful proportion of debt — leverage is a first-order driver of these companies' risk profile, not a footnote.
- **Commodity-price exposure**: revenue and margins are directly linked to crude oil and natural gas prices, which are volatile and largely outside management's control - a textbook source of cash-flow volatility that credit models are built to capture.
- **Upstream/downstream asymmetry**: upstream (E&P) companies are long commodity prices; downstream (refining/marketing) companies are exposed to *margins* (crack spreads) rather than the absolute price level, and carry large working-capital swings tied to inventory valuation - the same "oil price shock" hits different business models differently, which is exactly why this project splits the peer group by business model rather than treating "oil & gas" as one undifferentiated bucket.
- **Government ownership**: six of seven companies studied here are majority Government-of-India-owned, which affects both their observed cost of capital and (arguably) their true default risk in ways a pure market-based model may not fully price - see `docs/limitations.md`.
- **Refining margins and under-recoveries**: Indian downstream companies (IOC, BPCL, HPCL) have historically absorbed government fuel-pricing policy via "under-recoveries" during price spikes, which shows up directly in this project's own FY2023 data (see the HPCL operating-loss year, and the disagreement between Merton and Altman across the refiners discussed below) - a live, real illustration of why the sector is credit-risk-relevant, not a hypothetical one.

## 3. Merton model — intuition and implementation

See the full derivation and code in `src/merton_model.py`. In short: equity is modeled as a call option on firm assets struck at the face value of debt; solving the two option-pricing relationships simultaneously (via `scipy.optimize.root`, method `hybr` with an `lm` fallback, convergence explicitly checked) for the unobservable asset value V and asset volatility σ_V yields a Distance-to-Default and a risk-neutral model-implied default probability. The risk-neutral vs. physical distinction is treated as a first-class methodological point, not a footnote — see `docs/assumptions.md` Section 8.

## 4. Altman Z''-Score — why this formulation

See `src/altman_model.py` docstring for the full justification. In short: the original 1968 Z-Score's asset-turnover term (Sales/Total Assets) penalises capital-intensive, low-turnover businesses like refiners and upstream E&P companies for being capital-intensive, not for being distressed. The 1995 Z''-Score (Emerging Markets variant) drops this term and is the formulation this project uses, explicitly labeled as "modified" throughout.

## 5. Financial ratio engine

Liquidity, leverage, debt-servicing, profitability, cash-flow and working-capital ratios computed in `src/financial_ratios.py` for all 35 company-year observations. Where the underlying balance-sheet granularity limits precision (current/non-current split), this is disclosed via a "(proxy)" label rather than silently presented as exact.

## 6. Five-year trend analysis

For every company, Altman Z'' and the financial ratios are computed for all 5 fiscal years; the trend is classified Improving/Stable/Deteriorating using a linear slope fit across FY2021–FY2025 (threshold ±0.15 Z-points/year — see `src/altman_model.py::five_year_trend`). The Merton DD trend is computed as the documented "leverage-only" decomposition (see `docs/assumptions.md` Section 6) given the historical market-data limitation.

## 7. Model comparison and the disagreement analysis

The central comparison table tiers both models (Merton: Low/Moderate/Elevated Risk by DD; Altman: Safe/Grey/Distress Zone) and flags "Agreement" vs. "Disagreement" by comparing tiers, not raw scores. **The objective of the disagreement analysis is explicitly NOT to decide which model is "right"** — it is to understand what different information each model captures. In this dataset, the refiners (IOC, BPCL, HPCL) and Reliance show the most persistent disagreement: Merton (market-based, forward-looking, driven by low observed equity volatility and large market capitalisation) tends to rate them better than Altman (accounting-based, driven by FY2023's thin/negative refining margins during the under-recovery period). This is a genuine, data-driven finding, not a modeling artifact - see `outputs/reports/final_report.md`, "Model Disagreement Analysis" for the full discussion.

## 8. Stress testing

Three isolated single-factor scenarios (profitability, debt, equity value shocks, per Section 22) plus a combined bear case (Section 25, correlated shock to all four factors simultaneously) plus a reverse stress test (Section 26, solved via bisection over a plausible scenario range) plus a simplified oil/energy-price scenario framework and business-model-differentiated severity multipliers (Section 24). All propagate through to Interest Coverage, Debt/EBITDA, FCF/Debt, Merton DD/PD and the custom credit score. See `src/stress_testing.py`.

## 9. Early warning system

Rule-based, 8-indicator, 4-level (Green/Yellow/Orange/Red) system that names the exact metric(s) triggering each warning — see `src/early_warning.py`.

## 10. Model validation

Two layers: (1) numerical validation of every Merton solve (convergence, residual magnitude, positivity, finiteness — all 7 companies pass, see `outputs/tables/`); (2) behavioural sanity checks (debt up ⇒ DD down; equity down ⇒ DD down; volatility up ⇒ DD down; EBIT up ⇒ Altman Z up) — all 28 checks pass in this dataset. See `src/validation.py`.

## 11. Why no ML default classifier

Section 34 of the project brief explicitly permits omitting ML, and requires — if omitted — an explicit statistical justification. This project's population (7 companies, 5 years, 0 observed defaults) has no positive class to learn from. A logistic regression (or any classifier) fit to 35 observations with zero events would not be estimating a default probability; it would be reporting noise dressed up as a coefficient. This is explained in full in `docs/limitations.md`, Section 8, and is treated as a demonstration of judgment (knowing when *not* to apply a technique) rather than a missing feature.
