"""
Visualisation module for NZ car theft base-rate analysis.

Generates publication-quality figures that expose the base-rate fallacy
and tell the complete data story.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

from load_data import build_merged_dataset
from base_rate_analysis import compute_base_rate_metrics
from confound_model import (
    compute_age_risk_score,
    compute_security_score,
    compute_parts_demand_proxy,
    compute_geographic_risk,
    compute_composite_vulnerability,
    compute_residual_targeting,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Style configuration
COLORS = {
    "aqua_highlight": "#E63946",
    "bar_default": "#457B9D",
    "bar_secondary": "#A8DADC",
    "background": "#F1FAEE",
    "text": "#1D3557",
    "grid": "#CCCCCC",
}


def setup_style():
    """Configure matplotlib for clean, publication-style figures."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
    })


def plot_raw_vs_adjusted_ranking(df: pd.DataFrame):
    """
    Bump chart showing how models shift between raw and adjusted rankings.
    This is the money plot — it visualises the base-rate correction.
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    # Select top models by either ranking
    top = df.nsmallest(12, "rank_adjusted").copy()
    top = top.sort_values("rank_adjusted")

    for _, row in top.iterrows():
        color = (COLORS["aqua_highlight"] if row["model"] == "Toyota Aqua"
                 else COLORS["bar_default"])
        alpha = 1.0 if row["model"] == "Toyota Aqua" else 0.5
        lw = 3 if row["model"] == "Toyota Aqua" else 1.5

        ax.plot(
            [0, 1],
            [row["rank_raw"], row["rank_adjusted"]],
            color=color, alpha=alpha, linewidth=lw, marker="o",
            markersize=8, zorder=3,
        )

        ax.text(-0.05, row["rank_raw"], row["model"],
                ha="right", va="center", fontsize=9,
                color=color, fontweight="bold" if alpha == 1 else "normal")
        ax.text(1.05, row["rank_adjusted"], row["model"],
                ha="left", va="center", fontsize=9,
                color=color, fontweight="bold" if alpha == 1 else "normal")

    ax.set_xlim(-0.5, 1.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Raw Rank\n(theft count)", "Adjusted Rank\n(per 1,000 vehicles)"],
                       fontsize=12, fontweight="bold")
    ax.invert_yaxis()
    ax.set_ylabel("Rank (1 = highest)")
    ax.set_title("How Rankings Change After Base-Rate Correction",
                 pad=20)
    ax.grid(False)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_raw_vs_adjusted_ranking.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 01_raw_vs_adjusted_ranking.png")


def plot_theft_rate_bar_chart(df: pd.DataFrame):
    """Horizontal bar chart of theft rate per 1,000 vehicles."""
    fig, ax = plt.subplots(figsize=(10, 8))

    top = df.nsmallest(15, "rank_adjusted").sort_values(
        "theft_rate_per_1000", ascending=True
    )

    colors = [
        COLORS["aqua_highlight"] if m == "Toyota Aqua"
        else COLORS["bar_default"]
        for m in top["model"]
    ]

    bars = ax.barh(top["model"], top["theft_rate_per_1000"],
                   color=colors, edgecolor="white", linewidth=0.5)

    for bar, rate in zip(bars, top["theft_rate_per_1000"]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{rate:.1f}", va="center", fontsize=9,
                color=COLORS["text"])

    ax.set_xlabel("Annual Theft Rate per 1,000 Registered Vehicles")
    ax.set_title("Theft Risk by Model (Fleet-Adjusted)")
    ax.axvline(x=df["theft_rate_per_1000"].median(), color=COLORS["grid"],
               linestyle="--", alpha=0.7, label="Median")
    ax.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_theft_rate_per_1000.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 02_theft_rate_per_1000.png")


def plot_fleet_vs_thefts_scatter(df: pd.DataFrame):
    """
    Scatter plot: fleet size vs theft count.
    Shows whether the relationship is proportional (base-rate only)
    or if some models deviate (genuine targeting).
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Proportional line (H0: uniform risk)
    total_thefts = df["thefts_annual_est"].sum()
    total_fleet = df["fleet_registered"].sum()
    uniform_rate = total_thefts / total_fleet

    x_line = np.linspace(0, df["fleet_registered"].max() * 1.1, 100)
    y_line = uniform_rate * x_line
    ax.plot(x_line, y_line, "--", color=COLORS["grid"], linewidth=2,
            label="Expected if uniform risk", zorder=1)

    # Points
    for _, row in df.iterrows():
        is_aqua = row["model"] == "Toyota Aqua"
        color = COLORS["aqua_highlight"] if is_aqua else COLORS["bar_default"]
        size = 120 if is_aqua else 60
        zorder = 5 if is_aqua else 3

        ax.scatter(row["fleet_registered"], row["thefts_annual_est"],
                   c=color, s=size, zorder=zorder, edgecolors="white",
                   linewidth=1)

        # Label significant models
        if is_aqua or row["theft_fleet_ratio"] > 3 or row["rank_raw"] <= 3:
            offset = (10, 5) if not is_aqua else (10, 10)
            ax.annotate(row["model"],
                        (row["fleet_registered"], row["thefts_annual_est"]),
                        textcoords="offset points", xytext=offset,
                        fontsize=8, color=color,
                        fontweight="bold" if is_aqua else "normal")

    ax.set_xlabel("Fleet Size (registered vehicles)")
    ax.set_ylabel("Estimated Annual Thefts")
    ax.set_title("Fleet Size vs Theft Count\n"
                 "Points above the line = disproportionately stolen")
    ax.legend(loc="upper left")

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k"
    ))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_fleet_vs_thefts_scatter.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 03_fleet_vs_thefts_scatter.png")


