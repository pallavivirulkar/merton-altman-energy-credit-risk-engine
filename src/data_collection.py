"""
data_collection.py
===================
Raw data ingestion layer for the Merton-Altman Energy Credit Risk Engine.

IMPORTANT - HOW THIS DATA WAS COLLECTED
----------------------------------------
This project runs in a network-restricted research environment. Live API
access (e.g. yfinance, NSE/BSE data APIs) was attempted and blocked at the
network layer. All data below was therefore collected via targeted, documented
web retrieval from public financial-data aggregators and cross-checked where
possible, exactly as a human analyst without a paid terminal (Bloomberg/
Refinitiv) would do. Every figure in this file is a REAL, SOURCED number -
nothing here is synthetic or fabricated. Source, retrieval date and method
are logged in data/metadata/sources_log.csv.

Primary sources used:
  1. Screener.in (https://www.screener.in) - consolidated financial statements
     (Balance Sheet, P&L, Cash Flow, Key Ratios), which in turn aggregate
     audited figures filed with BSE/NSE. Retrieved 16-Aug-2026.
  2. Tickertape.in (https://www.tickertape.in) - current market price, market
     capitalisation, and 1-year trailing historical equity volatility.
     Retrieved 16-Aug-2026 (snapshot as of 14-Aug-2026 market close).
  3. FRED / OECD (https://fred.stlouisfed.org, series INDIRLTLT01STM) - India
     10-year government bond yield (long-term government bond yield series),
     monthly, used as the risk-free rate proxy. Retrieved 16-Aug-2026.

DATA LIMITATION (documented, not silently patched - see docs/limitations.md)
------------------------------------------------------------------------
The free-tier aggregator views used here report Balance Sheet assets/
liabilities at an aggregated level: "Fixed Assets", "CWIP", "Investments",
"Other Assets" and "Borrowings", "Other Liabilities". A current/non-current
split (i.e. a classified balance sheet with explicit Current Assets and
Current Liabilities) was NOT available through any accessible source in this
session (NSE/BSE historical & detailed-statement APIs returned region-block
errors; deeper paid views require login). Consequently:
  - "Other Assets" is used as a proxy for Current Assets (for this sector,
    dominated by inventory, receivables, cash and loans - overwhelmingly
    current in nature for PSU oil & gas operating companies).
  - "Other Liabilities" (Total Liabilities - Borrowings - Equity - Reserves)
    is used as a proxy for Current Liabilities (dominated by trade payables,
    statutory dues and short-term provisions).
  - Inventory and Receivables are BACKED OUT from turnover-day ratios
    (Debtor Days, Inventory Days) that ARE published, rather than invented.
This is flagged explicitly wherever used (see financial_ratios.py) and is
NOT presented as an exact classified-balance-sheet figure.

Similarly, full 5-year daily equity-return histories (needed for a textbook
daily-return annualised volatility per fiscal year) could not be retrieved
in bulk (Yahoo/NSE historical APIs blocked; scraped table views cap at ~50
rows per request). The project therefore uses CURRENT (Aug-2026) 1-year
trailing volatility, published by a data vendor, as the PRIMARY volatility
input for the fully-rigorous cross-sectional Merton analysis, and documents
this explicitly rather than fabricating historical daily-return series.
See docs/assumptions.md, Section "Volatility Methodology" for the full
treatment, including how the 5-year Merton trend is still constructed
honestly from real, varying Debt and real, varying fiscal-year-end market
equity values.
"""

from __future__ import annotations
import pandas as pd

