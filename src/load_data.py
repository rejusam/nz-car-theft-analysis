"""
Data ingestion and validation for NZ car theft analysis.

Loads and validates the three core datasets:
    - AMI theft claims (insurance data)
    - MoneyHub/Police theft records (police data)
    - NZTA fleet registration counts
"""

import pandas as pd
import sys
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_ami_data() -> pd.DataFrame:
    """Load AMI Insurance theft claims data for 2025."""
    path = DATA_DIR / "ami_theft_claims_2025.csv"
    df = pd.read_csv(path)
    print(f"AMI data loaded: {len(df)} models")
    return df


def load_police_data() -> pd.DataFrame:
    """Load MoneyHub/Police theft data (H2 2025, 6-month window)."""
    path = DATA_DIR / "moneyhub_police_thefts_2025.csv"
    df = pd.read_csv(path)

    # Annualise the 6-month counts
    df["thefts_annual_est"] = df["thefts_6mo"] * 2

    print(f"Police data loaded: {len(df)} models, "
          f"{df['thefts_6mo'].sum()} thefts in 6 months")
    return df


def load_fleet_data() -> pd.DataFrame:
    """Load NZTA/CarJam fleet registration data."""
    path = DATA_DIR / "nz_fleet_by_model.csv"
    df = pd.read_csv(path)
    total = df["fleet_registered"].sum()
    print(f"Fleet data loaded: {len(df)} models, "
          f"{total:,} total vehicles tracked")
    return df


def build_merged_dataset() -> pd.DataFrame:
    """
    Merge police theft data with fleet data for integrated analysis.

    Returns a DataFrame with:
        - model, make
        - fleet_registered
        - thefts_6mo, thefts_annual_est
        - theft_rate_per_1000 (annualised)
        - vehicle age and security metadata
    """
    police = load_police_data()
    fleet = load_fleet_data()

    merged = pd.merge(
        police,
        fleet,
        on=["model", "make"],
        how="inner",
        suffixes=("_police", "_fleet"),
    )

    # Use fleet data as canonical fleet size
    if "fleet_registered_fleet" in merged.columns:
        merged["fleet_registered"] = merged["fleet_registered_fleet"]
        merged.drop(
            columns=["fleet_registered_police", "fleet_registered_fleet"],
            inplace=True,
        )

    # Compute annualised theft rate per 1,000 registered vehicles
    merged["theft_rate_per_1000"] = (
        merged["thefts_annual_est"] / merged["fleet_registered"] * 1000
    )

    merged.sort_values("theft_rate_per_1000", ascending=False, inplace=True)
    merged.reset_index(drop=True, inplace=True)

    print(f"\nMerged dataset: {len(merged)} models")
    print(f"Highest theft rate: {merged.iloc[0]['model']} "
          f"({merged.iloc[0]['theft_rate_per_1000']:.1f} per 1,000)")

    return merged


def validate_data(df: pd.DataFrame) -> bool:
    """Run basic validation checks on the merged dataset."""
    issues = []

    if df["fleet_registered"].min() <= 0:
        issues.append("Fleet size must be positive for all models")

    if df["thefts_6mo"].min() < 0:
        issues.append("Theft counts cannot be negative")

    if df["theft_rate_per_1000"].max() > 100:
        issues.append("Implausibly high theft rate detected (>10%)")

    if issues:
        print("Validation FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    print("Validation passed.")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("NZ Car Theft Analysis — Data Loading")
    print("=" * 60)

    ami = load_ami_data()
    print()
    merged = build_merged_dataset()
    print()
    validate_data(merged)

    print("\n--- Merged Dataset Preview ---")
    cols = ["model", "make", "fleet_registered", "thefts_annual_est",
            "theft_rate_per_1000"]
    print(merged[cols].to_string(index=False))