def plot_theft_fleet_ratio(df: pd.DataFrame):
    """
    Bar chart of theft-to-fleet ratio.
    Values > 1 mean the model is stolen more than its fleet share predicts.
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    top = df.nsmallest(15, "rank_adjusted").sort_values(
        "theft_fleet_ratio", ascending=True
    )

    colors = [
        COLORS["aqua_highlight"] if row["theft_fleet_ratio"] > 1
        else COLORS["bar_secondary"]
        for _, row in top.iterrows()
    ]
    colors = [
        COLORS["aqua_highlight"] if m == "Toyota Aqua"
        else (COLORS["bar_default"] if r > 1 else COLORS["bar_secondary"])
        for m, r in zip(top["model"], top["theft_fleet_ratio"])
    ]

    ax.barh(top["model"], top["theft_fleet_ratio"],
            color=colors, edgecolor="white")

    ax.axvline(x=1.0, color=COLORS["text"], linewidth=2, linestyle="-",
               label="Expected ratio (1.0)")

    ax.set_xlabel("Theft-to-Fleet Ratio")
    ax.set_title("Disproportionality Index\n"
                 ">1.0 = stolen more than fleet share predicts")
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "04_theft_fleet_ratio.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 04_theft_fleet_ratio.png")


def plot_confound_heatmap(df: pd.DataFrame):
    """Heatmap of vulnerability factors by model."""
    fig, ax = plt.subplots(figsize=(12, 8))

    factors = ["age_vulnerability", "security_vulnerability",
               "geo_risk_score", "parts_demand_proxy"]
    labels = ["Vehicle Age", "Security\n(lack of)", "Auckland\nConcentration",
              "Parts Demand"]

    top = df.nsmallest(15, "rank_adjusted").sort_values(
        "composite_vulnerability", ascending=False
    )

    data = top[factors].values
    models = top["model"].values

    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models, fontsize=10)

    # Annotate cells
    for i in range(len(models)):
        for j in range(len(factors)):
            color = "white" if data[i, j] > 0.6 else "black"
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center",
                    color=color, fontsize=9)

    ax.set_title("Vulnerability Factor Heatmap")
    fig.colorbar(im, ax=ax, label="Risk Score (0-1)", shrink=0.8)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "05_confound_heatmap.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 05_confound_heatmap.png")


def plot_ami_insurance_comparison(df_ami: pd.DataFrame):
    """
    Compare AMI's per-1,000-insured rates (Aqua vs Corolla).
    This is the most direct evidence of disproportionate targeting.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    models = ["Toyota Aqua", "Toyota Corolla"]
    rates = [54, 15]
    colors_bar = [COLORS["aqua_highlight"], COLORS["bar_default"]]

    bars = ax.bar(models, rates, color=colors_bar, width=0.5,
                  edgecolor="white", linewidth=2)

    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                str(rate), ha="center", fontsize=14, fontweight="bold",
                color=COLORS["text"])

    ax.set_ylabel("Theft Claims per 1,000 Insured Vehicles")
    ax.set_title("AMI Insurance: Theft Rate Comparison (2025)\n"
                 "Aqua rate is 3.6x the Corolla's")
    ax.set_ylim(0, 65)
    ax.yaxis.grid(True, alpha=0.3)

    # Add ratio annotation
    ax.annotate("3.6×", xy=(0.5, 35), fontsize=24,
                fontweight="bold", color=COLORS["aqua_highlight"],
                ha="center")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "06_ami_rate_comparison.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 06_ami_rate_comparison.png")


