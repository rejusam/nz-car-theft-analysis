"""
Regional Theft Rate Analysis: Auckland vs Canterbury and beyond.

Computes per-model theft rates within each region, revealing how
geographic context changes the risk picture. Canterbury is the
"ute theft capital" while Auckland dominates for imported passenger
cars like the Aqua.

Data sources:
    - Police/MoneyHub regional theft counts (H2 2025)
    - NZTA MVR fleet data aggregated by territorial authority
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def load_regional_thefts() -> pd.DataFrame:
    """Load police-sourced theft counts broken down by region and model."""
    path = DATA_DIR / "regional_thefts_2025.csv"
    df = pd.read_csv(path)
    df["thefts_annual_est"] = df["thefts_6mo"] * 2
    return df


def load_regional_fleet() -> pd.DataFrame:
    """
    Load fleet counts by model and region.

    Uses NZTA MVR-derived summary if available (from nzta_fetcher.py),
    otherwise falls back to the pre-computed estimates.
    """
    path = DATA_DIR / "nzta_fleet_regional_summary.csv"
    return pd.read_csv(path)


def compute_regional_theft_rates(regions=None) -> pd.DataFrame:
    """
    Compute theft rate per 1,000 vehicles for each model within each region.

    This is the core analysis: same model, different regions, different
    risk profiles. The Aqua might be #1 in Auckland but not Canterbury.
    """
    thefts = load_regional_thefts()
    fleet = load_regional_fleet()

    if regions is None:
        regions = ["Auckland", "Canterbury", "Waikato", "Wellington",
                    "Bay of Plenty"]

    results = []
    for region in regions:
        fleet_col = f"fleet_{region.lower().replace(' ', '_').replace('of_', '')}"

        # Handle Bay of Plenty naming
        if region == "Bay of Plenty":
            fleet_col = "fleet_bop"

        if fleet_col not in fleet.columns:
            print(f"Warning: no fleet column '{fleet_col}' found, skipping {region}")
            continue

        region_thefts = thefts[thefts["region"] == region].copy()
        region_fleet = fleet[["model", "make", fleet_col]].copy()
        region_fleet.rename(columns={fleet_col: "fleet_regional"}, inplace=True)

        merged = pd.merge(
            region_thefts, region_fleet,
            on=["model", "make"], how="inner"
        )

        merged["theft_rate_per_1000"] = (
            merged["thefts_annual_est"] / merged["fleet_regional"] * 1000
        )

        merged["region"] = region
        results.append(merged)

    combined = pd.concat(results, ignore_index=True)
    combined.sort_values(
        ["region", "theft_rate_per_1000"],
        ascending=[True, False],
        inplace=True,
    )

    return combined


def compare_auckland_canterbury(df: pd.DataFrame) -> pd.DataFrame:
    """
    Head-to-head comparison of Auckland vs Canterbury theft rates.

    This highlights the divergence: Auckland = passenger car theft hub,
    Canterbury = ute theft capital.
    """
    akl = df[df["region"] == "Auckland"][
        ["model", "theft_rate_per_1000", "thefts_annual_est", "fleet_regional"]
    ].copy()
    akl.columns = ["model", "akl_rate", "akl_thefts", "akl_fleet"]

    cant = df[df["region"] == "Canterbury"][
        ["model", "theft_rate_per_1000", "thefts_annual_est", "fleet_regional"]
    ].copy()
    cant.columns = ["model", "cant_rate", "cant_thefts", "cant_fleet"]

    comparison = pd.merge(akl, cant, on="model", how="outer")
    comparison["rate_ratio_akl_cant"] = comparison["akl_rate"] / comparison["cant_rate"]
    comparison["higher_in"] = comparison.apply(
        lambda r: "Auckland" if r["akl_rate"] > r["cant_rate"] else "Canterbury",
        axis=1,
    )

    comparison.sort_values("rate_ratio_akl_cant", ascending=False, inplace=True)
    return comparison


def compute_regional_risk_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summary table: which model is riskiest in each region?
    """
    summary = (
        df.groupby("region")
        .apply(
            lambda g: pd.Series({
                "highest_risk_model": g.loc[g["theft_rate_per_1000"].idxmax(), "model"],
                "highest_rate": g["theft_rate_per_1000"].max(),
                "total_tracked_thefts_6mo": g["thefts_6mo"].sum(),
                "models_tracked": len(g),
            }),
            include_groups=False,
        )
        .reset_index()
    )
    return summary


