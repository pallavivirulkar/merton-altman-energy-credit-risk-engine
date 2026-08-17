# Merton–Altman Energy Credit Risk Engine

### Structural and Accounting-Based Credit Risk Assessment of Major Indian Oil & Gas Companies
*A Quantitative Framework for Credit Risk, Default Distance and Energy-Sector Stress Testing*

> **Disclaimer**: This is a research/educational project, not investment advice or a credit rating. See [`docs/limitations.md`](docs/limitations.md) before citing any figure from this repository.

---

## Problem Statement & Research Question

**How resilient are major Indian oil and gas companies to financial and market shocks, and what do structural and accounting-based credit models indicate about their credit risk?**

Four sub-questions are answered throughout the project:
1. Which companies appear financially strongest from an accounting perspective? (Altman Z''-Score)
2. Which companies have the greatest market-implied distance from default? (Merton Distance-to-Default)
3. Do the Merton and Altman models agree — and where they don't, why not?
4. How does credit risk change under severe energy-sector stress?

## Why Oil & Gas?

Oil & gas companies combine capital intensity, meaningful leverage, large fixed-asset bases, working-capital swings and direct commodity-price exposure — a sector where credit risk is genuinely financially meaningful, not academic. See [`docs/methodology.md`](docs/methodology.md) §2 for the full discussion, including why upstream, downstream and gas-transmission business models are treated separately rather than as one undifferentiated "oil & gas" bucket.

## Companies & Business-Model Classification

| Company | Symbol | Business Model | Peer Group |
|---|---|---|---|
| Oil and Natural Gas Corporation Ltd. | ONGC | Upstream (E&P) | Pure Energy |
| Indian Oil Corporation Ltd. | IOC | Refining & Marketing (Downstream) | Pure Energy |
| Bharat Petroleum Corporation Ltd. | BPCL | Refining & Marketing (Downstream) | Pure Energy |
| Hindustan Petroleum Corporation Ltd. | HPCL | Refining & Marketing (Downstream) | Pure Energy |
| GAIL (India) Ltd. | GAIL | Gas Transmission & Distribution | Pure Energy |
| Oil India Ltd. | OIL | Upstream (E&P) | Pure Energy |
| Reliance Industries Ltd. | RELIANCE | Diversified (O2C, Retail, Digital) | **Diversified Benchmark** |

**Reliance is not a pure-play oil & gas company** and is shown as a diversified large-cap benchmark throughout, never as a directly comparable peer without caveat — see [`docs/limitations.md`](docs/limitations.md).

## Data Sources