def plot_regional_comparison(regional_df: pd.DataFrame):
    """
    Grouped bar chart comparing theft rates across Auckland and Canterbury
    for top models. Highlights the divergent risk profiles.
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    focus_models = [
        "Toyota Aqua", "Toyota Hilux", "Ford Courier", "Mazda Bounty",
        "Toyota Corolla", "Nissan Tiida", "Subaru Legacy", "Mazda Demio",
        "Toyota Wish", "Ford Ranger",
    ]

    akl = regional_df[
        (regional_df["region"] == "Auckland") &
        (regional_df["model"].isin(focus_models))
    ].set_index("model")["theft_rate_per_1000"]

    cant = regional_df[
        (regional_df["region"] == "Canterbury") &
        (regional_df["model"].isin(focus_models))
    ].set_index("model")["theft_rate_per_1000"]

    # Order by Auckland rate
    models = akl.sort_values(ascending=False).index.tolist()
    models = [m for m in models if m in cant.index]

    x = np.arange(len(models))
    width = 0.35

    bars_akl = ax.bar(x - width/2, [akl.get(m, 0) for m in models],
                      width, label="Auckland", color=COLORS["aqua_highlight"],
                      alpha=0.85)
    bars_cant = ax.bar(x + width/2, [cant.get(m, 0) for m in models],
                       width, label="Canterbury", color=COLORS["bar_default"],
                       alpha=0.85)

    ax.set_ylabel("Annual Theft Rate per 1,000 Registered Vehicles")
    ax.set_title("Auckland vs Canterbury: Theft Rate by Model\n"
                 "Auckland dominates for imports; Canterbury for utes")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=35, ha="right", fontsize=9)
    ax.legend()
    ax.yaxis.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "07_regional_comparison.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 07_regional_comparison.png")


def plot_claims_time_series(aqua_trend: pd.DataFrame,
                            national: pd.DataFrame):
    """
    Dual-axis time series: national claims volume and Aqua claims.

    Shows the 2023 spike (ram-raid crisis) and subsequent decline,
    with the Aqua's trajectory overlaid.
    """
    fig, ax1 = plt.subplots(figsize=(10, 6))

    years = national["year"].values
    national_claims = national["total_claims"].values
    aqua_claims = aqua_trend["est_model_claims"].values

    # National claims (bar)
    ax1.bar(years, national_claims, color=COLORS["bar_secondary"],
            alpha=0.6, width=0.6, label="Total national claims")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Total National Claims", color=COLORS["bar_default"])
    ax1.tick_params(axis="y", labelcolor=COLORS["bar_default"])
    ax1.set_ylim(0, max(national_claims) * 1.15)

    # Add value labels on bars
    for yr, val in zip(years, national_claims):
        ax1.text(yr, val + 200, f"{int(val):,}", ha="center",
                 fontsize=9, color=COLORS["text"])

    # Aqua claims (line, secondary axis)
    ax2 = ax1.twinx()
    ax2.plot(years, aqua_claims, "o-", color=COLORS["aqua_highlight"],
             linewidth=2.5, markersize=8, label="Toyota Aqua claims",
             zorder=5)
    ax2.set_ylabel("Toyota Aqua Claims", color=COLORS["aqua_highlight"])
    ax2.tick_params(axis="y", labelcolor=COLORS["aqua_highlight"])
    ax2.set_ylim(0, max(aqua_claims) * 1.3)

    # Aqua value labels
    for yr, val in zip(years, aqua_claims):
        ax2.text(yr + 0.1, val + 30, f"{int(val):,}", ha="left",
                 fontsize=9, color=COLORS["aqua_highlight"],
                 fontweight="bold")

    ax1.set_xticks(years)
    ax1.set_xticklabels([str(int(y)) for y in years])

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    ax1.set_title("Vehicle Theft Claims: National Total vs Toyota Aqua (2022-2025)\n"
                  "2023 spike driven by ram-raid crisis; declining since")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "08_claims_time_series.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 08_claims_time_series.png")


def plot_aqua_share_trend(aqua_trend: pd.DataFrame):
    """
    Aqua's share of total claims over time.

    Declining share = other models are being stolen relatively more.
    Stable share = Aqua's risk is tracking the overall trend.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    years = aqua_trend["year"].values
    shares = aqua_trend["theft_claims_pct"].values

    ax.plot(years, shares, "o-", color=COLORS["aqua_highlight"],
            linewidth=2.5, markersize=10, zorder=5)

    # Shade area under curve
    ax.fill_between(years, shares, alpha=0.15,
                    color=COLORS["aqua_highlight"])

    for yr, sh in zip(years, shares):
        ax.text(yr, sh + 0.3, f"{sh}%", ha="center", fontsize=11,
                fontweight="bold", color=COLORS["aqua_highlight"])

    ax.set_xlabel("Year")
    ax.set_ylabel("Share of Total Theft Claims (%)")
    ax.set_title("Toyota Aqua: Share of AMI Theft Claims (2022-2025)")
    ax.set_xticks(years)
    ax.set_xticklabels([str(int(y)) for y in years])
    ax.set_ylim(0, max(shares) + 3)
    ax.yaxis.grid(True, alpha=0.3)

    # Trend line
    slope, intercept, _, _, _ = stats.linregress(years, shares)
    trend_y = intercept + slope * years
    ax.plot(years, trend_y, "--", color=COLORS["grid"], linewidth=1.5,
            label=f"Trend ({slope:+.1f}%/yr)")
    ax.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "09_aqua_share_trend.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 09_aqua_share_trend.png")


