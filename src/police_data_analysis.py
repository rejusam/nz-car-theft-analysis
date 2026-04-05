"""
NZ Police Stolen Vehicle Database: Row-Level Analysis.

Analyses 4,500+ individual stolen vehicle records from the NZ Police
Vehicle of Interest database (Oct 2021 – Apr 2022). This is the only
dataset in the project with row-level granularity — every other source
provides aggregates.

Key analyses:
    1. Model-level theft counts and shares (independent of insurance data)
    2. Regional distribution with per-capita normalisation
    3. Temporal patterns (day-of-week, monthly trends)
    4. Vehicle age distribution at time of theft
    5. Vehicle type breakdown (cars vs utes vs trailers)

Data source: NZ Police via Maven Analytics / Kaggle
License: CC0 Public Domain
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# Vehicle types that count as passenger/utility vehicles
CAR_TYPES = {
    "Saloon", "Hatchback", "Stationwagon", "Utility", "Sports Car",
    "Convertible", "SUV", "Light Van",
}

# Map raw model descriptions to standardised names used elsewhere
MODEL_STANDARDISATION = {
    "AQUA": "Toyota Aqua",
    "COROLLA": "Toyota Corolla",
    "HILUX": "Toyota Hilux",
    "VITZ": "Toyota Vitz",
    "WISH": "Toyota Wish",
    "CALDINA": "Toyota Caldina",
    "RAV4": "Toyota RAV4",
    "MARKX": "Toyota Mark X",
    "MARK X": "Toyota Mark X",
    "TIIDA": "Nissan Tiida",
    "WINGROAD": "Nissan Wingroad",
    "X-TRAIL": "Nissan X-Trail",
    "NAVARA": "Nissan Navara",
    "DEMIO": "Mazda Demio",
    "ATENZA": "Mazda Atenza",
    "BOUNTY": "Mazda Bounty",
    "CX-5": "Mazda CX-5",
    "AXELA": "Mazda Axela",
    "FAMILIA": "Mazda Familia",
    "FIT": "Honda Fit",
    "CRV": "Honda CRV",
    "CR-V": "Honda CRV",
    "ACCORD": "Honda Accord",
    "LEGACY": "Subaru Legacy",
    "IMPREZA": "Subaru Impreza",
    "FORESTER": "Subaru Forester",
    "COURIER": "Ford Courier",
    "RANGER": "Ford Ranger",
    "FALCON": "Ford Falcon",
    "SWIFT": "Suzuki Swift",
    "OUTLANDER": "Mitsubishi Outlander",
    "LANCER": "Mitsubishi Lancer",
    "COMMODORE": "Holden Commodore",
    "GOLF": "Volkswagen Golf",
}


def load_police_data() -> pd.DataFrame:
    """Load and enrich the police stolen vehicle dataset."""
    path = DATA_DIR / "police_stolen_vehicles_2022.csv"
    df = pd.read_csv(path, parse_dates=["date_stolen"])

    # Derived fields
    df["day_of_week"] = df["date_stolen"].dt.day_name()
    df["month"] = df["date_stolen"].dt.to_period("M")
    df["year_stolen"] = df["date_stolen"].dt.year

    # Vehicle age at time of theft
    df["vehicle_age"] = df["year_stolen"] - df["model_year"]
    df["vehicle_age"] = df["vehicle_age"].clip(lower=0)

    # Standardised model name
    df["model_std"] = df["model"].map(MODEL_STANDARDISATION)

    # Is this a car/van (vs trailer, bike, boat)?
    df["is_car"] = df["vehicle_type"].isin(CAR_TYPES)

    print(f"Police data loaded: {len(df)} records")
    print(f"  Date range: {df['date_stolen'].min().date()} to "
          f"{df['date_stolen'].max().date()}")
    print(f"  Cars/vans: {df['is_car'].sum()}, Other: {(~df['is_car']).sum()}")
    return df


def analyse_model_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rank models by theft frequency in the police data.

    This provides an independent ranking that can be compared
    against AMI and AA Insurance rankings.
    """
    cars = df[df["is_car"]].copy()
    total_cars = len(cars)

    model_counts = (
        cars.groupby("model")
        .agg(
            thefts=("vehicle_id", "count"),
            make=("make", "first"),
            median_age=("vehicle_age", "median"),
        )
        .sort_values("thefts", ascending=False)
        .reset_index()
    )

    model_counts["pct_of_total"] = (
        model_counts["thefts"] / total_cars * 100
    ).round(1)
    model_counts["rank_police"] = range(1, len(model_counts) + 1)

    # Add standardised name for cross-referencing
    model_counts["model_std"] = model_counts["model"].map(MODEL_STANDARDISATION)

    return model_counts


