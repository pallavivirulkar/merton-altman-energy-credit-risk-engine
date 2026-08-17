"""
visualization.py
=================
Generates the full chart set (Section 42) as PNG files in outputs/charts/.
Uses a consistent, muted, colour-blind-conscious finance-style palette.
"""
from __future__ import annotations
import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, os.path.dirname(__file__))

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ---- palette (muted, professional, consistent across all charts) ----
NAVY = "#1B2A4A"
TEAL = "#1F7A6C"
AMBER = "#C97B2E"
RED = "#B23A48"
GREY = "#8A94A6"
LIGHT_GREY = "#E4E7EC"
BG = "#FFFFFF"
PALETTE = [NAVY, TEAL, AMBER, RED, "#5B6B8C", "#7FB3A3", "#D9A24B"]
BUSINESS_COLORS = {
    "Upstream (E&P)": NAVY,
    "Refining & Marketing (Downstream)": AMBER,
    "Gas Transmission & Distribution": TEAL,
    "Diversified (O2C, Retail, Digital)": RED,
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": GREY,
    "axes.labelcolor": NAVY,
    "text.color": NAVY,
    "xtick.color": NAVY,
    "ytick.color": NAVY,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "axes.grid": True,
    "grid.color": LIGHT_GREY,
    "grid.linewidth": 0.7,
    "axes.axisbelow": True,
})


def _save(fig, name):
    path = os.path.join(CHARTS_DIR, name)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {path}")


def chart_dd_ranking(comparison):
    df = comparison.sort_values("merton_dd")
    colors = [BUSINESS_COLORS.get(bm, GREY) for bm in df["business_model"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df["company"], df["merton_dd"], color=colors)
    ax.set_xlabel("Merton Distance-to-Default (higher = lower model-implied risk)")
    ax.set_title("Merton Distance-to-Default — Peer Ranking (current snapshot)", fontweight="bold", loc="left")
    for i, v in enumerate(df["merton_dd"]):
        ax.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=9)
    _save(fig, "01_merton_dd_ranking.png")


def chart_pd_ranking(comparison):
    df = comparison.sort_values("merton_pd", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df["company"], df["merton_pd"] * 100, color=RED)
    ax.set_xlabel("Model-implied risk-neutral default probability (%) — NOT an actual PD")
    ax.set_title("Merton Model-Implied Default Probability — Peer Ranking", fontweight="bold", loc="left")
    ax.set_xscale("symlog", linthresh=0.001)
    for i, v in enumerate(df["merton_pd"] * 100):
        ax.text(v, i, f"  {v:.4f}%", va="center", fontsize=9)
    _save(fig, "02_merton_pd_ranking.png")


def chart_altman_ranking(comparison):
    df = comparison.sort_values("altman_z_em")
    colors = [RED if z < 4.5 else (AMBER if z < 5.85 else TEAL) for z in df["altman_z_em"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df["company"], df["altman_z_em"], color=colors)
    ax.axvline(4.5, color=GREY, linestyle="--", linewidth=1)
    ax.axvline(5.85, color=GREY, linestyle="--", linewidth=1)
    ax.text(4.5, -0.7, "Distress", fontsize=8, color=GREY, ha="center")
    ax.text(5.85, -0.7, "Safe", fontsize=8, color=GREY, ha="center")
    ax.set_xlabel("Altman Z''-Score (Emerging Markets, modified)")
    ax.set_title("Altman Z''-Score — Peer Ranking (FY2025)", fontweight="bold", loc="left")
    for i, v in enumerate(df["altman_z_em"]):
        ax.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=9)
    _save(fig, "03_altman_z_ranking.png")


def chart_dd_vs_z(comparison):
    fig, ax = plt.subplots(figsize=(7.5, 6))
    colors = [BUSINESS_COLORS.get(bm, GREY) for bm in comparison["business_model"]]
    ax.scatter(comparison["altman_z_em"], comparison["merton_dd"], s=180, c=colors, edgecolor="white", linewidth=1.2, zorder=3)
    for _, row in comparison.iterrows():
        ax.annotate(row["company"], (row["altman_z_em"], row["merton_dd"]), textcoords="offset points", xytext=(8, 4), fontsize=9)
    ax.axvline(5.85, color=GREY, linestyle="--", linewidth=1)
    ax.axhline(5.0, color=GREY, linestyle="--", linewidth=1)
    ax.set_xlabel("Altman Z''-Score (accounting-based)")
    ax.set_ylabel("Merton Distance-to-Default (market-based)")
    ax.set_title("Merton DD vs Altman Z'' — Model Agreement Map", fontweight="bold", loc="left")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=10, label=k) for k, c in BUSINESS_COLORS.items()]
    ax.legend(handles=handles, fontsize=8, loc="lower right", frameon=False)
    _save(fig, "04_dd_vs_altman_scatter.png")


