"""
Streamlit + Plotly interactive dashboard for the Merton-Altman Energy Credit
Risk Engine. Run with:  streamlit run dashboard/app.py

Panels: company selector, business-model filter, credit KPIs, five-year
trends, Merton vs Altman comparison, interactive stress-test controls,
early warnings, and an evidence-based analyst interpretation.
"""
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from run_pipeline import build_all
from credit_score import score_all
from early_warning import run_early_warning
from stress_testing import merton_under_scenario
from altman_model import five_year_trend as altman_5yr_trend

st.set_page_config(page_title="Merton-Altman Energy Credit Risk Engine", layout="wide")

NAVY = "#1B2A4A"
TEAL = "#1F7A6C"
AMBER = "#C97B2E"
RED = "#B23A48"


@st.cache_data
def load_data():
    out = build_all()
    scored = score_all(out["comparison"])
    ratios25 = out["ratios"][out["ratios"]["fy"] == 2025]
    ew = run_early_warning(out["comparison"], ratios25, out["mkt"])
    alt_trend = altman_5yr_trend(out["altman"])
    return out, scored, ew, alt_trend


out, scored, ew, alt_trend = load_data()
comparison = out["comparison"]
universe = out["universe"]
fin = out["fin"]
ratios = out["ratios"]
altman = out["altman"]
merton_hist = out["merton_hist"]
mkt = out["mkt"]

st.title("Merton–Altman Energy Credit Risk Engine")
st.caption("Structural and Accounting-Based Credit Risk Assessment of Major Indian Oil & Gas Companies. "
           "Educational/portfolio project — not investment advice or a credit rating. See docs/limitations.md.")

# ---------------- Sidebar: filters ----------------
st.sidebar.header("Filters")
business_models = ["All"] + sorted(universe["business_model"].unique().tolist())
selected_model = st.sidebar.selectbox("Business Model", business_models)

companies_available = universe["company"].tolist() if selected_model == "All" else universe[universe["business_model"] == selected_model]["company"].tolist()
selected_company = st.sidebar.selectbox("Company", companies_available, index=companies_available.index("IOC") if "IOC" in companies_available else 0)

st.sidebar.markdown("---")
st.sidebar.header("Interactive Stress Scenario")
prof_shock = st.sidebar.slider("Profitability (EBITDA) shock (%)", -50, 0, 0, step=5)
debt_shock = st.sidebar.slider("Debt shock (%)", 0, 100, 0, step=5)
equity_shock = st.sidebar.slider("Equity market value shock (%)", -60, 0, 0, step=5)
vol_shock = st.sidebar.slider("Equity volatility shock (%)", 0, 100, 0, step=5)

# ---------------- KPI row ----------------
row = comparison[comparison["company"] == selected_company].iloc[0]
score_row = scored[scored["company"] == selected_company].iloc[0]
ew_row = ew[ew["company"] == selected_company].iloc[0]
uni_row = universe[universe["company"] == selected_company].iloc[0]

st.subheader(f"{uni_row['name']} ({selected_company}) — {uni_row['business_model']}")
if uni_row["peer_group"] == "Diversified Benchmark":
    st.warning("Reliance is a diversified conglomerate, not a pure-play oil & gas company — shown as a benchmark, not a directly comparable peer. See docs/limitations.md.")

kpi_cols = st.columns(7)
kpi_cols[0].metric("Merton DD", f"{row['merton_dd']:.2f}")
kpi_cols[1].metric("Merton PD (risk-neutral)", f"{row['merton_pd']*100:.4f}%")
kpi_cols[2].metric("Altman Z''", f"{row['altman_z_em']:.2f}", row["altman_zone"])
kpi_cols[3].metric("Debt/EBITDA", f"{row['debt_to_ebitda']:.2f}x")
kpi_cols[4].metric("Interest Coverage", f"{row['interest_coverage_ebit']:.2f}x")
kpi_cols[5].metric("Current Ratio (proxy)", f"{row['current_ratio_proxy']:.2f}x")
kpi_cols[6].metric("FCF/Debt", f"{row['fcf_to_debt']:.2%}")

badge_color = {"Green": "🟢", "Yellow": "🟡", "Orange": "🟠", "Red": "🔴"}
st.markdown(f"**Energy Credit Score:** {score_row['energy_credit_score']:.1f}/100 (peer rank {int(score_row['rank'])} of 7) &nbsp;&nbsp; "
            f"**Early Warning:** {badge_color.get(ew_row['warning_level'],'')} {ew_row['warning_level']} &nbsp;&nbsp; "
            f"**Model Signal:** {row['overall_signal']}")
