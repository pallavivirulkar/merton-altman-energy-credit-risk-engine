# Interview Questions & Beginner-Friendly Answers

## Finance

**What is corporate credit risk?**
The risk that a company cannot pay back what it owes — interest or principal — in full and on time. It's separate from equity risk (the risk that a stock price falls); a company's debt can be perfectly safe even if its stock is volatile, and vice versa.

**Why is oil & gas credit risk interesting?**
Because it combines heavy debt-financed capital investment, large fixed-asset bases, and revenue directly exposed to a volatile global commodity price the company can't control — leverage and cash-flow volatility both matter a lot, at the same time, which is exactly what credit models are built to capture.

**What is Merton?**
A model (Robert Merton, 1974) that treats a company's equity as a call option on its assets, struck at the value of its debt. By observing equity's market value and volatility, you can back out an implied "distance" between the company's estimated asset value and its debt — that distance is the core credit-risk signal.

**Why can equity be viewed as a call option?**
Because shareholders only get paid after debt is serviced, and they have limited liability — they can't lose more than their investment. That "get the upside, capped downside at zero" payoff is exactly the payoff of a call option on firm assets struck at the debt level.

**What is Distance-to-Default?**
How many standard deviations of asset-value movement separate the current estimated asset value from the point where the company can no longer cover its debt. Higher = more cushion = the model considers the company safer.

**What is Altman Z-score?**
A weighted combination of accounting ratios (liquidity, cumulative profitability, operating profitability, leverage) originally built by Edward Altman in 1968 to statistically discriminate between companies that went bankrupt and those that didn't. There are several versions for different company types — this project uses the 1995 Emerging Markets version, chosen because it doesn't penalise capital-intensive businesses for being capital-intensive.

