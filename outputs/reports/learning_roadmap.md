# Learning Roadmap

A suggested order for understanding this project deeply enough to defend it in an interview — each stage builds on the last.

**Stage 1 — Financial statements.** Read a balance sheet, income statement, and cash flow statement for one company in this dataset (e.g. IOC's, via `data/processed/financials.csv`). Understand what Equity Capital, Reserves, Borrowings, EBITDA, and CFO actually represent.

**Stage 2 — Debt and leverage.** Understand Debt/EBITDA and Debt/Equity as "how many years of cash flow / how much shareholder cushion stands behind this debt." Look at HPCL's FY2023 numbers as a concrete example of leverage ratios deteriorating in a single bad year.

**Stage 3 — Credit risk.** Understand that credit risk is about debt repayment, distinct from equity/stock-price risk. Read `docs/methodology.md` §2 for why this sector makes the distinction concrete.

**Stage 4 — Equity vs debt.** Understand the capital structure: equity holders get residual value after debt is paid, and have limited liability (can't lose more than they put in).

**Stage 5 — Options intuition.** Understand a call option's payoff (upside participation, capped downside at zero premium loss) and see why equity's payoff structure matches it exactly. Work through the simple hypothetical in `src/merton_model.py`'s docstring before touching real numbers.

**Stage 6 — Merton model.** Read `src/merton_model.py` end to end: the two equations, why they're solved simultaneously, what `scipy.optimize.root` is doing. Re-run the `if __name__ == "__main__"` example by hand with a calculator for one or two steps to build intuition.

**Stage 7 — Distance-to-default.** Understand d2 as "how many standard deviations of (log) asset value separate you from the default point," and why N(-d2) turns that distance into a probability under the model's assumptions.

**Stage 8 — Altman Z-score.** Read `src/altman_model.py`'s docstring, understand each of the four ratios in one sentence each, and understand why this project chose the 1995 EM variant over the 1968 original.

**Stage 9 — Energy-sector economics.** Understand upstream vs downstream vs gas transmission vs diversified business models, and why an oil-price shock hits each differently (`docs/methodology.md` §2, and `src/stress_testing.py`'s business-model multipliers).

**Stage 10 — Stress testing.** Work through `src/stress_testing.py`'s isolated shocks, then the combined bear case, then the reverse stress test — in that order, since each builds conceptually on the last (single factor → correlated factors → "how bad would it have to get").

**Stage 11 — Model validation.** Read `src/validation.py` and understand the difference between numerical validation (did the solver actually converge to a real answer) and behavioural validation (does the model respond to inputs the way economic theory says it should).

Once comfortable through Stage 11, the full `outputs/reports/final_report.md` and the executed notebook should read as a connected story rather than a list of disconnected outputs.