# ---------------------------------------------------------------------------
# 1. COMPANY UNIVERSE & BUSINESS MODEL CLASSIFICATION
# ---------------------------------------------------------------------------
COMPANIES = {
    "ONGC":      {"name": "Oil and Natural Gas Corporation Ltd.", "nse_symbol": "ONGC",      "screener_code": "ONGC",      "business_model": "Upstream (E&P)",            "ownership": "PSU (Govt of India majority)", "peer_group": "Pure Energy"},
    "IOC":       {"name": "Indian Oil Corporation Ltd.",          "nse_symbol": "IOC",       "screener_code": "IOC",       "business_model": "Refining & Marketing (Downstream)", "ownership": "PSU (Govt of India majority)", "peer_group": "Pure Energy"},
    "BPCL":      {"name": "Bharat Petroleum Corporation Ltd.",    "nse_symbol": "BPCL",      "screener_code": "BPCL",      "business_model": "Refining & Marketing (Downstream)", "ownership": "PSU (Govt of India majority)", "peer_group": "Pure Energy"},
    "HPCL":      {"name": "Hindustan Petroleum Corporation Ltd.", "nse_symbol": "HINDPETRO", "screener_code": "HINDPETRO", "business_model": "Refining & Marketing (Downstream)", "ownership": "PSU (Govt of India majority)", "peer_group": "Pure Energy"},
    "GAIL":      {"name": "GAIL (India) Ltd.",                    "nse_symbol": "GAIL",      "screener_code": "GAIL",      "business_model": "Gas Transmission & Distribution",   "ownership": "PSU (Govt of India majority)", "peer_group": "Pure Energy"},
    "OIL":       {"name": "Oil India Ltd.",                       "nse_symbol": "OIL",       "screener_code": "OIL",       "business_model": "Upstream (E&P)",            "ownership": "PSU (Govt of India majority)", "peer_group": "Pure Energy"},
    "RELIANCE":  {"name": "Reliance Industries Ltd.",             "nse_symbol": "RELIANCE",  "screener_code": "RELIANCE",  "business_model": "Diversified (O2C, Retail, Digital)", "ownership": "Private, widely held",         "peer_group": "Diversified Benchmark"},
}

FISCAL_YEARS = [2021, 2022, 2023, 2024, 2025]  # FY label = year of fiscal year-end (31 March)

# ---------------------------------------------------------------------------
# 2. CONSOLIDATED FINANCIAL STATEMENT DATA (Rs. Crore), FY2021-FY2025
#    Source: Screener.in consolidated financials, retrieved 16-Aug-2026
#    All figures as filed / audited consolidated statements.
# ---------------------------------------------------------------------------
# Field definitions:
#   equity_capital, reserves      -> Shareholders' equity components
#   borrowings                    -> Total financial borrowings (ST+LT combined;
#                                     aggregator does not split maturity - documented)
#   other_liabilities             -> Total Liabilities - Equity Capital - Reserves - Borrowings
#                                     (proxy for current liabilities + other non-debt liabilities)
#   total_assets = total_liabilities (balance sheet identity, both sides tie out)
#   fixed_assets, cwip, investments, other_assets -> asset-side breakdown
#   sales                         -> Total revenue from operations
#   operating_profit              -> EBITDA (Sales - Operating Expenses, excl. D&A, interest, other income)
#   other_income                  -> Non-operating income (where disclosed)
#   interest                      -> Finance costs / interest expense
#   depreciation                  -> Depreciation & amortisation
#   pbt, net_profit, eps          -> as reported (where disclosed)
#   cfo                           -> Cash flow from operating activities
#   fcf                           -> Free cash flow (as computed by source; CFO - capex, approx)
#   debtor_days, inventory_days, payable_days -> working-capital turnover ratios (where disclosed)
#   roce                          -> Return on Capital Employed (%)