def plot_model_rank_trajectories(df_hist: pd.DataFrame):
    """
    Bump chart showing how model rankings shift across 2022-2025.

    Highlights which models are rising (Toyota Corolla) vs falling
    (Mazda Demio) in the theft rankings.
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    highlight_models = {"Toyota Aqua", "Toyota Corolla", "Mazda Demio",
                        "Nissan Tiida", "Toyota Hilux"}

    for model in df_hist["model"].unique():
        model_data = df_hist[df_hist["model"] == model].sort_values("year")
        if len(model_data) < 2:
            continue

        is_highlight = model in highlight_models
        color = (COLORS["aqua_highlight"] if model == "Toyota Aqua"
                 else COLORS["bar_default"] if is_highlight
                 else COLORS["grid"])
        alpha = 1.0 if is_highlight else 0.3
        lw = 3 if model == "Toyota Aqua" else 2 if is_highlight else 1
        zorder = 5 if model == "Toyota Aqua" else 3 if is_highlight else 1

        ax.plot(model_data["year"], model_data["rank"],
                "o-", color=color, alpha=alpha, linewidth=lw,
                markersize=6, zorder=zorder)

        # Label at the end
        if is_highlight:
            last = model_data.iloc[-1]
            ax.text(last["year"] + 0.1, last["rank"],
                    model.replace("Toyota ", "").replace("Nissan ", "").replace("Mazda ", ""),
                    va="center", fontsize=9, color=color,
                    fontweight="bold" if model == "Toyota Aqua" else "normal")

    ax.invert_yaxis()
    ax.set_xlabel("Year")
    ax.set_ylabel("AMI Theft Rank (1 = most stolen)")
    ax.set_title("Theft Ranking Trajectories (2022-2025)")
    ax.set_xticks([2022, 2023, 2024, 2025])
    ax.set_yticks(range(1, 11))
    ax.yaxis.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "10_rank_trajectories.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 10_rank_trajectories.png")


def plot_forecast_rank_trajectories(df_hist: pd.DataFrame,
                                    share_fc: pd.DataFrame):
    """
    Bump chart showing historical rank trajectories (2022-2025) extended
    with dashed projected lines (2026-2027).

    Highlights the projected Corolla-Aqua crossover and the Hilux rise.
    """
    fig, ax = plt.subplots(figsize=(14, 9))

    highlight_models = {"Toyota Aqua", "Toyota Corolla", "Mazda Demio",
                        "Nissan Tiida", "Toyota Hilux"}

    model_colors = {
        "Toyota Aqua": COLORS["aqua_highlight"],
        "Toyota Corolla": "#2A9D8F",
        "Toyota Hilux": "#E9C46A",
        "Mazda Demio": "#264653",
        "Nissan Tiida": "#457B9D",
    }

    for model in df_hist["model"].unique():
        model_data = df_hist[df_hist["model"] == model].sort_values("year")
        if len(model_data) < 2:
            continue

        is_highlight = model in highlight_models
        color = model_colors.get(model, COLORS["grid"])
        alpha = 1.0 if is_highlight else 0.25
        lw = 3 if model == "Toyota Aqua" else 2.5 if is_highlight else 1
        zorder = 5 if model == "Toyota Aqua" else 3 if is_highlight else 1

        # Historical line (solid)
        ax.plot(model_data["year"], model_data["rank"],
                "o-", color=color, alpha=alpha, linewidth=lw,
                markersize=7, zorder=zorder)

        # Forecast extension (dashed)
        if is_highlight:
            last_year = int(model_data.iloc[-1]["year"])
            last_rank = int(model_data.iloc[-1]["rank"])

            fc_model = share_fc[share_fc["model"] == model].sort_values("year")
            if not fc_model.empty:
                fc_years = [last_year] + fc_model["year"].tolist()
                fc_ranks = [last_rank] + fc_model["projected_rank"].tolist()

                ax.plot(fc_years, fc_ranks, "o--", color=color,
                        alpha=alpha * 0.7, linewidth=lw, markersize=7,
                        zorder=zorder)

            # Label at the end
            final_row = fc_model.iloc[-1] if not fc_model.empty else model_data.iloc[-1]
            final_year = final_row["year"]
            final_rank = (final_row["projected_rank"]
                          if "projected_rank" in final_row
                          else final_row["rank"])
            short = (model.replace("Toyota ", "")
                          .replace("Nissan ", "")
                          .replace("Mazda ", ""))
            ax.text(final_year + 0.15, final_rank, short,
                    va="center", fontsize=9, color=color,
                    fontweight="bold" if model == "Toyota Aqua" else "normal")

    # Forecast region shading
    ax.axvspan(2025.5, 2027.5, alpha=0.06, color=COLORS["bar_default"],
               zorder=0)
    ax.text(2026.5, 0.3, "Projected", ha="center", fontsize=10,
            color=COLORS["bar_default"], fontstyle="italic",
            transform=ax.get_xaxis_transform())

    ax.invert_yaxis()
    ax.set_xlabel("Year")
    ax.set_ylabel("Theft Rank (1 = most stolen)")
    ax.set_title("Theft Ranking Trajectories: History + Forecast\n"
                 "Corolla projected to overtake Aqua by 2026")
    ax.set_xticks([2022, 2023, 2024, 2025, 2026, 2027])
    ax.set_yticks(range(1, 13))
    ax.yaxis.grid(True, alpha=0.2)
    ax.set_xlim(2021.7, 2027.8)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "14_forecast_rank_trajectories.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 14_forecast_rank_trajectories.png")


def plot_claims_forecast(aqua_trend: pd.DataFrame,
                         national_fc: pd.DataFrame,
                         share_fc: pd.DataFrame):
    """
    National and Aqua claims with forecast bands.

    Historical data as solid bars/lines; forecast as hatched bars with
    shaded prediction intervals.
    """
    fig, ax1 = plt.subplots(figsize=(12, 7))

    hist = national_fc[~national_fc["is_forecast"]]
    fc = national_fc[national_fc["is_forecast"]]

    # Historical national bars
    ax1.bar(hist["year"], hist["total_claims"], color=COLORS["bar_secondary"],
            alpha=0.6, width=0.6, label="National claims (actual)")

    # Forecast national bars with intervals
    ax1.bar(fc["year"], fc["total_claims"], color=COLORS["bar_secondary"],
            alpha=0.3, width=0.6, hatch="//",
            label="National claims (projected)")
    ax1.errorbar(fc["year"], fc["total_claims"],
                 yerr=[fc["total_claims"] - fc["claims_lo"],
                       fc["claims_hi"] - fc["total_claims"]],
                 fmt="none", color=COLORS["bar_default"], capsize=5,
                 linewidth=2, zorder=4)

    # Value labels
    for _, row in national_fc.iterrows():
        tag = "*" if row["is_forecast"] else ""
        ax1.text(row["year"], row["total_claims"] + 250,
                 f"{int(row['total_claims']):,}{tag}", ha="center",
                 fontsize=9, color=COLORS["text"])

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Total National Claims", color=COLORS["bar_default"])
    ax1.tick_params(axis="y", labelcolor=COLORS["bar_default"])
    ax1.set_ylim(0, 20000)

    # Aqua claims (secondary axis)
    ax2 = ax1.twinx()

    aqua_years = aqua_trend["year"].values
    aqua_claims = aqua_trend["est_model_claims"].values

    ax2.plot(aqua_years, aqua_claims, "o-", color=COLORS["aqua_highlight"],
             linewidth=2.5, markersize=8, label="Aqua claims (actual)",
             zorder=5)

    # Aqua forecast
    aqua_fc = share_fc[share_fc["model"] == "Toyota Aqua"].sort_values("year")
    if not aqua_fc.empty:
        fc_aqua_claims = []
        fc_lo = []
        fc_hi = []
        for _, row in aqua_fc.iterrows():
            nat = national_fc[national_fc["year"] == row["year"]]
            if not nat.empty:
                nat_claims = nat.iloc[0]["total_claims"]
                fc_aqua_claims.append(row["projected_share"] / 100 * nat_claims)
                fc_lo.append(row["share_lo"] / 100 * nat.iloc[0]["claims_lo"])
                fc_hi.append(row["share_hi"] / 100 * nat.iloc[0]["claims_hi"])

        fc_years = aqua_fc["year"].values
        bridge_years = np.concatenate([[aqua_years[-1]], fc_years])
        bridge_claims = np.concatenate([[aqua_claims[-1]], fc_aqua_claims])

        ax2.plot(bridge_years, bridge_claims, "o--",
                 color=COLORS["aqua_highlight"], linewidth=2.5, markersize=8,
                 alpha=0.6, label="Aqua claims (projected)", zorder=5)

        ax2.fill_between(fc_years, fc_lo, fc_hi,
                         alpha=0.12, color=COLORS["aqua_highlight"])

    ax2.set_ylabel("Toyota Aqua Claims", color=COLORS["aqua_highlight"])
    ax2.tick_params(axis="y", labelcolor=COLORS["aqua_highlight"])
    ax2.set_ylim(0, 1800)

    # Aqua value labels
    for yr, val in zip(aqua_years, aqua_claims):
        ax2.text(yr + 0.12, val + 20, f"{int(val):,}", ha="left",
                 fontsize=9, color=COLORS["aqua_highlight"],
                 fontweight="bold")
    for yr, val in zip(fc_years, fc_aqua_claims):
        ax2.text(yr + 0.12, val + 20, f"{int(val):,}*", ha="left",
                 fontsize=9, color=COLORS["aqua_highlight"], alpha=0.7)

    ax1.set_xticks([2022, 2023, 2024, 2025, 2026, 2027])

    # Forecast region
    ax1.axvspan(2025.5, 2027.5, alpha=0.05, color=COLORS["bar_default"],
                zorder=0)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right",
               fontsize=9)

    ax1.set_title("Vehicle Theft Claims: Actual (2022-2025) + Forecast (2026-2027)\n"
                  "* Projected from post-peak trend; 4-year series caveat applies")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "15_claims_forecast.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 15_claims_forecast.png")


def plot_police_vehicle_age_distribution(police_df: pd.DataFrame):
    """
    Histogram of stolen vehicle ages from police row-level data.

    Validates the claim that ~90% of stolen vehicles are 10+ years old
    using actual police records, not insurance estimates.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    cars = police_df[police_df["is_car"]].copy()
    ages = cars["vehicle_age"].dropna()

    ax.hist(ages, bins=range(0, 36), color=COLORS["bar_default"],
            edgecolor="white", alpha=0.8)

    # Highlight key thresholds
    pct_10 = (ages >= 10).mean() * 100
    pct_15 = (ages >= 15).mean() * 100

    ax.axvline(x=10, color=COLORS["aqua_highlight"], linewidth=2,
               linestyle="--", label=f"10 years ({pct_10:.0f}% older)")
    ax.axvline(x=15, color=COLORS["text"], linewidth=2,
               linestyle="--", label=f"15 years ({pct_15:.0f}% older)")

    # Aqua overlay
    aqua_ages = cars[cars["model"] == "AQUA"]["vehicle_age"].dropna()
    if len(aqua_ages) > 5:
        ax.hist(aqua_ages, bins=range(0, 36), color=COLORS["aqua_highlight"],
                edgecolor="white", alpha=0.6, label="Toyota Aqua")

    ax.set_xlabel("Vehicle Age at Theft (years)")
    ax.set_ylabel("Count")
    ax.set_title("Age Distribution of Stolen Vehicles (NZ Police Data)\n"
                 f"{pct_10:.0f}% are 10+ years old; "
                 f"Aqua median age = {aqua_ages.median():.0f} years")
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "11_vehicle_age_distribution.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 11_vehicle_age_distribution.png")


