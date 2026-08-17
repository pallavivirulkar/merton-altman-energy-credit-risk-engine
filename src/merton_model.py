"""
merton_model.py
================
Market-based structural credit risk: the Merton (1974) model.

INTUITION (plain language, before the maths)
----------------------------------------------
A company's assets are financed by a mix of debt and equity:
    Assets (V) = Debt (D) + Equity (E)

Merton's insight: equity behaves like a CALL OPTION on the firm's assets,
struck at the face value of debt, D, at horizon T. Shareholders only get
paid after debt is repaid - so equity holders effectively own the "upside"
above D, capped below at zero (limited liability). If, at T, the estimated
value of assets V is comfortably above D, equity is valuable and the firm
can meet its obligations. If V falls below D, the firm is - under this
simplified model - economically unable to fully cover its debt.

Simple hypothetical example: a company has assets worth Rs. 100 and owes
Rs. 60 of debt due in one year. If asset value is volatile (say the assets
could plausibly range between Rs. 40 and Rs. 160 a year from now), there is
some chance the assets end up worth less than Rs. 60 - at that point,
shareholders would rationally not "exercise their option" (i.e. would not
be able to fully repay lenders). The Merton model turns "how far away is
that bad outcome" into a single number: the Distance-to-Default.

We never observe V (asset value) or its volatility (sigma_V) directly -
only market equity value E, equity volatility sigma_E, and the face value
of debt D are observable. So we SOLVE for V and sigma_V using the two
option-pricing relationships below.

THE TWO EQUATIONS (solved simultaneously)
--------------------------------------------
    E = V * N(d1) - D * exp(-r*T) * N(d2)              ... (1) Black-Scholes call
    sigma_E * E = N(d1) * sigma_V * V                    ... (2) Ito's lemma link

    d1 = [ln(V/D) + (r + 0.5*sigma_V**2) * T] / (sigma_V * sqrt(T))
    d2 = d1 - sigma_V * sqrt(T)

SOLVER
-------
scipy.optimize.root (method='hybr' with a fallback to 'lm') is used to solve
the 2x2 nonlinear system for (V, sigma_V), starting from the standard
initial guess V0 = E + D, sigma_V0 = sigma_E * E / (E + D). Convergence is
explicitly checked (residual norm, solver success flag, positivity of V and
sigma_V) - see validate_solution() and src/validation.py. No output is
accepted without these checks passing.

RISK-NEUTRAL vs PHYSICAL - DO NOT CONFLATE (Section 12/13 requirement)
--------------------------------------------------------------------------
Because equation (1) is the risk-neutral Black-Scholes pricing formula, the
d2 that falls out of solving it uses the RISK-FREE RATE r as the assumed
asset drift. The resulting

    DD_risk_neutral = d2
    PD_risk_neutral = N(-d2)

is a RISK-NEUTRAL, model-implied quantity. It answers "what asset-value
shortfall probability is consistent with option-pricing theory and the
observed inputs" - it is NOT a forecast of the physical (real-world)
probability that the company actually defaults, and it is NOT equivalent to
a credit-rating agency's default probability. Risk-neutral PDs are
systematically HIGHER than physical PDs because they embed a risk premium.

As a clearly-labeled SUPPLEMENTARY exercise only (never the headline number),
this module also reports an illustrative "physical" distance-to-default that
replaces r with mu = r + ERP (ERP = India total equity risk premium, ~7.0%,
Damodaran-style estimate, Jan-2026 vintage - see docs/assumptions.md). This
is a simplification (it does not estimate a firm-specific beta on assets) and
is explicitly flagged as illustrative in every output table and chart.

NEVER report either PD as "the probability company X will default." Always:
"Under the stated Merton assumptions, the model-implied default probability
is X%."
"""

from __future__ import annotations
import numpy as np
from scipy.stats import norm
from scipy.optimize import root
from dataclasses import dataclass, asdict


@dataclass
class MertonResult:
    company: str
    period: str
    E: float          # market value of equity
    sigma_E: float     # equity volatility (annualised, decimal)
    D: float           # face value of debt (Merton default point)
    r: float           # risk-free rate (decimal)
    T: float           # horizon (years)
    V: float            # solved asset value
    sigma_V: float       # solved asset volatility
    d1: float
    d2: float
    dd_risk_neutral: float
    pd_risk_neutral: float
    mu_physical: float | None
    dd_physical: float | None
    pd_physical: float | None
    converged: bool
    residual_norm: float
    solver_message: str