FINANCIALS_RAW = [
    # ONGC
    dict(company="ONGC", fy=2021, equity_capital=6290, reserves=214691, borrowings=133187, other_liabilities=187580, total_liabilities=541748,
         fixed_assets=243746, cwip=100309, investments=60320, other_assets=137372,
         sales=303849, operating_profit=49473, other_income=11271, interest=5079, depreciation=25538, pbt=30126, net_profit=21360, eps=12.96,
         cfo=47185, fcf=15147, debtor_days=19, inventory_days=85, payable_days=51, roce_pct=9),
    dict(company="ONGC", fy=2022, equity_capital=6290, reserves=253213, borrowings=121986, other_liabilities=201771, total_liabilities=583260,
         fixed_assets=254402, cwip=106719, investments=66642, other_assets=155496,
         sales=491246, operating_profit=79874, other_income=6797, interest=5696, depreciation=26883, pbt=54091, net_profit=49294, eps=36.19,
         cfo=78248, fcf=45158, debtor_days=14, inventory_days=90, payable_days=66, roce_pct=16),
    dict(company="ONGC", fy=2023, equity_capital=6290, reserves=274357, borrowings=142255, other_liabilities=190212, total_liabilities=613115,
         fixed_assets=250819, cwip=113945, investments=78873, other_assets=169478,
         sales=632291, operating_profit=75527, other_income=-30, interest=7889, depreciation=24557, pbt=43051, net_profit=32778, eps=28.17,
         cfo=84211, fcf=47758, debtor_days=11, inventory_days=61, payable_days=46, roce_pct=14),
    dict(company="ONGC", fy=2024, equity_capital=6290, reserves=332779, borrowings=191195, other_liabilities=206357, total_liabilities=736621,
         fixed_assets=317183, cwip=118729, investments=100862, other_assets=199847,
         sales=601581, operating_profit=102383, other_income=14712, interest=13026, depreciation=30440, pbt=73629, net_profit=55273, eps=39.06,
         cfo=98847, fcf=60965, debtor_days=12, inventory_days=87, payable_days=61, roce_pct=18),
    dict(company="ONGC", fy=2025, equity_capital=6290, reserves=337150, borrowings=187817, other_liabilities=221401, total_liabilities=752658,
         fixed_assets=340175, cwip=112614, investments=95617, other_assets=204252,
         sales=612064, operating_profit=88857, other_income=13282, interest=14535, depreciation=35206, pbt=52398, net_profit=38329, eps=28.80,
         cfo=90856, fcf=50143, debtor_days=13, inventory_days=99, payable_days=64, roce_pct=12),

    # IOC
    dict(company="IOC", fy=2021, equity_capital=9181, reserves=102657, borrowings=116649, other_liabilities=126658, total_liabilities=355145,
         fixed_assets=157085, cwip=36291, investments=44717, other_assets=117053,
         sales=363950, operating_profit=39929, other_income=4696, interest=2933, depreciation=10941, pbt=30751, net_profit=21762, eps=15.32,
         cfo=49650, fcf=27904, debtor_days=14, inventory_days=111, payable_days=None, roce_pct=15),
    dict(company="IOC", fy=2022, equity_capital=9181, reserves=124354, borrowings=132020, other_liabilities=145327, total_liabilities=410882,
         fixed_assets=160514, cwip=47469, investments=52352, other_assets=150546,
         sales=589336, operating_profit=46619, other_income=4318, interest=4301, depreciation=12348, pbt=34289, net_profit=25727, eps=17.78,
         cfo=24570, fcf=1533, debtor_days=12, inventory_days=84, payable_days=None, roce_pct=16),
    dict(company="IOC", fy=2023, equity_capital=13772, reserves=125949, borrowings=148977, other_liabilities=153298, total_liabilities=441995,
         fixed_assets=180048, cwip=51133, investments=52190, other_assets=158624,
         sales=841756, operating_profit=30683, other_income=5124, interest=7588, depreciation=13181, pbt=15038, net_profit=11704, eps=6.93,
         cfo=29644, fcf=-2524, debtor_days=7, inventory_days=59, payable_days=None, roce_pct=8),
    dict(company="IOC", fy=2024, equity_capital=13772, reserves=169645, borrowings=132628, other_liabilities=166639, total_liabilities=482683,
         fixed_assets=195998, cwip=61032, investments=65542, other_assets=160111,
         sales=776352, operating_profit=75650, other_income=5384, interest=7881, depreciation=15866, pbt=57288, net_profit=43161, eps=29.55,
         cfo=71146, fcf=34453, debtor_days=6, inventory_days=70, payable_days=None, roce_pct=21),
    dict(company="IOC", fy=2025, equity_capital=13772, reserves=172716, borrowings=152271, other_liabilities=168796, total_liabilities=507554,
         fixed_assets=201142, cwip=77921, investments=67218, other_assets=161272,
         sales=758106, operating_profit=36040, other_income=7112, interest=9311, depreciation=16777, pbt=17063, net_profit=13789, eps=9.63,
         cfo=34452, fcf=83, debtor_days=9, inventory_days=63, payable_days=None, roce_pct=7),

    # BPCL
    dict(company="BPCL", fy=2021, equity_capital=2093, reserves=51462, borrowings=54532, other_liabilities=52891, total_liabilities=160978,
         fixed_assets=64098, cwip=17037, investments=26768, other_assets=53075,
         sales=230171, operating_profit=21001, other_income=None, interest=1723, depreciation=4334, pbt=22432, net_profit=17320, eps=37.26,
         cfo=23455, fcf=14403, debtor_days=12, inventory_days=52, payable_days=None, roce_pct=18),
    dict(company="BPCL", fy=2022, equity_capital=2129, reserves=49776, borrowings=64534, other_liabilities=71089, total_liabilities=187529,
         fixed_assets=83901, cwip=15433, investments=23616, other_assets=64578,
         sales=346791, operating_profit=19137, other_income=None, interest=2606, depreciation=5434, pbt=16037, net_profit=11682, eps=26.93,
         cfo=20336, fcf=12643, debtor_days=10, inventory_days=51, payable_days=None, roce_pct=16),
    dict(company="BPCL", fy=2023, equity_capital=2129, reserves=51393, borrowings=69376, other_liabilities=65240, total_liabilities=188138,
         fixed_assets=86675, cwip=16249, investments=26778, other_assets=58436,
         sales=473187, operating_profit=10899, other_income=None, interest=4263, depreciation=6369, pbt=2821, net_profit=2131, eps=4.91,
         cfo=12466, fcf=3960, debtor_days=5, inventory_days=32, payable_days=None, roce_pct=7),
    dict(company="BPCL", fy=2024, equity_capital=2136, reserves=73499, borrowings=54599, other_liabilities=72184, total_liabilities=202418,
         fixed_assets=86798, cwip=20204, investments=26631, other_assets=68785,
         sales=448083, operating_profit=44082, other_income=None, interest=4149, depreciation=6771, pbt=36194, net_profit=26859, eps=61.91,
         cfo=35936, fcf=26391, debtor_days=7, inventory_days=42, payable_days=None, roce_pct=32),
    dict(company="BPCL", fy=2025, equity_capital=4273, reserves=77112, borrowings=61101, other_liabilities=75898, total_liabilities=218382,
         fixed_assets=88628, cwip=26387, investments=26531, other_assets=76837,
         sales=440272, operating_profit=25401, other_income=None, interest=3591, depreciation=7257, pbt=18182, net_profit=13337, eps=30.74,
         cfo=23678, fcf=8574, debtor_days=8, inventory_days=43, payable_days=None, roce_pct=16),

    # HPCL
    dict(company="HPCL", fy=2021, equity_capital=1452, reserves=36628, borrowings=43709, other_liabilities=52438, total_liabilities=134228,
         fixed_assets=50912, cwip=25336, investments=15093, other_assets=42887,
         sales=233248, operating_profit=16055, other_income=2731, interest=963, depreciation=3625, pbt=None, net_profit=10663, eps=48.83,
         cfo=17829, fcf=6222, debtor_days=11, inventory_days=53, payable_days=None, roce_pct=19),
    dict(company="HPCL", fy=2022, equity_capital=1419, reserves=39985, borrowings=48498, other_liabilities=64774, total_liabilities=154676,
         fixed_assets=58126, cwip=28907, investments=18867, other_assets=48775,
         sales=349913, operating_profit=10244, other_income=3897, interest=997, depreciation=4000, pbt=None, net_profit=7294, eps=34.28,
         cfo=15810, fcf=3782, debtor_days=7, inventory_days=40, payable_days=None, roce_pct=12),
    dict(company="HPCL", fy=2023, equity_capital=1419, reserves=30844, borrowings=70671, other_liabilities=58452, total_liabilities=161387,
         fixed_assets=68387, cwip=25607, investments=23689, other_assets=43703,
         sales=440709, operating_profit=-7192, other_income=3942, interest=2174, depreciation=4560, pbt=None, net_profit=-6980, eps=-32.80,
         cfo=-3466, fcf=-12646, debtor_days=6, inventory_days=25, payable_days=None, roce_pct=-8),
    dict(company="HPCL", fy=2024, equity_capital=1419, reserves=45502, borrowings=66684, other_liabilities=69188, total_liabilities=182794,
         fixed_assets=79763, cwip=20078, investments=29540, other_assets=53413,
         sales=433857, operating_profit=24928, other_income=3725, interest=2556, depreciation=5596, pbt=None, net_profit=16015, eps=75.26,
         cfo=23852, fcf=13906, debtor_days=8, inventory_days=32, payable_days=None, roce_pct=21),
    dict(company="HPCL", fy=2025, equity_capital=2128, reserves=49016, borrowings=70558, other_liabilities=73067, total_liabilities=194770,
         fixed_assets=86179, cwip=17967, investments=27046, other_assets=63577,
         sales=434106, operating_profit=16448, other_income=2072, interest=3365, depreciation=6154, pbt=None, net_profit=6736, eps=31.66,
         cfo=14231, fcf=4814, debtor_days=10, inventory_days=35, payable_days=None, roce_pct=11),

    # GAIL
    dict(company="GAIL", fy=2021, equity_capital=4440, reserves=48742, borrowings=7873, other_liabilities=19975, total_liabilities=81030,
         fixed_assets=41160, cwip=13400, investments=13058, other_assets=13413,
         sales=57372, operating_profit=7245, other_income=None, interest=179, depreciation=2174, pbt=None, net_profit=6143, eps=9.21,
         cfo=8993, fcf=3309, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=13),
    dict(company="GAIL", fy=2022, equity_capital=4440, reserves=59674, borrowings=9216, other_liabilities=23254, total_liabilities=96584,
         fixed_assets=44572, cwip=15490, investments=16408, other_assets=20114,
         sales=92770, operating_profit=15161, other_income=None, interest=202, depreciation=2420, pbt=None, net_profit=12304, eps=18.40,
         cfo=9420, fcf=2481, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=23),
    dict(company="GAIL", fy=2023, equity_capital=6575, reserves=58352, borrowings=17816, other_liabilities=25062, total_liabilities=107805,
         fixed_assets=49697, cwip=16646, investments=17248, other_assets=24214,
         sales=145668, operating_profit=7500, other_income=None, interest=365, depreciation=2702, pbt=None, net_profit=5596, eps=8.54,
         cfo=3205, fcf=-5548, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=10),
    dict(company="GAIL", fy=2024, equity_capital=6575, reserves=70422, borrowings=21794, other_liabilities=25944, total_liabilities=124735,
         fixed_assets=55188, cwip=23627, investments=21910, other_assets=24010,
         sales=133228, operating_profit=14314, other_income=None, interest=719, depreciation=3672, pbt=None, net_profit=9903, eps=15.06,
         cfo=12586, fcf=98, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=15),
    dict(company="GAIL", fy=2025, equity_capital=6575, reserves=78422, borrowings=21595, other_liabilities=26583, total_liabilities=133176,
         fixed_assets=58836, cwip=27421, investments=22765, other_assets=24155,
         sales=141902, operating_profit=15412, other_income=None, interest=740, depreciation=3799, pbt=None, net_profit=12463, eps=18.93,
         cfo=15727, fcf=7818, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=14),

    # OIL (Oil India)
    dict(company="OIL", fy=2021, equity_capital=1084, reserves=22582, borrowings=19718, other_liabilities=12151, total_liabilities=55535,
         fixed_assets=15969, cwip=3171, investments=24010, other_assets=12385,
         sales=17616, operating_profit=5689, other_income=None, interest=660, depreciation=1844, pbt=None, net_profit=4146, eps=21.69,
         cfo=5235, fcf=2108, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=13),
    dict(company="OIL", fy=2022, equity_capital=1084, reserves=29478, borrowings=16721, other_liabilities=13846, total_liabilities=61129,
         fixed_assets=16805, cwip=5900, investments=27099, other_assets=11325,
         sales=25906, operating_profit=10500, other_income=None, interest=940, depreciation=1824, pbt=None, net_profit=6719, eps=34.56,
         cfo=9310, fcf=3342, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=21),
    dict(company="OIL", fy=2023, equity_capital=1084, reserves=37397, borrowings=18832, other_liabilities=16866, total_liabilities=74179,
         fixed_assets=18098, cwip=11953, investments=27924, other_assets=16204,
         sales=36084, operating_profit=15255, other_income=None, interest=901, depreciation=1947, pbt=None, net_profit=9854, eps=53.66,
         cfo=11410, fcf=2886, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=25),
    dict(company="OIL", fy=2024, equity_capital=1084, reserves=47255, borrowings=24040, other_liabilities=20115, total_liabilities=92494,
         fixed_assets=20520, cwip=20028, investments=34450, other_assets=17496,
         sales=31749, operating_profit=12504, other_income=None, interest=964, depreciation=2129, pbt=None, net_profit=6980, eps=38.95,
         cfo=10933, fcf=-1130, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=18),
    dict(company="OIL", fy=2025, equity_capital=1627, reserves=48141, borrowings=30645, other_liabilities=24410, total_liabilities=104823,
         fixed_assets=23649, cwip=29527, investments=31613, other_assets=20034,
         sales=31703, operating_profit=11158, other_income=None, interest=1069, depreciation=2318, pbt=None, net_profit=7040, eps=40.27,
         cfo=11332, fcf=-1637, debtor_days=None, inventory_days=None, payable_days=None, roce_pct=13),

    # RELIANCE (diversified benchmark)
    dict(company="RELIANCE", fy=2021, equity_capital=6445, reserves=693727, borrowings=278962, other_liabilities=340931, total_liabilities=1320065,
         fixed_assets=541258, cwip=125953, investments=364828, other_assets=288026,
         sales=466307, operating_profit=80790, other_income=None, interest=21189, depreciation=26572, pbt=55461, net_profit=53739, eps=38.75,
         cfo=26958, fcf=-76560, debtor_days=15, inventory_days=102, payable_days=None, roce_pct=8),
    dict(company="RELIANCE", fy=2022, equity_capital=6765, reserves=772720, borrowings=319158, other_liabilities=399979, total_liabilities=1498622,
         fixed_assets=627798, cwip=172506, investments=394264, other_assets=304054,
         sales=694673, operating_profit=108581, other_income=None, interest=14584, depreciation=29782, pbt=83815, net_profit=67845, eps=44.87,
         cfo=110654, fcf=13646, debtor_days=12, inventory_days=83, payable_days=None, roce_pct=8),
    dict(company="RELIANCE", fy=2023, equity_capital=6766, reserves=709106, borrowings=451664, other_liabilities=438346, total_liabilities=1605882,
         fixed_assets=724805, cwip=293752, investments=235560, other_assets=351765,
         sales=876396, operating_profit=142318, other_income=None, interest=19571, depreciation=40303, pbt=94464, net_profit=74088, eps=49.29,
         cfo=115032, fcf=-16770, debtor_days=12, inventory_days=87, payable_days=None, roce_pct=9),
    dict(company="RELIANCE", fy=2024, equity_capital=6766, reserves=786715, borrowings=350719, other_liabilities=610848, total_liabilities=1755048,
         fixed_assets=779985, cwip=338855, investments=225672, other_assets=410536,
         sales=899041, operating_profit=162498, other_income=None, interest=23118, depreciation=50832, pbt=104340, net_profit=79020, eps=51.45,
         cfo=158788, fcf=21212, debtor_days=13, inventory_days=95, payable_days=None, roce_pct=10),
    dict(company="RELIANCE", fy=2025, equity_capital=13532, reserves=829668, borrowings=374313, other_liabilities=732200, total_liabilities=1949713,
         fixed_assets=999393, cwip=262358, investments=242381, other_assets=445581,
         sales=962820, operating_profit=165598, other_income=None, interest=24269, depreciation=53136, pbt=106017, net_profit=81309, eps=51.47,
         cfo=178703, fcf=41079, debtor_days=16, inventory_days=85, payable_days=None, roce_pct=10),
]

