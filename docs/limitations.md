# Limitations

This project is built for demonstration, learning, and portfolio purposes. It is **not** investment advice, a credit rating, or a substitute for a professional credit assessment. Read this document before citing any number from this project as a definitive statement about a company's creditworthiness.

## Data limitations

### 1. Environment / tooling constraints on market data
This project was built in a network-restricted research environment. Live financial-data APIs (yfinance, NSE/BSE historical-data endpoints) were attempted and returned connection errors (`curl: (7) CONNECT tunnel failed`) or region-block messages ("This site is not accessible in your region at the moment"). Bulk historical-price download endpoints (Yahoo Finance chart API, Stooq CSV export, NSE API) were blocked by `robots.txt` or returned 403/404 errors when fetched. Scraped historical-price table views (e.g. TipRanks) cap at roughly 50 rows per request regardless of the requested date range, which is sufficient for a spot-check but not for reconstructing a 5-year, ~1,250-trading-day daily-return series per company.

**Consequence:** a full, independently-computed daily-return annualised equity volatility for each of the FY2021–FY2025 fiscal years, and the historical fiscal-year-end market equity value implied by actual historical share prices, could not be retrieved. The project uses a single current (14-Aug-2026) volatility and market-cap snapshot as the primary, fully-rigorous Merton input, and documents an explicitly-labeled "leverage-only" decomposition for the FY2021–FY2024 trend (see `docs/assumptions.md`, Section 6). **Do not read the historical DD trend chart as a claim about actual 2021–2024 market pricing** - read the axis label and footnote on that chart, which state the methodology plainly.

### 2. Balance-sheet granularity
The accessible data source (Screener.in, free tier) reports an aggregated balance sheet: Fixed Assets, CWIP, Investments, Other Assets on the asset side; Equity Capital, Reserves, Borrowings, Other Liabilities on the liability side. A fully classified balance sheet with an explicit Current Assets / Current Liabilities split was not available (NSE/BSE detailed-filing APIs returned region-block errors; deeper aggregator views require a paid login).

**Consequence:** Current Ratio, Quick Ratio, Working Capital/Total Assets (Altman X1) all use "Other Assets" and "Other Liabilities" as documented proxies for current assets/liabilities. For a sector with predominantly current-natured residual buckets (inventory, receivables, cash, payables, provisions) this is a reasonable approximation, but it will systematically misstate liquidity ratios to the extent those buckets contain non-current items (e.g., long-term employee benefit provisions, deferred tax). **Every chart, table, and dashboard panel showing these ratios is labeled "(proxy)".**

### 3. Company-specific data gaps
- HPCL: PBT not disclosed at the captured granularity (net profit and EPS were used instead; PBT-dependent ratios are left blank rather than backed into a number).
- GAIL, Oil India: PBT, Debtor Days, Inventory Days, Payable Days not disclosed at the captured granularity.
- BPCL: Other Income not separately disclosed for most years (EBIT is computed as EBITDA − Depreciation specifically so this gap does not block EBIT-based ratios).
- Payable Days is only available for ONGC; the full Cash Conversion Cycle is therefore only computable for ONGC. Other companies show a partial DSO+DIO figure, clearly labeled.
- These are listed in full, with the exact missing-field counts, in `data/metadata/validation_log.csv` and `data/metadata/data_dictionary.md`. None were estimated or fabricated.

### 4. Single point-in-time market snapshot
All seven companies' market data (price, market cap, volatility) are drawn from the same date (14-Aug-2026), which is good for cross-sectional comparability but means the "current" Merton analysis reflects market conditions on that specific day, which may not be representative of a longer-run average. The sensitivity analysis is designed to partially address this by showing how much the results would change under plausible alternative levels.

## Model limitations

### 5. Merton model simplifications
- Assumes a single zero-coupon debt claim maturing at T — real companies have layered, amortising, multi-maturity debt structures.
- Assumes lognormal asset value dynamics and constant asset volatility — asset returns for commodity-exposed companies can exhibit jumps and regime shifts (e.g. oil price shocks) that a lognormal diffusion does not capture well.
- Ignores dividends, which for PSU energy companies (dividend yields of 2-7% in this dataset) transfer value out of the firm and would, if modeled explicitly, tend to lower the implied asset value / raise implied volatility versus the simplified model used here.
- The risk-neutral PD is **not** a real-world default probability - see `docs/assumptions.md` Section 8 and `src/merton_model.py` docstring. It is systematically higher than a physical-measure PD because it embeds a risk premium, and it should never be quoted as "the probability company X defaults."
- Government ownership: six of the seven companies are majority Government-of-India-owned. Implicit sovereign support is a real credit factor that the Merton model - built purely from market-observable equity and debt data - does not explicitly capture. This may mean the model UNDERSTATES the effective credit quality of these PSUs relative to what a rating agency (which does consider parentage/support) would conclude, or it may simply be reflected already in these companies' low observed equity volatility. This project does not take a position on which; it is flagged as an open question for the reader.

### 6. Altman Z''-Score simplifications
- Designed originally for non-financial industrials broadly, not calibrated specifically to the oil & gas sector's capital structure norms (which run higher-leverage than many industries even in a "healthy" steady state, given asset-backed borrowing capacity).
- Retained Earnings is proxied by total Reserves & Surplus (may include securities premium and other non-retained-earnings reserves).
- The interpretation zones (Safe/Grey/Distress) are a widely-cited convention for the EM variant, not a universally agreed, precisely back-tested threshold set for Indian energy PSUs specifically.

### 7. Custom Energy Corporate Credit Score
Entirely project-defined (see `docs/assumptions.md` Section 12). It is a transparent, traceable composite - not a validated statistical model, not back-tested against actual default outcomes (none of these seven companies has defaulted in the sample period, so there is no default data to back-test against - see below), and not comparable to a rating agency's methodology.

### 8. No supervised default-prediction model
All seven companies are large, systemically important, majority Government-of-India-backed (except Reliance) entities; none has defaulted in the observed period or, to this project's knowledge, in Indian corporate history. With zero default events in the sample, there is no statistically meaningful way to train or validate a supervised classifier (logistic regression or otherwise) to predict default. Building one anyway - and reporting a spurious accuracy/AUC number from a model with no positive examples - would be actively misleading. This project therefore does NOT include a default-prediction ML model, and treats that omission as a methodological strength, not a gap (see `docs/methodology.md`, "Why no ML default classifier").

## What this project is not
- Not a credit rating and not a substitute for CRISIL/ICRA/CARE/India Ratings/Moody's/S&P analysis, which incorporate qualitative factors (management quality, sector outlook, explicit government support agreements, covenant structures) this project does not have access to.
- Not investment advice.
- Not a claim that any company's shares, bonds, or credit risk will behave as this model implies in the future - all model outputs are conditional on the stated assumptions and inputs, which are estimates, not certainties.