def chart_debt_ebitda(comparison):
    df = comparison.sort_values("debt_to_ebitda")
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [RED if v > 3.5 else TEAL for v in df["debt_to_ebitda"]]
    ax.barh(df["company"], df["debt_to_ebitda"], color=colors)
    ax.axvline(3.5, color=GREY, linestyle="--", linewidth=1)
    ax.set_xlabel("Debt / EBITDA (x)")
    ax.set_title("Debt/EBITDA — Peer Comparison (FY2025)", fontweight="bold", loc="left")
    for i, v in enumerate(df["debt_to_ebitda"]):
        ax.text(v + 0.05, i, f"{v:.2f}x", va="center", fontsize=9)
    _save(fig, "05_debt_ebitda_comparison.png")


def chart_interest_coverage(comparison):
    df = comparison.sort_values("interest_coverage_ebit")
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [RED if v < 3 else TEAL for v in df["interest_coverage_ebit"]]
    ax.barh(df["company"], df["interest_coverage_ebit"], color=colors)
    ax.axvline(3.0, color=GREY, linestyle="--", linewidth=1)
    ax.set_xlabel("Interest Coverage = EBIT / Interest (x)")
    ax.set_title("Interest Coverage — Peer Comparison (FY2025)", fontweight="bold", loc="left")
    for i, v in enumerate(df["interest_coverage_ebit"]):
        ax.text(v + 0.1, i, f"{v:.2f}x", va="center", fontsize=9)
    _save(fig, "06_interest_coverage_comparison.png")


def chart_five_year_dd_trend(merton_hist):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    companies = merton_hist["company"].unique()
    for i, c in enumerate(companies):
        d = merton_hist[merton_hist["company"] == c].sort_values("fy")
        ax.plot(d["fy"], d["dd_risk_neutral"], marker="o", label=c, color=PALETTE[i % len(PALETTE)], linewidth=2)
    ax.set_xlabel("Fiscal Year")
    ax.set_ylabel("Merton Distance-to-Default (leverage-only decomposition)")
    ax.set_title("Five-Year Merton DD Trend — Leverage-Only View*", fontweight="bold", loc="left")
    ax.set_xticks([2021, 2022, 2023, 2024, 2025])
    ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.15), frameon=False)
    fig.text(0.01, -0.02, "*Uses real, year-specific Debt & risk-free rate; equity value/volatility held at current levels (data limitation — see docs/limitations.md). Isolates the leverage-driven component only.",
              fontsize=7.5, color=GREY)
    _save(fig, "07_five_year_dd_trend.png")


def chart_five_year_altman_trend(altman_df):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    companies = altman_df["company"].unique()
    for i, c in enumerate(companies):
        d = altman_df[altman_df["company"] == c].sort_values("fy")
        ax.plot(d["fy"], d["altman_z_em"], marker="o", label=c, color=PALETTE[i % len(PALETTE)], linewidth=2)
    ax.axhline(5.85, color=GREY, linestyle="--", linewidth=0.8)
    ax.axhline(4.5, color=GREY, linestyle="--", linewidth=0.8)
    ax.set_xlabel("Fiscal Year")
    ax.set_ylabel("Altman Z''-Score")
    ax.set_title("Five-Year Altman Z''-Score Trend (fully real, accounting-based)", fontweight="bold", loc="left")
    ax.set_xticks([2021, 2022, 2023, 2024, 2025])
    ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.15), frameon=False)
    _save(fig, "08_five_year_altman_trend.png")


