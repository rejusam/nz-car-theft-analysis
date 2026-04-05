"""
Confound Analysis: What factors beyond fleet size explain theft rates?

The Aqua's disproportionate theft rate could reflect:
    1. Vehicle age (older = weaker security)
    2. Lack of encrypted immobiliser
    3. Parts market demand (popular model = valuable parts)
    4. Geographic concentration (Auckland)
    5. Insurance selection effects

This module quantifies each confound's contribution.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from load_data import build_merged_dataset


def compute_age_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score each model's age-related theft vulnerability.

    Logic: Older vehicles lack modern security features.
    70% of stolen cars in NZ are 15+ years old (MoneyHub data).
    """
    # Normalise median age to a 0-1 risk score
    max_age = df["median_vehicle_age_years"].max()
    df["age_risk_score"] = df["median_vehicle_age_years"] / max_age

    # Combine with % of fleet over 10 years old
    df["age_vulnerability"] = (
        0.5 * df["age_risk_score"] +
        0.5 * df["pct_over_10_years"] / 100
    )

    return df


def compute_security_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score each model's anti-theft security level.

    Encrypted immobilisers are the single strongest deterrent.
    Models without them are vastly easier to steal.
    """
    security_map = {"No": 0.0, "Mixed": 0.5, "Yes": 1.0}
    df["security_score"] = df["has_encrypted_immobiliser"].map(security_map)

    # Invert: higher = more vulnerable
    df["security_vulnerability"] = 1.0 - df["security_score"]

    return df


def compute_parts_demand_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Proxy for parts market demand.

    More vehicles on road = larger parts ecosystem = higher demand for
    stolen parts. This is a known driver: Japanese imports dominate NZ
    used parts markets.
    """
    max_fleet = df["fleet_registered"].max()
    df["parts_demand_proxy"] = df["fleet_registered"] / max_fleet

    return df


def compute_geographic_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Geographic concentration risk.

    Auckland has the highest theft volume. Models with high Auckland
    fleet concentration face elevated exposure.
    """
    max_auckland = df["pct_fleet_in_auckland"].max()
    df["geo_risk_score"] = df["pct_fleet_in_auckland"] / max_auckland

    return df


def compute_composite_vulnerability(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weighted composite vulnerability index.

    Weights reflect the estimated relative importance of each factor
    based on the literature and NZ-specific patterns:
        - Vehicle security: 35% (strongest predictor)
        - Vehicle age: 30% (highly correlated with security)
        - Geographic concentration: 20%
        - Parts demand: 15%
    """
    df["composite_vulnerability"] = (
        0.35 * df["security_vulnerability"] +
        0.30 * df["age_vulnerability"] +
        0.20 * df["geo_risk_score"] +
        0.15 * df["parts_demand_proxy"]
    )

    return df


def correlate_vulnerability_with_theft(df: pd.DataFrame) -> dict:
    """
    Test whether the composite vulnerability index correlates with
    actual observed theft rates.

    Strong correlation would suggest theft rates are largely
    explained by these structural factors rather than model-specific
    "targeting".
    """
    r, p = stats.pearsonr(
        df["composite_vulnerability"],
        df["theft_rate_per_1000"],
    )

    rho, p_spearman = stats.spearmanr(
        df["composite_vulnerability"],
        df["theft_rate_per_1000"],
    )

    return {
        "pearson_r": round(r, 3),
        "pearson_p": p,
        "spearman_rho": round(rho, 3),
        "spearman_p": p_spearman,
    }


def compute_residual_targeting(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute residual targeting score.

    After accounting for vulnerability factors, which models are STILL
    stolen more than predicted? High residuals suggest genuine
    model-specific targeting beyond structural explanations.
    """
    # Simple linear prediction from composite vulnerability
    slope, intercept, _, _, _ = stats.linregress(
        df["composite_vulnerability"],
        df["theft_rate_per_1000"],
    )

    df["predicted_rate"] = intercept + slope * df["composite_vulnerability"]
    df["residual_targeting"] = df["theft_rate_per_1000"] - df["predicted_rate"]
    df["residual_pct"] = (
        df["residual_targeting"] / df["predicted_rate"] * 100
    ).round(1)

    return df


def print_confound_report(df: pd.DataFrame, corr: dict):
    """Print the confound analysis report."""
    print("\n" + "=" * 70)
    print("CONFOUND ANALYSIS REPORT")
    print("What drives theft rates beyond fleet size?")
    print("=" * 70)

    print("\n--- Vulnerability Scores by Model ---\n")
    cols = ["model", "age_vulnerability", "security_vulnerability",
            "geo_risk_score", "parts_demand_proxy",
            "composite_vulnerability", "theft_rate_per_1000"]
    display = df.sort_values("composite_vulnerability", ascending=False)
    print(display[cols].to_string(index=False, float_format="%.3f"))

    print(f"\n--- Vulnerability-Theft Correlation ---\n")
    print(f"Pearson r  = {corr['pearson_r']}  (p = {corr['pearson_p']:.4f})")
    print(f"Spearman ρ = {corr['spearman_rho']}  "
          f"(p = {corr['spearman_p']:.4f})")

    if abs(corr["pearson_r"]) > 0.6:
        print("\nStrong correlation: theft rates are largely explained by")
        print("structural vulnerability factors (age, security, geography).")
    elif abs(corr["pearson_r"]) > 0.3:
        print("\nModerate correlation: vulnerability factors partially explain")
        print("theft rates, but model-specific factors also matter.")
    else:
        print("\nWeak correlation: structural factors alone do not explain")
        print("theft rate variation. Model-specific targeting is significant.")

    print(f"\n--- Residual Targeting (After Confound Adjustment) ---\n")
    cols_r = ["model", "theft_rate_per_1000", "predicted_rate",
              "residual_targeting", "residual_pct"]
    display_r = df.sort_values("residual_targeting", ascending=False)
    print(display_r[cols_r].head(10).to_string(
        index=False, float_format="%.2f"
    ))

    aqua = df[df["model"] == "Toyota Aqua"].iloc[0]
    print(f"\n--- Toyota Aqua Spotlight ---\n")
    print(f"Composite vulnerability: {aqua['composite_vulnerability']:.3f}")
    print(f"Predicted theft rate:    {aqua['predicted_rate']:.2f} per 1,000")
    print(f"Actual theft rate:       {aqua['theft_rate_per_1000']:.2f} per 1,000")
    print(f"Residual targeting:      {aqua['residual_targeting']:+.2f} per 1,000 "
          f"({aqua['residual_pct']:+.1f}%)")

    if aqua["residual_targeting"] > 0:
        print("\nThe Aqua is stolen MORE than its structural vulnerability")
        print("predicts, suggesting some degree of model-specific targeting.")
    else:
        print("\nThe Aqua's theft rate is fully explained by its structural")
        print("vulnerability profile. No additional targeting detected.")


def main():
    df = build_merged_dataset()

    # Compute all vulnerability dimensions
    df = compute_age_risk_score(df)
    df = compute_security_score(df)
    df = compute_parts_demand_proxy(df)
    df = compute_geographic_risk(df)
    df = compute_composite_vulnerability(df)

    # Test correlation
    corr = correlate_vulnerability_with_theft(df)

    # Compute residuals
    df = compute_residual_targeting(df)

    # Report
    print_confound_report(df, corr)

    # Save
    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "confound_analysis_results.csv", index=False)
    print(f"\nResults saved to {out_dir / 'confound_analysis_results.csv'}")

    return df, corr


if __name__ == "__main__":
    main()