# ---------------------------------------------------------------------------
# 3. CURRENT MARKET DATA SNAPSHOT (as of 14-Aug-2026 close)
#    Source: Screener.in (price, market cap, face value, book value, P/E,
#    ROCE, ROE, dividend yield) and Tickertape.in (1-year trailing equity
#    volatility). Retrieved 16-Aug-2026.
# ---------------------------------------------------------------------------
MARKET_DATA_RAW = [
    dict(company="ONGC",     price=236.40,  market_cap_cr=297398,  face_value=5,  book_value=296, stock_pe=6.80,  div_yield_pct=5.60, roce_pct=14.2, roe_pct=11.6, volatility_1y_pct=23.63),
    dict(company="IOC",      price=139.40,  market_cap_cr=196850,  face_value=10, book_value=155, stock_pe=5.85,  div_yield_pct=5.92, roce_pct=18.7, roe_pct=20.5, volatility_1y_pct=26.93),
    dict(company="BPCL",     price=319.45,  market_cap_cr=138594,  face_value=10, book_value=231, stock_pe=8.94,  div_yield_pct=5.48, roce_pct=25.6, roe_pct=28.8, volatility_1y_pct=29.58),
    dict(company="HPCL",     price=373.50,  market_cap_cr=79474,   face_value=10, book_value=308, stock_pe=47.6,  div_yield_pct=6.49, roce_pct=22.2, roe_pct=30.9, volatility_1y_pct=34.99),
    dict(company="GAIL",     price=174.90,  market_cap_cr=114998,  face_value=10, book_value=135, stock_pe=11.6,  div_yield_pct=3.14, roce_pct=9.67, roe_pct=8.71, volatility_1y_pct=25.51),
    dict(company="OIL",      price=468.50,  market_cap_cr=76207,   face_value=10, book_value=357, stock_pe=9.12,  div_yield_pct=2.24, roce_pct=11.6, roe_pct=12.3, volatility_1y_pct=30.94),
    dict(company="RELIANCE", price=1310.00, market_cap_cr=1772762, face_value=10, book_value=668, stock_pe=23.7,  div_yield_pct=0.46, roce_pct=10.3, roe_pct=8.91, volatility_1y_pct=20.82),
]
MARKET_SNAPSHOT_DATE = "2026-08-14"