def print_regional_report(df: pd.DataFrame, comparison: pd.DataFrame,
                          summary: pd.DataFrame):
    """Print the regional analysis report."""
    print("\n" + "=" * 70)
    print("REGIONAL THEFT RATE ANALYSIS")
    print("Auckland vs Canterbury vs Waikato vs Wellington vs Bay of Plenty")
    print("=" * 70)

    print("\n--- Regional Risk Summary ---\n")
    print(summary.to_string(index=False))

    print("\n--- Auckland vs Canterbury: Head-to-Head ---\n")
    cols = ["model", "akl_rate", "cant_rate", "rate_ratio_akl_cant", "higher_in"]
    display = comparison[cols].copy()
    display.columns = ["Model", "Auckland Rate", "Canterbury Rate",
                       "Ratio (Akl/Cant)", "Higher In"]
    print(display.to_string(index=False, float_format="%.1f"))

    # Aqua spotlight
    aqua_row = comparison[comparison["model"] == "Toyota Aqua"]
    if not aqua_row.empty:
        aqua = aqua_row.iloc[0]
        print(f"\n--- Toyota Aqua Regional Profile ---\n")
        print(f"  Auckland rate:    {aqua['akl_rate']:.1f} per 1,000")
        print(f"  Canterbury rate:  {aqua['cant_rate']:.1f} per 1,000")
        print(f"  Auckland is {aqua['rate_ratio_akl_cant']:.1f}x "
              f"Canterbury's rate")

    # Hilux spotlight (Canterbury's problem)
    hilux_row = comparison[comparison["model"] == "Toyota Hilux"]
    if not hilux_row.empty:
        hilux = hilux_row.iloc[0]
        print(f"\n--- Toyota Hilux Regional Profile ---\n")
        print(f"  Auckland rate:    {hilux['akl_rate']:.1f} per 1,000")
        print(f"  Canterbury rate:  {hilux['cant_rate']:.1f} per 1,000")
        if hilux["cant_rate"] > hilux["akl_rate"]:
            print(f"  Canterbury is {1/hilux['rate_ratio_akl_cant']:.1f}x "
                  f"Auckland's rate — confirming 'ute theft capital' status")

    # Courier spotlight
    courier_row = comparison[comparison["model"] == "Ford Courier"]
    if not courier_row.empty:
        courier = courier_row.iloc[0]
        print(f"\n--- Ford Courier Regional Profile ---\n")
        print(f"  Auckland rate:    {courier['akl_rate']:.1f} per 1,000")
        print(f"  Canterbury rate:  {courier['cant_rate']:.1f} per 1,000")

    print(f"\n--- Full Regional Rates (Top 10 per Region) ---\n")
    for region in ["Auckland", "Canterbury"]:
        region_data = df[df["region"] == region].nsmallest(
            10, "theft_rate_per_1000"
        ).sort_values("theft_rate_per_1000", ascending=False)
        # Actually get top 10 by rate
        region_data = df[df["region"] == region].nlargest(10, "theft_rate_per_1000")
        print(f"\n  {region}:")
        for _, row in region_data.iterrows():
            print(f"    {row['model']:25s} {row['theft_rate_per_1000']:6.1f} per 1,000"
                  f"  ({int(row['thefts_6mo'])} thefts/6mo)")


def main():
    df = compute_regional_theft_rates()
    comparison = compare_auckland_canterbury(df)
    summary = compute_regional_risk_summary(df)
    print_regional_report(df, comparison, summary)

    # Save outputs
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "regional_theft_rates.csv", index=False)
    comparison.to_csv(OUTPUT_DIR / "auckland_vs_canterbury.csv", index=False)
    print(f"\nResults saved to {OUTPUT_DIR}/")

    return df, comparison, summary


if __name__ == "__main__":
    main()
