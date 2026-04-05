"""
Time Series Analysis: AMI theft claims 2022–2025.

Tracks how the Aqua's theft risk has evolved over four years of AMI
data. Key questions:
    1. Is the Aqua's absolute theft count declining?
    2. Is its share of total claims stable or shifting?
    3. Is the overall theft trend driving model-level changes?
    4. Are newer models with better security displacing older targets?

Data source: AMI Insurance (IAG NZ) annual stolen vehicle reports,
compiled from published press releases and news coverage.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def load_historical_ami() -> pd.DataFrame:
    """Load 4 years of AMI theft claims data (2022-2025)."""
    path = DATA_DIR / "ami_theft_claims_historical.csv"
    df = pd.read_csv(path)
    print(f"Historical AMI data loaded: {len(df)} records, "
          f"{df['year'].nunique()} years")
    return df


def compute_aqua_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Toyota Aqua trend metrics across all available years.

    Returns one row per year with:
        - claims count and percentage
        - total national claims
        - year-over-year changes
    """
    aqua = df[df["model"] == "Toyota Aqua"].sort_values("year").copy()

    aqua["claims_yoy_change"] = aqua["est_model_claims"].diff()
    aqua["claims_yoy_pct_change"] = (
        aqua["est_model_claims"].pct_change() * 100
    ).round(1)
    aqua["national_yoy_change"] = aqua["total_claims_national"].diff()
    aqua["share_change"] = aqua["theft_claims_pct"].diff()

    return aqua.reset_index(drop=True)


def compute_model_trajectories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rank trajectory for each model across years.

    Identifies which models are rising vs falling in the theft rankings,
    revealing fleet composition shifts (e.g., Mazda Demio declining as
    the fleet ages out, Toyota Corolla rising).
    """
    trajectories = []

    for model in df["model"].unique():
        model_data = df[df["model"] == model].sort_values("year")
        years_present = model_data["year"].tolist()
        ranks = model_data["rank"].tolist()

        if len(years_present) < 2:
            continue

        # Linear trend in rank (negative slope = improving = moving up)
        if len(years_present) >= 3:
            slope, _, r_value, p_value, _ = stats.linregress(
                years_present, ranks
            )
        else:
            slope = ranks[-1] - ranks[0]
            r_value = np.nan
            p_value = np.nan

        first_rank = ranks[0]
        last_rank = ranks[-1]
        rank_change = last_rank - first_rank

        trajectories.append({
            "model": model,
            "first_year": min(years_present),
            "last_year": max(years_present),
            "years_in_top_10": len(years_present),
            "first_rank": first_rank,
            "last_rank": last_rank,
            "rank_change": rank_change,
            "rank_trend_slope": round(slope, 2),
            "trajectory": (
                "Stable" if abs(rank_change) <= 1
                else "Rising" if rank_change < 0
                else "Falling"
            ),
        })

    return pd.DataFrame(trajectories).sort_values("last_rank")


def compute_national_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    National theft claims trend.

    The spike in 2023 (ram-raid crisis) and subsequent decline are
    critical context for interpreting model-level trends.
    """
    national = (
        df.groupby("year")
        .agg(
            total_claims=("total_claims_national", "first"),
            models_tracked=("model", "nunique"),
        )
        .reset_index()
    )

    national["yoy_change"] = national["total_claims"].diff()
    national["yoy_pct_change"] = (
        national["total_claims"].pct_change() * 100
    ).round(1)

    # Compound annual growth rate
    first_year = national.iloc[0]["total_claims"]
    last_year = national.iloc[-1]["total_claims"]
    n_years = len(national) - 1
    if first_year > 0 and n_years > 0:
        cagr = ((last_year / first_year) ** (1 / n_years) - 1) * 100
        national["cagr_from_start"] = round(cagr, 1)

    return national


def assess_aqua_risk_trend(aqua_trend: pd.DataFrame) -> dict:
    """
    Synthesise the Aqua risk trend into a structured assessment.

    Key question: Is the Aqua becoming safer as newer models with
    encrypted immobilisers enter the fleet?
    """
    claims = aqua_trend["est_model_claims"].values
    years = aqua_trend["year"].values
    shares = aqua_trend["theft_claims_pct"].values

    # Absolute claims trend (excluding 2023 spike)
    peak_year = aqua_trend.loc[
        aqua_trend["est_model_claims"].idxmax(), "year"
    ]
    peak_claims = aqua_trend["est_model_claims"].max()
    latest_claims = claims[-1]
    decline_from_peak = ((peak_claims - latest_claims) / peak_claims * 100)

    # Share trend
    share_start = shares[0]
    share_end = shares[-1]
    share_change = share_end - share_start

    # Linear trend on claims
    slope, intercept, r, p, se = stats.linregress(years, claims)

    assessment = {
        "peak_year": int(peak_year),
        "peak_claims": int(peak_claims),
        "latest_claims": int(latest_claims),
        "decline_from_peak_pct": round(decline_from_peak, 1),
        "share_2022": share_start,
        "share_latest": share_end,
        "share_change_pp": round(share_change, 1),
        "claims_trend_slope": round(slope, 1),
        "claims_trend_p": p,
        "trending_down": slope < 0,
        "share_declining": share_change < 0,
    }

    # Narrative
    if slope < 0 and share_change < 0:
        assessment["narrative"] = (
            "Both absolute claims and claim share are declining. "
            "The Aqua's theft risk appears to be genuinely decreasing, "
            "likely driven by the overall crime decline and gradual "
            "fleet turnover to newer, more secure models."
        )
    elif slope < 0 and share_change >= 0:
        assessment["narrative"] = (
            "Absolute claims are falling but the Aqua's share of total "
            "claims is stable or rising. The decline is driven by the "
            "national crime trend, not Aqua-specific improvement. "
            "The Aqua remains disproportionately targeted relative to "
            "other models."
        )
    else:
        assessment["narrative"] = (
            "Claims are not declining. The Aqua's theft risk remains "
            "elevated and is not showing signs of improvement from "
            "newer, more secure models entering the fleet."
        )

    return assessment


