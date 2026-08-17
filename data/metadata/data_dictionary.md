# Data Dictionary & Source Log

## Coverage
- 7 companies: ONGC, IOC, BPCL, HPCL, GAIL, OIL (Oil India), RELIANCE
- 5 fiscal years: FY2021–FY2025 (fiscal year ends 31 March)
- 35 company-year observations for accounting data
- 1 current market snapshot (14-Aug-2026) for market/volatility data
- 5 fiscal year-end risk-free rate observations

## Sources

| # | Data | Source | URL | Retrieved | Type |
|---|------|--------|-----|-----------|------|
| 1 | Consolidated Balance Sheet, P&L, Cash Flow, Key Ratios FY2021–FY2025 for all 7 companies | Screener.in (aggregates audited statements filed with BSE/NSE) | screener.in/company/{CODE}/consolidated/ | 2026-08-16 | Reported (sourced from audited filings) |
| 2 | Current share price, market capitalisation, face value, book value, P/E, ROCE, ROE, dividend yield (as of 14-Aug-2026) | Screener.in | screener.in/company/{CODE}/consolidated/ | 2026-08-16 | Reported |
| 3 | 1-year trailing historical equity volatility (as of 14-Aug-2026) | Tickertape.in | tickertape.in/stocks/{slug} | 2026-08-16 | Reported (vendor-computed) |
| 4 | India 10-year government bond yield, monthly, March of each FY 2021–2025 | FRED (Federal Reserve Bank of St. Louis), series INDIRLTLT01STM, originally OECD | fred.stlouisfed.org/data/INDIRLTLT01STM | 2026-08-16 | Reported |
| 5 | Current India 10Y yield cross-check | TradingEconomics.com | tradingeconomics.com/india/government-bond-yield | 2026-08-16 | Reported (cross-check only) |

## Field definitions (financials.csv)

| Field | Definition | Unit |
|---|---|---|
| equity_capital | Paid-up share capital | Rs. Crore |
| reserves | Reserves & surplus | Rs. Crore |
| borrowings | Total financial borrowings (short-term + long-term combined; source does not split by maturity — see limitations.md) | Rs. Crore |
| other_liabilities | Total Liabilities − Equity Capital − Reserves − Borrowings (residual; proxy for current liabilities + non-debt long-term liabilities) | Rs. Crore |
| total_liabilities | Total Liabilities = Total Assets (balance sheet identity) | Rs. Crore |
| fixed_assets, cwip, investments, other_assets | Asset-side breakdown as reported; other_assets is a residual proxy for current assets | Rs. Crore |
| sales | Revenue from operations | Rs. Crore |
| operating_profit | EBITDA = Sales − operating expenses (excludes D&A, interest, other income); verified against reported PBT reconciliation | Rs. Crore |
| other_income | Non-operating income (where disclosed) | Rs. Crore |
| interest | Finance costs | Rs. Crore |
| depreciation | Depreciation & amortisation | Rs. Crore |
| pbt, net_profit, eps | As reported (where disclosed) | Rs. Crore / Rs. |
| cfo | Cash flow from operating activities | Rs. Crore |
| fcf | Free cash flow (source-computed) | Rs. Crore |
| debtor_days, inventory_days, payable_days | Working-capital turnover ratios, where disclosed by source | Days |
| roce_pct | Return on Capital Employed | % |

## Known data gaps (documented, not fabricated)

- **Current/non-current balance sheet split**: not available from the accessible data source. `other_assets` and `other_liabilities` are used as documented proxies for current assets/current liabilities. See `docs/limitations.md`.
- **HPCL**: `cwip`, `investments`, `other_assets`, `pbt` not disclosed at the level of granularity captured; left as NaN, not estimated.
- **GAIL, OIL**: `pbt`, `debtor_days`, `inventory_days`, `payable_days` not disclosed at the granularity captured; left as NaN.
- **BPCL**: `other_income` not separately disclosed at the granularity captured for most years; left as NaN. EBIT is computed as EBITDA − Depreciation (operating basis) specifically so this gap does not block EBIT-based ratios.
- **payable_days**: only available for ONGC; Cash Conversion Cycle is therefore only fully computable for ONGC and is flagged as partial (Debtor Days + Inventory Days only) for the other six companies.
- **Historical (FY2021–FY2024) daily-return equity volatility and historical market capitalisation**: could not be retrieved via available tools (bulk historical price APIs blocked at the network layer in this environment; scraped historical-price table views cap at ~50 rows per request; NSE/BSE APIs returned region-block errors). See `docs/assumptions.md` → "Volatility & Historical Market Data Methodology" for how this is handled honestly in the Merton model (current-snapshot primary analysis + explicitly labeled leverage-only historical decomposition).

## Validation
Automated checks are in `src/data_cleaning.py` and their output is in `data/metadata/validation_log.csv`. No values were silently corrected; all flagged issues are logged.