| Data | Source | Period |
|---|---|---|
| Consolidated financial statements | [Screener.in](https://www.screener.in) (aggregates audited BSE/NSE filings) | FY2021–FY2025 |
| Market price, market cap, 1Y equity volatility | [Screener.in](https://www.screener.in), [Tickertape.in](https://www.tickertape.in) | Snapshot, 14-Aug-2026 |
| India 10-year G-Sec yield (risk-free rate) | [FRED](https://fred.stlouisfed.org/data/INDIRLTLT01STM) (OECD series), TradingEconomics (cross-check) | FY2021–FY2025 + current |

Full source log with retrieval dates: [`data/metadata/data_dictionary.md`](data/metadata/data_dictionary.md). Known data gaps are documented, never silently filled — see [`docs/limitations.md`](docs/limitations.md).

## Merton Methodology (summary)

Equity is modeled as a call option on firm assets, struck at the face value of debt. The two option-pricing equations are solved simultaneously via `scipy.optimize.root` (with explicit convergence checks — all 7 companies converge cleanly, residuals < 1e-8) for the unobservable asset value and asset volatility, yielding a Distance-to-Default and a **risk-neutral, model-implied** default probability. Full derivation, intuition and code: [`src/merton_model.py`](src/merton_model.py).

**We never claim a Merton output is "the probability of default."** Every figure is reported as "under the stated Merton assumptions, the model-implied default probability is X%" — see [`docs/assumptions.md`](docs/assumptions.md) §8.

## Altman Methodology (summary)

Uses the **Altman Z''-Score (Emerging Markets, 1995)** — explicitly labeled "modified," chosen because it drops the asset-turnover term that would otherwise penalise capital-intensive energy companies for being capital-intensive rather than distressed. Full justification: [`src/altman_model.py`](src/altman_model.py).

## Financial Ratios

Liquidity, leverage, debt-servicing, profitability, cash-flow and working-capital ratios for all 35 company-years. See [`src/financial_ratios.py`](src/financial_ratios.py) — note the documented proxy used for Current Assets/Liabilities given data-source granularity limits.

## Stress Testing

Profitability shock (−10/−20/−30%), debt shock (+10/+25/+50%), equity-market shock (−10/−20/−30/−40%), a simplified oil/energy-price scenario framework, business-model-differentiated severity multipliers, a combined bear case, and a reverse stress test (bisection-solved over a plausible scenario range). See [`src/stress_testing.py`](src/stress_testing.py).

## Early Warning System

Rule-based, 8-indicator, Green/Yellow/Orange/Red system that names the exact metric(s) triggering each warning. See [`src/early_warning.py`](src/early_warning.py).

## Model Comparison — Results (FY2025 / current snapshot)

| Company | Merton DD | Merton PD (risk-neutral) | Altman Z'' | Altman Zone | Energy Credit Score | Rank | Early Warning | Signal |
|---|---|---|---|---|---|---|---|---|
| GAIL | 8.65 | ~0.0000% | 7.49 | Safe | 84.4 | 1 | Yellow | Agreement – Low Risk |
| RELIANCE* | 10.28 | ~0.0000% | 4.86 | Grey | 65.6 | 2 | Yellow | **Disagreement** |
| ONGC | 6.60 | ~0.0000% | 5.92 | Safe | 62.7 | 3 | Yellow | Agreement – Low Risk |
| BPCL | 5.77 | ~0.0000% | 5.61 | Grey | 58.3 | 4 | Green | **Disagreement** |
| OIL | 5.66 | ~0.0000% | 5.99 | Safe | 57.3 | 5 | Orange | Agreement – Low Risk |
| IOC | 5.48 | ~0.0000% | 5.13 | Grey | 49.0 | 6 | Red | **Disagreement** |
| HPCL | 4.04 | 0.0027% | 4.48 | Distress | 43.5 | 7 | Orange | **Disagreement** |

*Reliance shown per its diversified-benchmark caveat, not as a directly comparable pure-play peer.

**Key finding — model disagreement**: the three refiners (IOC, BPCL, HPCL) and Reliance are where Merton (market-based) and Altman (accounting-based) disagree most. Merton — driven by low observed equity volatility and large market capitalisation — rates them better than Altman, which is still weighed down by FY2023's thin-to-negative refining margins during the government fuel under-recovery period (HPCL posted an operating **loss** that year). This is a genuine, data-driven finding about what each model captures, not a modeling artifact — full discussion in [`outputs/reports/final_report.md`](outputs/reports/final_report.md).

**Sensitivity finding**: across every company, equity volatility is the single largest driver of Merton DD — larger than equivalent-magnitude shocks to debt or equity value (see `outputs/charts/12_sensitivity_heatmap.png`).

**Validation**: all 7 Merton solves converge with residuals < 1e-8; all 28 behavioural sanity checks (debt↑⇒DD↓, equity↓⇒DD↓, volatility↑⇒DD↓, EBIT↑⇒Altman Z↑) pass. See `src/validation.py`.

## Dashboard

An interactive Streamlit + Plotly dashboard (`dashboard/app.py`) provides a company selector, credit KPIs, five-year trends, model comparison, interactive stress-test controls, early warnings, and an evidence-based analyst interpretation panel.

```bash
streamlit run dashboard/app.py
```

## Installation

```bash
git clone <repo-url>
cd energy-credit-risk-engine
pip install -r requirements.txt
```

## Usage

```bash
python src/run_pipeline.py        # runs data cleaning -> ratios -> Altman -> Merton -> comparison
python src/stress_testing.py      # stress scenarios + combined bear case + reverse stress test
python src/sensitivity_analysis.py
python src/validation.py          # numerical + behavioural sanity checks
python src/visualization.py       # generates all 20 charts to outputs/charts/
streamlit run dashboard/app.py    # interactive dashboard
jupyter notebook notebooks/Merton_Altman_Energy_Credit_Risk.ipynb
```

## Repository Structure

```
energy-credit-risk-engine/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/                # raw scraped data + source metadata
│   ├── processed/          # cleaned, analysis-ready CSVs
│   └── metadata/           # data dictionary, source log, validation log
├── notebooks/
│   └── Merton_Altman_Energy_Credit_Risk.ipynb
├── src/
│   ├── data_collection.py
│   ├── data_cleaning.py
│   ├── financial_ratios.py
│   ├── altman_model.py
│   ├── merton_model.py
│   ├── run_pipeline.py
│   ├── stress_testing.py
│   ├── sensitivity_analysis.py
│   ├── credit_score.py
│   ├── early_warning.py
│   ├── validation.py
│   └── visualization.py
├── dashboard/
│   └── app.py
├── outputs/
│   ├── charts/              # 20 PNG charts
│   ├── tables/               # model comparison, final summary CSVs
│   └── reports/              # final report, resume bullets, interview Q&A
└── docs/
    ├── methodology.md
    ├── assumptions.md
    └── limitations.md
```

## IOC Deep Dive

Indian Oil Corporation is used as the primary single-company case study (project author's prior business-development/ESG background at IOCL — disclosed, and the model is not tuned toward any particular conclusion about IOC; see [`outputs/reports/final_report.md`](outputs/reports/final_report.md) §"IOC Deep Dive" and Cell 35 of the notebook). IOC's FY2025 Energy Credit Score (49.0, rank 6/7) and Red early-warning level are a direct, unbiased output of the same pipeline applied to every other company.

## Limitations

See [`docs/limitations.md`](docs/limitations.md) for the full list — data-source granularity, historical market-data availability, Merton/Altman model simplifications, and why this project deliberately does not include a supervised ML default classifier.

## Future Improvements

- Replace the current/historical-volatility split with a licensed market-data feed providing true daily-return series per fiscal year.
- Source a fully classified (current/non-current) balance sheet to remove the Current Ratio / Working Capital proxy.
- Incorporate published credit ratings (CRISIL/ICRA/CARE/India Ratings) as a third comparison point, per project brief §32.
- Extend the debt definition to split short-term vs. long-term borrowings for a KMV-style default point.
- Add a firm-specific asset-beta estimate to sharpen the "physical" PD supplement beyond the current ERP-based approximation.

## Disclaimer

This project is for educational and portfolio purposes only. It does not constitute investment advice, a credit rating, or a recommendation to buy, sell or hold any security. All model outputs are conditional on stated assumptions; see `docs/assumptions.md` and `docs/limitations.md`.