# ---------------------------------------------------------------------------
# 4. RISK-FREE RATE: India 10-Year Government Bond Yield (fiscal year-end, March)
#    Source: FRED series INDIRLTLT01STM (OECD long-term govt bond yield, India),
#    monthly average for March of each year. Retrieved 16-Aug-2026.
# ---------------------------------------------------------------------------
RISK_FREE_RATE_RAW = [
    dict(fy=2021, date="2021-03-31", rate_pct=6.35),
    dict(fy=2022, date="2022-03-31", rate_pct=6.82),
    dict(fy=2023, date="2023-03-31", rate_pct=7.36),
    dict(fy=2024, date="2024-03-31", rate_pct=7.07),
    dict(fy=2025, date="2025-03-31", rate_pct=6.68),
]
RISK_FREE_RATE_CURRENT = dict(date="2026-08-14", rate_pct=6.76, source="tradingeconomics.com (live quote, cross-check)")


def load_financials() -> pd.DataFrame:
    return pd.DataFrame(FINANCIALS_RAW)


def load_market_data() -> pd.DataFrame:
    return pd.DataFrame(MARKET_DATA_RAW)


def load_risk_free_rate() -> pd.DataFrame:
    return pd.DataFrame(RISK_FREE_RATE_RAW)


def load_company_universe() -> pd.DataFrame:
    df = pd.DataFrame.from_dict(COMPANIES, orient="index")
    df.index.name = "company"
    return df.reset_index()


if __name__ == "__main__":
    print(load_financials().shape, load_market_data().shape, load_risk_free_rate().shape)