**Why use both models?**
Because they use completely different information — Merton uses live market prices and volatility (forward-looking, market's opinion); Altman uses the last audited financial statements (backward-looking, accounting record). When they agree, that's reassuring. When they disagree, that disagreement itself is informative — it tells you where the market and the accountants see the world differently.

**Why might they disagree?**
Classic case (seen in this project): a company had a genuinely bad accounting year (thin/negative margins), which drags Altman down, but the market has already priced in a recovery and equity volatility stayed low, so Merton stays strong. The market is forward-looking; the balance sheet is a rear-view mirror.

**Why use market equity instead of book equity in Merton?**
Because Merton's whole logic is options pricing, which requires the market's current view of value, not a historical accounting cost. Book equity would defeat the purpose of using a market-based model at all.

**Why is equity volatility important?**
Because it's the only piece of market information that turns equity's *price* into an estimate of the *underlying firm's* volatility (via the option-pricing relationship). This project found equity volatility is actually the single biggest driver of the model's output — bigger than debt or market-cap shocks of similar size.

**Why is debt treated as a default threshold?**
Because in the simplified Merton framework, if asset value falls below the face value of debt at the horizon date, the firm cannot fully repay — debt acts exactly like the option's strike price.

**What happens when debt increases?**
All else equal, the default threshold rises relative to asset value, so Distance-to-Default falls — this project confirmed that directionally for every company tested (a required "sanity check").

**What happens when equity volatility increases?**
Distance-to-Default falls, because a more volatile asset value is more likely to dip below the debt threshold at some point — also confirmed as a sanity check, and found to be the most powerful lever in this project's sensitivity analysis.

**What happens when oil-sector profitability falls?**
Interest coverage and Debt/EBITDA both worsen mechanically; if the shock is severe and sustained enough to also affect the market's view of the company (equity value, volatility), Merton DD falls too — this project modeled that combined effect explicitly in the "combined bear case" scenario.

**Why isn't Merton PD an actual probability of default?**
Because it's computed under the *risk-neutral* measure (assets assumed to grow at the risk-free rate, a mathematical convenience from option-pricing theory), not the real-world (*physical*) measure. Risk-neutral PDs are systematically higher than real-world ones because they embed a risk premium. This project never states a Merton PD as "the probability of default" — always "the model-implied risk-neutral default probability under these assumptions."

**What are the model limitations?**
For Merton: assumes one simple debt structure, ignores dividends, assumes smooth (lognormal) asset-value moves, and produces a risk-neutral not a physical PD. For Altman: it's a statistical fit calibrated on a different (mostly US, mostly older) sample, and its zones are a convention, not a law of nature. Both models here also rely on documented balance-sheet and market-data proxies given real data-access constraints — see `docs/limitations.md`.

**Why isn't Reliance directly comparable to IOC?**
Because Reliance is a diversified conglomerate (oil-to-chemicals, retail, telecom/digital) — its equity value and volatility reflect the whole group, not just its energy business, so its Merton profile in particular is not a clean read on "oil & gas credit risk" the way IOC's is.

## Technical

**How did you solve Merton?**
By treating it as a system of two nonlinear equations in two unknowns (asset value V, asset volatility σ_V) and solving with `scipy.optimize.root` (method `hybr`, with an `lm` fallback), starting from the standard initial guess V₀=E+D, σ_V0 = σ_E·E/(E+D), and explicitly checking convergence, residual size, and positivity of the solution before accepting it.

**Why scipy.optimize?**
Because the two Merton equations can't be solved in closed form for V and σ_V simultaneously — you need a numerical root-finder. `scipy.optimize.root` is a standard, well-tested implementation with multiple underlying algorithms, letting me fall back to a second method if the first doesn't converge, rather than relying on a single fragile solver.

**How did you estimate volatility?**
Using a current 1-year trailing equity volatility from a market-data vendor. I was not able to retrieve a full 5-year daily-return series for a truly independent per-year volatility estimate given the tools available in this environment — I documented that limitation explicitly rather than fabricate historical numbers, and used sensitivity analysis to show how much the results would move if volatility had actually differed historically.

**How did you handle missing data?**
Logged it, never invented it. Every missing field is listed by company and field in `data/metadata/data_dictionary.md` and `docs/limitations.md`, and downstream ratios that depend on a missing field are left as N/A rather than estimated silently.

**How did you validate convergence?**
Two layers: numerically (solver success flag, residual norm below a tolerance, positivity and finiteness of every output) and behaviourally (a set of directional sanity checks — e.g. debt up must mean DD down — run against the actual solved model, not assumed).

**How did you stress-test the model?**
Isolated shocks to profitability, debt, and equity value individually (per the brief's specified magnitudes), a combined "bear case" applying all of them plus a volatility shock simultaneously, and a reverse stress test that solves (via bisection) for the shock magnitude needed to cross a risk-tier boundary, capped at a plausible range rather than extrapolated to implausible multiples.

**How did you calculate Altman?**
Using the 1995 Z''-Score (Emerging Markets) formulation — four accounting ratios (working capital/total assets, retained earnings/total assets, EBIT/total assets, book equity/total liabilities) combined with published weights and a scaling constant, computed from the same cleaned financial-statement dataset used for the ratio engine.

**How did you compare the two models?**
By tiering each model's output independently (Merton DD into Low/Moderate/Elevated Risk; Altman Z'' into Safe/Grey/Distress Zone) and then comparing tiers, rather than trying to average two differently-scaled numbers together — and treating disagreements as a subject for investigation, not an error to reconcile away.

**How did you prevent data leakage?**
There's no train/test split in this project (it's not a predictive ML model), so "leakage" in the ML sense doesn't directly apply — but the analogous discipline I applied was keeping accounting-derived (Altman) and market-derived (Merton) inputs cleanly separated so that neither model's inputs silently incorporated the other's logic, which would have made the "do they agree" comparison meaningless by construction.

**Why did you avoid complex ML?**
Because the sample has 35 company-year observations and zero observed defaults — there's no positive class to learn from. Any classifier trained on that data would be fitting noise, and reporting an accuracy or AUC number from it would misrepresent the reliability of the result. Recognising when a dataset can't support a technique is itself part of doing the analysis correctly.