def plot_cross_source_ranking(comparison: pd.DataFrame):
    """
    Dot plot comparing model rankings across data sources.

    Each row is a model; dots show its rank in each source.
    Agreement = dots cluster; divergence = dots spread.
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    # Top models that appear in at least 2 sources
    top = comparison[comparison["sources_ranked"] >= 2].head(12)
    top = top.sort_values("avg_rank")

    y_positions = range(len(top))
    source_markers = {
        "rank_ami": ("o", COLORS["aqua_highlight"], "AMI Insurance"),
        "rank_aa": ("s", COLORS["bar_default"], "AA Insurance"),
        "rank_police": ("^", COLORS["text"], "NZ Police (2021-22)"),
        "rank_moneyhub": ("D", COLORS["bar_secondary"], "MoneyHub (H2 2025)"),
    }

    for col, (marker, color, label) in source_markers.items():
        vals = top[col].values
        valid = ~pd.isna(vals)
        ax.scatter(
            vals[valid],
            np.array(list(y_positions))[valid],
            marker=marker, c=color, s=100, zorder=5,
            label=label, edgecolors="white", linewidth=1,
        )

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(top["model"].values, fontsize=10)
    ax.set_xlabel("Rank (1 = most stolen)")
    ax.set_title("Cross-Source Ranking Comparison\n"
                 "Clustered dots = sources agree; spread = divergence")
    ax.legend(loc="lower right", fontsize=9)
    ax.xaxis.grid(True, alpha=0.3)
    ax.set_xlim(0, 35)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "12_cross_source_rankings.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 12_cross_source_rankings.png")


def plot_police_regional_percapita(regional: pd.DataFrame):
    """
    Bar chart of per-capita theft rates by region from police data.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    reg = regional.sort_values("rate_per_10k", ascending=True)
    colors = [
        COLORS["aqua_highlight"] if r in ("Auckland", "Canterbury")
        else COLORS["bar_default"]
        for r in reg["region"]
    ]

    bars = ax.barh(reg["region"], reg["rate_per_10k"], color=colors,
                   edgecolor="white")

    for bar, rate in zip(bars, reg["rate_per_10k"]):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                f"{rate:.1f}", va="center", fontsize=9, color=COLORS["text"])

    ax.set_xlabel("Thefts per 10,000 Population (6-month rate)")
    ax.set_title("Vehicle Theft Rate by Region (NZ Police Data, 2021-22)")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "13_police_regional_percapita.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 13_police_regional_percapita.png")