def chart_risk_heatmap(comparison):
    metrics = ["merton_dd", "altman_z_em", "debt_to_ebitda", "interest_coverage_ebit", "current_ratio_proxy", "fcf_to_debt"]
    labels = ["Merton DD", "Altman Z''", "Debt/EBITDA\n(inverted)", "Interest\nCoverage", "Current Ratio\n(proxy)", "FCF/Debt"]
    df = comparison.set_index("company")[metrics].copy()
    df["debt_to_ebitda"] = -df["debt_to_ebitda"]  # invert so higher = better everywhere
    norm = (df - df.min()) / (df.max() - df.min())
    fig, ax = plt.subplots(figsize=(8, 5.5))
    im = ax.imshow(norm.values, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks(range(len(norm.index)))
    ax.set_yticklabels(norm.index, fontsize=9)
    for i in range(norm.shape[0]):
        for j in range(norm.shape[1]):
            ax.text(j, i, f"{df.values[i, j]:.2f}" if labels[j] != "Debt/EBITDA\n(inverted)" else f"{-df.values[i, j]:.2f}",
                    ha="center", va="center", fontsize=8, color="black")
    ax.set_title("Credit Risk Heatmap — Normalised Across Peers (green = stronger)", fontweight="bold", loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Normalised strength (0=weakest peer, 1=strongest peer)")
    _save(fig, "09_credit_risk_heatmap.png")


def chart_business_model_comparison(comparison):
    grp = comparison.groupby("business_model").agg(
        avg_dd=("merton_dd", "mean"), avg_z=("altman_z_em", "mean"),
        avg_debt_ebitda=("debt_to_ebitda", "mean"), n=("company", "count")).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar(grp["business_model"], grp["avg_dd"], color=[BUSINESS_COLORS.get(b, GREY) for b in grp["business_model"]])
    axes[0].set_title("Avg Merton DD by Business Model", fontsize=10, fontweight="bold")
    axes[0].tick_params(axis="x", rotation=30, labelsize=7.5)
    axes[1].bar(grp["business_model"], grp["avg_z"], color=[BUSINESS_COLORS.get(b, GREY) for b in grp["business_model"]])
    axes[1].set_title("Avg Altman Z'' by Business Model", fontsize=10, fontweight="bold")
    axes[1].tick_params(axis="x", rotation=30, labelsize=7.5)
    fig.suptitle("Energy Business-Model Comparison", fontweight="bold", x=0.02, ha="left")
    _save(fig, "10_business_model_comparison.png")


def chart_stress_impact(bear_case_df):
    df = bear_case_df.sort_values("dd_change")
    fig, ax = plt.subplots(figsize=(8.5, 5))
    y = np.arange(len(df))
    ax.barh(y, df["dd_base"], color=LIGHT_GREY, label="Base DD (FY2025)")
    ax.barh(y, df["dd_bear"], color=RED, alpha=0.85, label="Bear Case DD")
    ax.set_yticks(y)
    ax.set_yticklabels(df["company"])
    ax.set_xlabel("Merton Distance-to-Default")
    ax.set_title("Combined Bear Case — Stress-Test Impact on Merton DD", fontweight="bold", loc="left")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, "11_stress_test_impact.png")


def chart_sensitivity_heatmap(sens_df):
    pct_drivers = sens_df[sens_df["driver"].isin(["Equity Volatility", "Debt", "Equity Value"])]
    piv = pct_drivers.pivot_table(index="company", columns=["driver", "shock"], values="dd_change_from_base")
    # collapse to driver-level average absolute impact for a clean heatmap
    impact = pct_drivers.groupby(["company", "driver"])["dd_change_from_base"].apply(lambda s: s.abs().mean()).unstack()
    fig, ax = plt.subplots(figsize=(7, 5.5))
    im = ax.imshow(impact.values, cmap="OrRd", aspect="auto")
    ax.set_xticks(range(len(impact.columns)))
    ax.set_xticklabels(impact.columns, fontsize=9)
    ax.set_yticks(range(len(impact.index)))
    ax.set_yticklabels(impact.index, fontsize=9)
    for i in range(impact.shape[0]):
        for j in range(impact.shape[1]):
            ax.text(j, i, f"{impact.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Sensitivity Heatmap — Avg |ΔDD| Across ±10/25/50% Shocks", fontweight="bold", loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Average |change in DD|")
    _save(fig, "12_sensitivity_heatmap.png")


def chart_company_profile(company, comparison, altman_df, merton_hist, ew_row):
    row = comparison[comparison["company"] == company].iloc[0]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    fig.suptitle(f"{row['name']} — Credit Profile", fontweight="bold", fontsize=13, x=0.02, ha="left")

    # panel 1: Altman trend
    d = altman_df[altman_df["company"] == company].sort_values("fy")
    axes[0, 0].plot(d["fy"], d["altman_z_em"], marker="o", color=NAVY, linewidth=2)
    axes[0, 0].axhline(5.85, color=GREY, ls="--", lw=0.8)
    axes[0, 0].axhline(4.5, color=GREY, ls="--", lw=0.8)
    axes[0, 0].set_title("Altman Z'' Trend (FY21-FY25)", fontsize=10)

    # panel 2: Merton DD leverage-only trend
    d2 = merton_hist[merton_hist["company"] == company].sort_values("fy")
    axes[0, 1].plot(d2["fy"], d2["dd_risk_neutral"], marker="o", color=TEAL, linewidth=2)
    axes[0, 1].set_title("Merton DD Trend (leverage-only view)", fontsize=10)

    # panel 3: key ratios bar
    metrics = ["debt_to_ebitda", "interest_coverage_ebit", "current_ratio_proxy", "fcf_to_debt"]
    vals = [row[m] for m in metrics]
    axes[1, 0].bar(["Debt/\nEBITDA", "Int.\nCoverage", "Current\nRatio", "FCF/\nDebt"], vals, color=PALETTE[:4])
    axes[1, 0].set_title("Key Credit Ratios (FY2025)", fontsize=10)

    # panel 4: early warning summary text
    axes[1, 1].axis("off")
    lvl = ew_row["warning_level"] if ew_row is not None else "N/A"
    txt = (f"Merton DD: {row['merton_dd']:.2f}\n"
           f"Merton PD (risk-neutral): {row['merton_pd']*100:.4f}%\n"
           f"Altman Z'': {row['altman_z_em']:.2f} ({row['altman_zone']})\n"
           f"Early Warning Level: {lvl}\n"
           f"Overall Signal: {row['overall_signal']}")
    axes[1, 1].text(0, 0.9, txt, fontsize=10.5, va="top", family="monospace")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _save(fig, f"13_company_profile_{company}.png")


def chart_agreement_matrix(comparison):
    fig, ax = plt.subplots(figsize=(7, 5.5))
    tiers = ["Elevated Risk", "Moderate Risk", "Low Risk"]
    grid = pd.DataFrame(0, index=tiers, columns=tiers)
    for _, row in comparison.iterrows():
        grid.loc[row["merton_tier"], row["altman_tier"]] += 1
    im = ax.imshow(grid.values, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_xticklabels(tiers, fontsize=9)
    ax.set_yticks(range(3)); ax.set_yticklabels(tiers, fontsize=9)
    ax.set_xlabel("Altman Tier")
    ax.set_ylabel("Merton Tier")
    for i in range(3):
        for j in range(3):
            v = grid.values[i, j]
            names = comparison[(comparison["merton_tier"] == tiers[i]) & (comparison["altman_tier"] == tiers[j])]["company"].tolist()
            label = f"{v}\n" + "\n".join(names) if v else ""
            ax.text(j, i, label, ha="center", va="center", fontsize=8, color="black" if v < 3 else "white")
    ax.set_title("Model Agreement / Disagreement Matrix", fontweight="bold", loc="left")
    _save(fig, "14_agreement_disagreement_matrix.png")


def generate_all():
    from run_pipeline import build_all
    from stress_testing import combined_bear_case
    from sensitivity_analysis import sensitivity_table
    from early_warning import run_early_warning

    out = build_all()
    fin25 = out["fin"][out["fin"]["fy"] == 2025]
    bear = combined_bear_case(fin25, out["mkt"])
    inputs = out["merton_current"][["company", "E", "sigma_E", "D", "r"]]
    sens = sensitivity_table(inputs)
    ratios25 = out["ratios"][out["ratios"]["fy"] == 2025]
    ew = run_early_warning(out["comparison"], ratios25, out["mkt"])

    chart_dd_ranking(out["comparison"])
    chart_pd_ranking(out["comparison"])
    chart_altman_ranking(out["comparison"])
    chart_dd_vs_z(out["comparison"])
    chart_debt_ebitda(out["comparison"])
    chart_interest_coverage(out["comparison"])
    chart_five_year_dd_trend(out["merton_hist"])
    chart_five_year_altman_trend(out["altman"])
    chart_risk_heatmap(out["comparison"])
    chart_business_model_comparison(out["comparison"])
    chart_stress_impact(bear)
    chart_sensitivity_heatmap(sens)
    for c in out["comparison"]["company"]:
        ew_row = ew[ew["company"] == c].iloc[0] if c in ew["company"].values else None
        chart_company_profile(c, out["comparison"], out["altman"], out["merton_hist"], ew_row)
    chart_agreement_matrix(out["comparison"])
    print("All charts generated.")


if __name__ == "__main__":
    generate_all()