if ew_row["n_triggers"] > 0:
    st.caption(f"Triggered by: {ew_row['triggered_metrics']}")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Five-Year Trend", "Model Comparison (All Peers)", "Stress Test", "Early Warnings", "Analyst Interpretation"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        d = altman[altman["company"] == selected_company].sort_values("fy")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["fy"], y=d["altman_z_em"], mode="lines+markers", name="Altman Z''", line=dict(color=NAVY, width=3)))
        fig.add_hline(y=5.85, line_dash="dash", line_color="grey", annotation_text="Safe")
        fig.add_hline(y=4.50, line_dash="dash", line_color="grey", annotation_text="Distress")
        fig.update_layout(title="Altman Z'' Trend, FY2021-FY2025", height=380)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        d2 = merton_hist[merton_hist["company"] == selected_company].sort_values("fy")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=d2["fy"], y=d2["dd_risk_neutral"], mode="lines+markers", name="Merton DD", line=dict(color=TEAL, width=3)))
        fig2.update_layout(title="Merton DD Trend (leverage-only view*), FY2021-FY2025", height=380)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("*Real, year-specific debt & risk-free rate; equity value/volatility held at current levels "
                   "(historical daily-return data limitation — see docs/limitations.md).")

    ratio_trend = ratios[ratios["company"] == selected_company][["fy", "debt_to_ebitda", "interest_coverage_ebit", "fcf_to_debt", "roe_pct"]]
    st.dataframe(ratio_trend.set_index("fy"), use_container_width=True)

with tab2:
    fig3 = px.scatter(comparison, x="altman_z_em", y="merton_dd", color="business_model", text="company",
                       size=[30]*len(comparison), title="Merton DD vs Altman Z'' — All Peers")
    fig3.update_traces(textposition="top center")
    fig3.add_vline(x=5.85, line_dash="dash", line_color="grey")
    fig3.add_hline(y=5.0, line_dash="dash", line_color="grey")
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(comparison.set_index("company"), use_container_width=True)
    st.dataframe(scored.set_index("company"), use_container_width=True)

with tab3:
    st.markdown("Adjust the sliders in the sidebar to apply an isolated or combined stress scenario to **" + selected_company + "**.")
    fin25 = fin[(fin["fy"] == 2025) & (fin["company"] == selected_company)].iloc[0]
    mkt_row = mkt[mkt["company"] == selected_company].iloc[0]

    E0 = mkt_row["market_cap_cr"]
    sigma0 = mkt_row["volatility_1y_pct"] / 100.0
    D0 = fin25["borrowings"]
    ebitda0 = fin25["operating_profit"]
    r0 = 0.0676

    E_s = E0 * (1 + equity_shock / 100)
    D_s = D0 * (1 + debt_shock / 100)
    sigma_s = sigma0 * (1 + vol_shock / 100)
    ebitda_s = ebitda0 * (1 + prof_shock / 100)
    ebit_s = ebitda_s - fin25["depreciation"]

    dd_base, pd_base, _ = merton_under_scenario(selected_company, E0, sigma0, D0, r0)
    dd_stress, pd_stress, conv = merton_under_scenario(selected_company, E_s, sigma_s, D_s, r0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Merton DD (base -> stressed)", f"{dd_stress:.2f}", f"{dd_stress - dd_base:+.2f}")
    c2.metric("Debt/EBITDA (base -> stressed)", f"{D_s/ebitda_s:.2f}x" if ebitda_s != 0 else "n/a", f"{(D_s/ebitda_s) - (D0/ebitda0):+.2f}x" if ebitda_s != 0 else "")
    c3.metric("Interest Coverage (base -> stressed)", f"{ebit_s/fin25['interest']:.2f}x", f"{(ebit_s/fin25['interest']) - (ebitda0-fin25['depreciation'])/fin25['interest']:+.2f}x")

    if not conv:
        st.error("Merton solver did not converge for this combination of shocks — try a less extreme scenario.")

with tab4:
    st.dataframe(ew.set_index("company")[["warning_level", "n_triggers", "triggered_metrics"]], use_container_width=True)
    st.bar_chart(ew.set_index("company")["n_triggers"])

with tab5:
    st.markdown(f"""
### Analyst Interpretation — {selected_company}

- **Structural view (Merton)**: Distance-to-Default of {row['merton_dd']:.2f} places {selected_company} in the
  **{row['merton_tier']}** tier under this project's convention, with a model-implied risk-neutral default
  probability of {row['merton_pd']*100:.4f}%. This is a market-observed, forward-looking view, not a rating.
- **Accounting view (Altman)**: Z''-Score of {row['altman_z_em']:.2f} places it in the **{row['altman_zone']}**,
  based on FY2025 audited financials.
- **Model signal**: {row['overall_signal']}. Where the two models disagree, this reflects genuinely different
  information — Merton is driven by current market pricing and volatility, Altman by the trailing accounting
  record. See `docs/methodology.md` §7 for the full disagreement-analysis discussion.
- **Early warning**: {ew_row['warning_level']} ({ew_row['n_triggers']} indicator(s) triggered: {ew_row['triggered_metrics']}).
- **Energy Credit Score**: {score_row['energy_credit_score']:.1f}/100, peer rank {int(score_row['rank'])} of 7
  (project-defined composite — see docs/assumptions.md §12).

*This is a model output conditional on stated assumptions, not a credit rating or investment recommendation.*
""")

st.markdown("---")
st.caption("Merton–Altman Energy Credit Risk Engine. Data sources: Screener.in, Tickertape.in, FRED (INDIRLTLT01STM). "
           "See docs/methodology.md, docs/assumptions.md, docs/limitations.md.")