def plot_socioeconomic_drivers(df: pd.DataFrame, correlations: pd.DataFrame):
    """
    Panel of scatter plots showing the strongest socioeconomic
    predictors of regional theft rate.

    Four panels: deprivation, unemployment, urbanisation, and density.
    Each region is a point, labelled where space permits.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 11))

    panels = [
        ("deprivation_index", "NZ Deprivation Index\n(1=least, 10=most deprived)"),
        ("unemployment_rate", "Unemployment Rate (%)"),
        ("pct_urban", "Urban Population (%)"),
        ("density_km2", "Population Density (per km²)"),
    ]

    label_regions = {"Gisborne", "Auckland", "Nelson", "Canterbury",
                     "Wellington", "Northland", "Southland",
                     "Bay of Plenty"}

    for ax, (var, xlabel) in zip(axes.flat, panels):
        x = df[var].values
        y = df["thefts_per_10k"].values

        # Correlation from precomputed table (Spearman)
        corr_row = correlations[correlations["variable"] == var]
        rho = corr_row.iloc[0]["spearman_rho"] if not corr_row.empty else 0
        rho_p = corr_row.iloc[0]["spearman_p"] if not corr_row.empty else 1

        ax.scatter(x, y, c=COLORS["bar_default"], s=80, zorder=5,
                   edgecolors="white", linewidth=1)

        # Trend line (visual aid only)
        slope, intercept, _, _, _ = stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, intercept + slope * x_line, "--",
                color=COLORS["aqua_highlight"], linewidth=1.5, alpha=0.7)

        # Labels
        for _, row in df.iterrows():
            if row["region"] in label_regions:
                offset = (5, 5)
                if row["region"] == "Auckland":
                    offset = (5, -12)
                elif row["region"] == "Nelson":
                    offset = (5, -12)
                ax.annotate(
                    row["region"], (row[var], row["thefts_per_10k"]),
                    textcoords="offset points", xytext=offset,
                    fontsize=8, color=COLORS["text"], alpha=0.8,
                )

        sig = " *" if rho_p < 0.05 else ""
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Thefts per 10,000 pop.")
        ax.set_title(f"ρ = {rho:+.3f} (p={rho_p:.2f}){sig}", fontsize=11)
        ax.yaxis.grid(True, alpha=0.2)

    fig.suptitle("Socioeconomic Predictors of Regional Theft Rate\n"
                 "Each point is a NZ region (n=13); "
                 "dashed line = linear fit",
                 fontsize=13, fontweight="bold", y=1.01)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "16_socioeconomic_drivers.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 16_socioeconomic_drivers.png")


def plot_residual_map(residuals: pd.DataFrame, model_info: dict):
    """
    Horizontal bar chart of model residuals: which regions have
    more/fewer thefts than socioeconomic factors predict?

    Positive residuals = unexplained excess theft (other factors at
    play). Negative = less theft than expected (protective factors).
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    res = residuals.sort_values("std_residual")

    colors = [
        COLORS["aqua_highlight"] if r > 0.8
        else "#264653" if r < -0.8
        else COLORS["bar_secondary"]
        for r in res["std_residual"]
    ]

    ax.barh(res["region"], res["std_residual"], color=colors,
            edgecolor="white", linewidth=0.5)

    # Reference lines
    ax.axvline(0, color=COLORS["text"], linewidth=1)
    ax.axvline(1.0, color=COLORS["grid"], linewidth=1, linestyle="--",
               alpha=0.5)
    ax.axvline(-1.0, color=COLORS["grid"], linewidth=1, linestyle="--",
               alpha=0.5)

    # Value labels
    for i, (_, row) in enumerate(res.iterrows()):
        ha = "left" if row["std_residual"] >= 0 else "right"
        offset = 0.08 if row["std_residual"] >= 0 else -0.08
        ax.text(row["std_residual"] + offset, i,
                f'{row["std_residual"]:+.2f}',
                va="center", ha=ha, fontsize=9, color=COLORS["text"])

    preds = ", ".join(p.replace("_", " ") for p in model_info["predictors"])
    ax.set_xlabel("Standardised Residual\n"
                  "(positive = more theft than predicted)")
    ax.set_title(f"Theft Rates Unexplained by Socioeconomic Factors\n"
                 f"Model: {preds} (R² = {model_info['r_squared']:.2f})",
                 fontsize=12)
    ax.xaxis.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "17_socioeconomic_residuals.png", dpi=150,
                bbox_inches="tight")
    plt.close()
    print("Saved: 17_socioeconomic_residuals.png")