def _equations(x, E, sigma_E, D, r, T):
    V, sigma_V = x
    if V <= 0 or sigma_V <= 0:
        return [1e10, 1e10]  # push solver away from invalid region
    d1 = (np.log(V / D) + (r + 0.5 * sigma_V ** 2) * T) / (sigma_V * np.sqrt(T))
    d2 = d1 - sigma_V * np.sqrt(T)
    eq1 = V * norm.cdf(d1) - D * np.exp(-r * T) * norm.cdf(d2) - E
    eq2 = norm.cdf(d1) * sigma_V * V - sigma_E * E
    return [eq1, eq2]


def solve_merton(E: float, sigma_E: float, D: float, r: float, T: float = 1.0) -> tuple[float, float, bool, float, str]:
    """Solve the 2x2 Merton system for (V, sigma_V). Returns (V, sigma_V, converged, residual_norm, message)."""
    if D <= 0 or E <= 0 or sigma_E <= 0:
        return np.nan, np.nan, False, np.nan, "Invalid input: D, E and sigma_E must all be positive."

    V0 = E + D
    sigmaV0 = sigma_E * E / (E + D)
    x0 = [V0, sigmaV0]

    sol = root(_equations, x0, args=(E, sigma_E, D, r, T), method="hybr")
    if not sol.success or sol.x[0] <= 0 or sol.x[1] <= 0:
        # fallback solver
        sol2 = root(_equations, x0, args=(E, sigma_E, D, r, T), method="lm")
        if sol2.success and sol2.x[0] > 0 and sol2.x[1] > 0:
            sol = sol2

    V, sigma_V = sol.x
    residual = float(np.linalg.norm(_equations([V, sigma_V], E, sigma_E, D, r, T)))
    converged = bool(sol.success) and V > 0 and sigma_V > 0 and residual < 1e-3 * max(1.0, E)
    return float(V), float(sigma_V), converged, residual, str(sol.message)


def run_merton(company: str, period: str, E: float, sigma_E: float, D: float, r: float, T: float = 1.0,
               erp: float | None = 0.07) -> MertonResult:
    V, sigma_V, converged, residual, msg = solve_merton(E, sigma_E, D, r, T)

    if converged:
        d1 = (np.log(V / D) + (r + 0.5 * sigma_V ** 2) * T) / (sigma_V * np.sqrt(T))
        d2 = d1 - sigma_V * np.sqrt(T)
        dd_rn = d2
        pd_rn = float(norm.cdf(-d2))

        dd_phys = pd_phys = mu = None
        if erp is not None:
            mu = r + erp
            d1_phys = (np.log(V / D) + (mu + 0.5 * sigma_V ** 2) * T) / (sigma_V * np.sqrt(T))
            dd_phys = d1_phys - sigma_V * np.sqrt(T)
            pd_phys = float(norm.cdf(-dd_phys))
    else:
        d1 = d2 = dd_rn = pd_rn = np.nan
        dd_phys = pd_phys = mu = np.nan

    return MertonResult(
        company=company, period=period, E=E, sigma_E=sigma_E, D=D, r=r, T=T,
        V=V, sigma_V=sigma_V, d1=float(d1), d2=float(d2),
        dd_risk_neutral=float(dd_rn), pd_risk_neutral=pd_rn,
        mu_physical=mu, dd_physical=dd_phys, pd_physical=pd_phys,
        converged=converged, residual_norm=residual, solver_message=msg,
    )


def run_merton_batch(rows: list[dict], T: float = 1.0, erp: float = 0.07) -> "pd.DataFrame":
    import pandas as pd
    results = []
    for row in rows:
        res = run_merton(
            company=row["company"], period=row.get("period", "current"),
            E=row["E"], sigma_E=row["sigma_E"], D=row["D"], r=row["r"], T=T, erp=erp,
        )
        results.append(asdict(res))
    return pd.DataFrame(results)


if __name__ == "__main__":
    # Quick sanity example matching the hypothetical in the docstring
    res = run_merton("EXAMPLE", "illustrative", E=40, sigma_E=0.60, D=60, r=0.0668, T=1.0)
    print(res)