def print_time_series_report(aqua_trend: pd.DataFrame,
                             trajectories: pd.DataFrame,
                             national: pd.DataFrame,
                             assessment: dict):
    """Print the time series analysis report."""
    print("\n" + "=" * 70)
    print("TIME SERIES ANALYSIS: AMI THEFT CLAIMS 2022-2025")
    print("Is the Aqua's risk trending down?")
    print("=" * 70)

    print("\n--- National Claims Trend ---\n")
    for _, row in national.iterrows():
        yoy = f" ({row['yoy_pct_change']:+.0f}%)" if pd.notna(row.get("yoy_pct_change")) and not np.isnan(row["yoy_pct_change"]) else ""
        print(f"  {int(row['year'])}: {int(row['total_claims']):,} claims{yoy}")

    print(f"\n  Pattern: Spike in 2023 (ram-raid crisis), declining since.")

    print("\n--- Toyota Aqua Trend ---\n")
    for _, row in aqua_trend.iterrows():
        yoy = ""
        if pd.notna(row.get("claims_yoy_pct_change")) and not np.isnan(row["claims_yoy_pct_change"]):
            yoy = f" ({row['claims_yoy_pct_change']:+.0f}%)"
        per1k = ""
        if pd.notna(row.get("theft_per_1000_insured")) and row["theft_per_1000_insured"] > 0:
            per1k = f"  [{row['theft_per_1000_insured']:.0f}/1000 insured]"
        print(f"  {int(row['year'])}: {int(row['est_model_claims']):,} claims "
              f"({row['theft_claims_pct']}% share, rank #{int(row['rank'])})"
              f"{yoy}{per1k}")

    print(f"\n--- Risk Assessment ---\n")
    print(f"  Peak year:            {assessment['peak_year']}")
    print(f"  Peak claims:          {assessment['peak_claims']:,}")
    print(f"  Latest claims:        {assessment['latest_claims']:,}")
    print(f"  Decline from peak:    {assessment['decline_from_peak_pct']:.0f}%")
    print(f"  Share change:         {assessment['share_change_pp']:+.1f} "
          f"percentage points ({assessment['share_2022']}% → "
          f"{assessment['share_latest']}%)")
    print(f"  Claims trend:         {'Declining' if assessment['trending_down'] else 'Rising/Flat'}")
    print(f"  Share trend:          {'Declining' if assessment['share_declining'] else 'Stable/Rising'}")

    print(f"\n  Interpretation:")
    print(f"  {assessment['narrative']}")

    print("\n--- Model Trajectories (2022-2025) ---\n")
    cols = ["model", "first_rank", "last_rank", "rank_change", "trajectory",
            "years_in_top_10"]
    display = trajectories[cols].copy()
    display.columns = ["Model", "First Rank", "Latest Rank", "Change",
                        "Trajectory", "Years in Top 10"]
    print(display.to_string(index=False))

    # Notable shifts
    risers = trajectories[trajectories["trajectory"] == "Rising"]
    fallers = trajectories[trajectories["trajectory"] == "Falling"]

    if not risers.empty:
        print(f"\n  Rising: {', '.join(risers['model'].tolist())}")
    if not fallers.empty:
        print(f"  Falling: {', '.join(fallers['model'].tolist())}")


def main():
    df = load_historical_ami()

    aqua_trend = compute_aqua_trend(df)
    trajectories = compute_model_trajectories(df)
    national = compute_national_trend(df)
    assessment = assess_aqua_risk_trend(aqua_trend)

    print_time_series_report(aqua_trend, trajectories, national, assessment)

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    aqua_trend.to_csv(OUTPUT_DIR / "aqua_trend_2022_2025.csv", index=False)
    trajectories.to_csv(OUTPUT_DIR / "model_trajectories.csv", index=False)
    national.to_csv(OUTPUT_DIR / "national_claims_trend.csv", index=False)
    print(f"\nResults saved to {OUTPUT_DIR}/")

    return aqua_trend, trajectories, national, assessment


if __name__ == "__main__":
    main()
