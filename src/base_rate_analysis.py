"""
Base Rate Analysis: Normalising theft counts by fleet prevalence.

The central question: Does the Toyota Aqua's #1 theft ranking survive
adjustment for how many Aquas are on the road?

This module computes:
    1. Raw theft share (the headline statistic)
    2. Fleet share (what proportion of the fleet is each model)
    3. Theft-to-fleet ratio (the key diagnostic)
    4. Theft rate per 1,000 vehicles (the corrected metric)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from load_data import build_merged_dataset, load_ami_data


def compute_base_rate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add base-rate-corrected columns to the merged dataset.

    New columns:
        - theft_share: proportion of all thefts attributed to this model
        - fleet_share: proportion of tracked fleet that is this model
        - theft_fleet_ratio: theft_share / fleet_share
          (>1 = disproportionately stolen, <1 = under-represented in thefts)
        - rank_raw: ranking by absolute theft count
        - rank_adjusted: ranking by theft rate per 1,000
    """
    total_thefts = df["thefts_annual_est"].sum()
    total_fleet = df["fleet_registered"].sum()

    df["theft_share"] = df["thefts_annual_est"] / total_thefts
    df["fleet_share"] = df["fleet_registered"] / total_fleet

    # The key metric: how much more (or less) is this model stolen
    # relative to what we'd expect from its fleet share alone?
    df["theft_fleet_ratio"] = df["theft_share"] / df["fleet_share"]

    # Rankings
    df["rank_raw"] = df["thefts_annual_est"].rank(
        ascending=False, method="min"
    ).astype(int)
    df["rank_adjusted"] = df["theft_rate_per_1000"].rank(
        ascending=False, method="min"
    ).astype(int)

    df["rank_change"] = df["rank_raw"] - df["rank_adjusted"]

    return df


def summarise_aqua_findings(df: pd.DataFrame) -> dict:
    """Extract key metrics for the Toyota Aqua vs comparison models."""
    aqua = df[df["model"] == "Toyota Aqua"].iloc[0]
    corolla = df[df["model"] == "Toyota Corolla"].iloc[0]
    courier = df[df["model"] == "Ford Courier"].iloc[0]
    hilux = df[df["model"] == "Toyota Hilux"].iloc[0]

    findings = {
        "aqua_raw_rank": int(aqua["rank_raw"]),
        "aqua_adjusted_rank": int(aqua["rank_adjusted"]),
        "aqua_theft_rate": round(aqua["theft_rate_per_1000"], 1),
        "aqua_theft_fleet_ratio": round(aqua["theft_fleet_ratio"], 2),
        "aqua_fleet_size": int(aqua["fleet_registered"]),
        "aqua_annual_thefts": int(aqua["thefts_annual_est"]),
        "corolla_theft_rate": round(corolla["theft_rate_per_1000"], 1),
        "corolla_fleet_size": int(corolla["fleet_registered"]),
        "aqua_vs_corolla_rate_ratio": round(
            aqua["theft_rate_per_1000"] / corolla["theft_rate_per_1000"], 1
        ),
        "courier_theft_rate": round(courier["theft_rate_per_1000"], 1),
        "courier_adjusted_rank": int(courier["rank_adjusted"]),
        "hilux_raw_rank": int(hilux["rank_raw"]),
        "hilux_adjusted_rank": int(hilux["rank_adjusted"]),
        "hilux_rank_drop": int(hilux["rank_raw"] - hilux["rank_adjusted"]),
    }

    return findings


def print_base_rate_report(df: pd.DataFrame, findings: dict):
    """Print a formatted base-rate analysis report."""
    print("\n" + "=" * 70)
    print("BASE RATE ANALYSIS REPORT")
    print("Is the Toyota Aqua genuinely the most theft-prone car in NZ?")
    print("=" * 70)

    print("\n--- Ranking Comparison: Raw vs Adjusted ---\n")
    cols = ["model", "fleet_registered", "thefts_annual_est",
            "theft_rate_per_1000", "rank_raw", "rank_adjusted", "rank_change"]
    display = df[cols].copy()
    display.columns = ["Model", "Fleet", "Thefts/yr", "Rate/1000",
                       "Raw #", "Adj #", "Change"]
    print(display.to_string(index=False))

    print(f"\n--- Key Findings ---\n")

    print(f"Toyota Aqua:")
    print(f"  Raw rank: #{findings['aqua_raw_rank']}  →  "
          f"Adjusted rank: #{findings['aqua_adjusted_rank']}")
    print(f"  Theft rate: {findings['aqua_theft_rate']} per 1,000 vehicles")
    print(f"  Theft-to-fleet ratio: {findings['aqua_theft_fleet_ratio']}x "
          f"(>{1.0} = disproportionately targeted)")
    print(f"  Rate is {findings['aqua_vs_corolla_rate_ratio']}x "
          f"the Corolla's rate")

    print(f"\nFord Courier:")
    print(f"  Adjusted rank: #{findings['courier_adjusted_rank']} "
          f"(highest risk per vehicle)")
    print(f"  Theft rate: {findings['courier_theft_rate']} per 1,000 vehicles")

    print(f"\nToyota Hilux:")
    print(f"  Raw rank: #{findings['hilux_raw_rank']}  →  "
          f"Adjusted rank: #{findings['hilux_adjusted_rank']}")
    print(f"  Rank drops {abs(findings['hilux_rank_drop'])} places "
          f"after adjustment")

    print(f"\n--- Verdict ---\n")
    if findings["aqua_theft_fleet_ratio"] > 2.0:
        print("CONCLUSION: The Toyota Aqua IS genuinely disproportionately")
        print(f"targeted (theft-fleet ratio = "
              f"{findings['aqua_theft_fleet_ratio']}x).")
        print("The 'most stolen car' claim is NOT purely a base-rate artefact.")
    else:
        print("CONCLUSION: The Toyota Aqua's high theft count is primarily")
        print("explained by its fleet prevalence.")

    if findings["aqua_adjusted_rank"] > 1:
        print(f"\nHOWEVER: After fleet-size adjustment, the Aqua drops to")
        print(f"rank #{findings['aqua_adjusted_rank']}. Models like the")
        print(f"Ford Courier pose higher per-vehicle risk. The headline")
        print(f"'most stolen car' framing is therefore PARTIALLY misleading.")
    print()


def main():
    df = build_merged_dataset()
    df = compute_base_rate_metrics(df)
    findings = summarise_aqua_findings(df)
    print_base_rate_report(df, findings)

    # Save enriched dataset
    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = df.sort_values("rank_adjusted")
    out.to_csv(out_dir / "base_rate_results.csv", index=False)
    print(f"Results saved to {out_dir / 'base_rate_results.csv'}")

    return df, findings


if __name__ == "__main__":
    main()