def generate_all_figures():
    """Generate all analysis figures."""
    setup_style()

    print("\n" + "=" * 50)
    print("GENERATING FIGURES")
    print("=" * 50 + "\n")

    # Load and prepare data
    df = build_merged_dataset()
    df = compute_base_rate_metrics(df)

    # Confound scores
    df = compute_age_risk_score(df)
    df = compute_security_score(df)
    df = compute_parts_demand_proxy(df)
    df = compute_geographic_risk(df)
    df = compute_composite_vulnerability(df)
    df = compute_residual_targeting(df)

    # Original plots
    plot_raw_vs_adjusted_ranking(df)
    plot_theft_rate_bar_chart(df)
    plot_fleet_vs_thefts_scatter(df)
    plot_theft_fleet_ratio(df)
    plot_confound_heatmap(df)
    plot_ami_insurance_comparison(None)

    # Regional comparison
    from regional_analysis import compute_regional_theft_rates
    regional_df = compute_regional_theft_rates()
    plot_regional_comparison(regional_df)

    # Time series
    from time_series_analysis import (
        load_historical_ami, compute_aqua_trend, compute_national_trend,
        forecast_national_claims, forecast_model_shares,
    )
    hist = load_historical_ami()
    aqua_trend = compute_aqua_trend(hist)
    national = compute_national_trend(hist)

    plot_claims_time_series(aqua_trend, national)
    plot_aqua_share_trend(aqua_trend)
    plot_model_rank_trajectories(hist)

    # Forecasting
    national_fc = forecast_national_claims(national)
    share_fc = forecast_model_shares(hist)
    plot_forecast_rank_trajectories(hist, share_fc)
    plot_claims_forecast(aqua_trend, national_fc, share_fc)

    # Police data plots
    from police_data_analysis import (
        load_police_data, analyse_model_distribution,
        analyse_regional_distribution,
    )
    police_df = load_police_data()
    plot_police_vehicle_age_distribution(police_df)

    police_regional = analyse_regional_distribution(police_df)
    plot_police_regional_percapita(police_regional)

    # Cross-source comparison
    from cross_source_validation import build_comparison_table
    comparison = build_comparison_table()
    plot_cross_source_ranking(comparison)

    # Socioeconomic analysis
    from socioeconomic_analysis import (
        build_analysis_dataset, compute_bivariate_correlations,
        fit_multivariable_model,
    )
    socio_df = build_analysis_dataset()
    socio_corr = compute_bivariate_correlations(socio_df)
    socio_model = fit_multivariable_model(socio_df)
    plot_socioeconomic_drivers(socio_df, socio_corr)
    plot_residual_map(socio_model["residuals"], socio_model)

    print(f"\nAll figures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    generate_all_figures()