def analyse_regional_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Theft counts and per-capita rates by region.

    Uses actual police records rather than insurance claims,
    capturing uninsured vehicle thefts that AMI/AA miss.
    """
    cars = df[df["is_car"]].copy()

    regional = (
        cars.groupby("region")
        .agg(
            thefts=("vehicle_id", "count"),
            population=("region_population", "first"),
            density=("region_density_km2", "first"),
        )
        .sort_values("thefts", ascending=False)
        .reset_index()
    )

    # Population may have commas from source CSV
    regional["population"] = (
        regional["population"].astype(str).str.replace(",", "").astype(float)
    )

    # Per capita rate (per 10,000 population)
    regional["rate_per_10k"] = (
        regional["thefts"] / regional["population"] * 10000
    ).round(1)

    # Annualise (data covers ~6 months)
    regional["thefts_annual_est"] = regional["thefts"] * 2
    regional["annual_rate_per_10k"] = (regional["rate_per_10k"] * 2).round(1)

    regional["pct_of_total"] = (
        regional["thefts"] / regional["thefts"].sum() * 100
    ).round(1)

    return regional


def analyse_temporal_patterns(df: pd.DataFrame) -> dict:
    """
    Day-of-week and monthly trends in vehicle theft.

    Identifies whether specific days or months are higher-risk,
    which informs prevention strategies.
    """
    cars = df[df["is_car"]].copy()

    # Day of week
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    dow = cars["day_of_week"].value_counts().reindex(day_order)

    # Monthly trend
    monthly = cars.groupby("month").size()

    # Chi-squared test: are thefts uniformly distributed across days?
    expected_daily = len(cars) / 7
    chi2, p = stats.chisquare(dow.values, f_exp=[expected_daily] * 7)

    return {
        "day_of_week": dow,
        "monthly": monthly,
        "peak_day": dow.idxmax(),
        "peak_day_count": int(dow.max()),
        "trough_day": dow.idxmin(),
        "trough_day_count": int(dow.min()),
        "chi2_uniform_day": round(chi2, 2),
        "chi2_p_value": p,
        "days_significant": p < 0.05,
    }


def analyse_vehicle_age(df: pd.DataFrame) -> dict:
    """
    Age distribution of stolen vehicles.

    Tests the claim that ~90% of stolen vehicles are 10+ years old.
    """
    cars = df[df["is_car"]].copy()
    ages = cars["vehicle_age"].dropna()

    pct_over_10 = (ages >= 10).mean() * 100
    pct_over_15 = (ages >= 15).mean() * 100
    pct_over_5 = (ages >= 5).mean() * 100

    # Age distribution by model (for key models)
    key_models = ["AQUA", "COROLLA", "HILUX", "DEMIO", "TIIDA", "COURIER"]
    model_ages = {}
    for model in key_models:
        subset = cars[cars["model"] == model]["vehicle_age"]
        if len(subset) > 5:
            model_ages[model] = {
                "median": round(subset.median(), 1),
                "mean": round(subset.mean(), 1),
                "pct_over_10": round((subset >= 10).mean() * 100, 1),
                "count": len(subset),
            }

    return {
        "median_age": round(ages.median(), 1),
        "mean_age": round(ages.mean(), 1),
        "pct_over_5_years": round(pct_over_5, 1),
        "pct_over_10_years": round(pct_over_10, 1),
        "pct_over_15_years": round(pct_over_15, 1),
        "model_ages": model_ages,
    }


def analyse_vehicle_types(df: pd.DataFrame) -> pd.DataFrame:
    """Breakdown by vehicle type (car vs ute vs trailer vs bike)."""
    type_counts = (
        df.groupby("vehicle_type")
        .agg(count=("vehicle_id", "count"))
        .sort_values("count", ascending=False)
        .reset_index()
    )
    type_counts["pct"] = (type_counts["count"] / len(df) * 100).round(1)
    return type_counts


def print_police_report(model_dist, regional, temporal, age_info, types):
    """Print the police data analysis report."""
    print("\n" + "=" * 70)
    print("NZ POLICE STOLEN VEHICLE DATABASE ANALYSIS")
    print("4,500+ records, Oct 2021 – Apr 2022")
    print("=" * 70)

    print("\n--- Vehicle Type Breakdown ---\n")
    print(types.head(10).to_string(index=False))

    print("\n--- Top 20 Stolen Models (Cars/Vans Only) ---\n")
    cols = ["rank_police", "model", "make", "thefts", "pct_of_total",
            "median_age"]
    print(model_dist[cols].head(20).to_string(index=False))

    print(f"\n--- Regional Distribution ---\n")
    cols_r = ["region", "thefts", "pct_of_total", "rate_per_10k",
              "population"]
    print(regional[cols_r].to_string(index=False))

    print(f"\n--- Temporal Patterns ---\n")
    print(f"Peak day: {temporal['peak_day']} "
          f"({temporal['peak_day_count']} thefts)")
    print(f"Trough day: {temporal['trough_day']} "
          f"({temporal['trough_day_count']} thefts)")
    chi2_verdict = ("significant" if temporal["days_significant"]
                    else "not significant")
    print(f"Day-of-week uniformity test: chi² = "
          f"{temporal['chi2_uniform_day']}, p = "
          f"{temporal['chi2_p_value']:.4f} ({chi2_verdict})")
    print(f"\nDay-of-week counts:")
    for day, count in temporal["day_of_week"].items():
        print(f"  {day:12s} {count:4d}")

    print(f"\n--- Vehicle Age Analysis ---\n")
    print(f"Median age at theft: {age_info['median_age']} years")
    print(f"Over 5 years:  {age_info['pct_over_5_years']}%")
    print(f"Over 10 years: {age_info['pct_over_10_years']}%")
    print(f"Over 15 years: {age_info['pct_over_15_years']}%")

    if age_info["model_ages"]:
        print(f"\nAge by model:")
        for model, info in age_info["model_ages"].items():
            print(f"  {model:12s} median={info['median']:.0f}yr  "
                  f"over10={info['pct_over_10']}%  (n={info['count']})")

    # Aqua spotlight
    aqua = model_dist[model_dist["model"] == "AQUA"]
    if not aqua.empty:
        a = aqua.iloc[0]
        print(f"\n--- Toyota Aqua in Police Data ---\n")
        print(f"  Rank: #{int(a['rank_police'])} "
              f"({int(a['thefts'])} thefts, {a['pct_of_total']}%)")
        print(f"  Median age at theft: {a['median_age']:.0f} years")
        print(f"  Note: This is 2021-22 data; Aqua rose to #1 in "
              f"insurance claims from 2022 onward.")


def main():
    df = load_police_data()

    model_dist = analyse_model_distribution(df)
    regional = analyse_regional_distribution(df)
    temporal = analyse_temporal_patterns(df)
    age_info = analyse_vehicle_age(df)
    types = analyse_vehicle_types(df)

    print_police_report(model_dist, regional, temporal, age_info, types)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model_dist.to_csv(OUTPUT_DIR / "police_model_ranking.csv", index=False)
    regional.to_csv(OUTPUT_DIR / "police_regional_distribution.csv",
                    index=False)
    print(f"\nResults saved to {OUTPUT_DIR}/")

    return df, model_dist, regional, temporal, age_info


if __name__ == "__main__":
    main()
