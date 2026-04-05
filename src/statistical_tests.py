"""
Statistical Hypothesis Testing for NZ car theft analysis.

Tests whether the Toyota Aqua's theft rate is statistically significant
or could plausibly arise from chance under a uniform-risk model.

Tests implemented:
    1. Chi-squared goodness-of-fit
    2. Binomial exact test (per model)
    3. Bootstrap confidence intervals on theft rates
    4. Poisson rate test
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
from load_data import build_merged_dataset


def chi_squared_test(df: pd.DataFrame) -> dict:
    """
    Chi-squared goodness-of-fit test.

    H0: Thefts are distributed proportionally to fleet size
        (i.e., every car has equal probability of being stolen).
    H1: Some models are stolen at rates disproportionate to fleet size.

    If we reject H0, the theft distribution is NOT explained by
    fleet prevalence alone — some models are genuinely targeted.
    """
    total_thefts = df["thefts_annual_est"].sum()
    total_fleet = df["fleet_registered"].sum()

    # Expected thefts under H0: proportional to fleet share
    expected = df["fleet_registered"] / total_fleet * total_thefts
    observed = df["thefts_annual_est"].values

    chi2, p_value = stats.chisquare(observed, f_exp=expected.values)

    return {
        "test": "Chi-squared goodness-of-fit",
        "H0": "Thefts proportional to fleet size (uniform risk)",
        "chi2_statistic": round(chi2, 2),
        "degrees_of_freedom": len(df) - 1,
        "p_value": p_value,
        "reject_H0": p_value < 0.05,
    }


def binomial_test_aqua(df: pd.DataFrame) -> dict:
    """
    Exact binomial test for the Toyota Aqua.

    Under H0 (uniform risk), the probability of a random theft being
    an Aqua equals the Aqua's fleet share. We test whether the observed
    count significantly exceeds this expectation.
    """
    aqua = df[df["model"] == "Toyota Aqua"].iloc[0]

    total_thefts = int(df["thefts_annual_est"].sum())
    total_fleet = df["fleet_registered"].sum()

    aqua_thefts = int(aqua["thefts_annual_est"])
    aqua_fleet_share = aqua["fleet_registered"] / total_fleet

    result = stats.binomtest(
        aqua_thefts, total_thefts, aqua_fleet_share, alternative="greater"
    )

    return {
        "test": "Binomial exact test (Toyota Aqua)",
        "H0": f"P(theft is Aqua) = {aqua_fleet_share:.4f} (fleet share)",
        "observed_aqua_thefts": aqua_thefts,
        "expected_aqua_thefts": round(aqua_fleet_share * total_thefts, 1),
        "total_thefts": total_thefts,
        "p_value": result.pvalue,
        "reject_H0": result.pvalue < 0.05,
        "effect_size": round(aqua_thefts / (aqua_fleet_share * total_thefts), 2),
    }


def bootstrap_theft_rates(df: pd.DataFrame, n_bootstrap: int = 10000,
                          ci: float = 0.95) -> pd.DataFrame:
    """
    Non-parametric bootstrap confidence intervals for per-model theft rates.

    For each model, we resample from its observed theft count (Poisson model)
    and compute the theft rate, building a distribution of plausible rates.
    """
    results = []
    alpha = (1 - ci) / 2

    rng = np.random.default_rng(seed=42)

    for _, row in df.iterrows():
        # Treat observed 6-month count as a Poisson observation
        lam = row["thefts_6mo"]
        fleet = row["fleet_registered"]

        # Bootstrap: resample from Poisson(lambda=observed)
        samples = rng.poisson(lam=lam, size=n_bootstrap)
        # Annualise and compute rate
        rates = samples * 2 / fleet * 1000

        results.append({
            "model": row["model"],
            "rate_per_1000": round(row["theft_rate_per_1000"], 2),
            "ci_lower": round(np.percentile(rates, alpha * 100), 2),
            "ci_upper": round(np.percentile(rates, (1 - alpha) * 100), 2),
            "ci_width": round(
                np.percentile(rates, (1 - alpha) * 100) -
                np.percentile(rates, alpha * 100), 2
            ),
        })

    return pd.DataFrame(results)


def poisson_rate_test(df: pd.DataFrame, model_a: str,
                      model_b: str) -> dict:
    """
    Test whether two models have significantly different theft rates.

    Uses a Poisson rate comparison (E-test approximation).
    """
    a = df[df["model"] == model_a].iloc[0]
    b = df[df["model"] == model_b].iloc[0]

    # Rates: thefts per vehicle-year
    rate_a = a["thefts_annual_est"] / a["fleet_registered"]
    rate_b = b["thefts_annual_est"] / b["fleet_registered"]

    # Standard errors
    se_a = np.sqrt(a["thefts_annual_est"]) / a["fleet_registered"]
    se_b = np.sqrt(b["thefts_annual_est"]) / b["fleet_registered"]

    # Z-test for rate difference
    z = (rate_a - rate_b) / np.sqrt(se_a**2 + se_b**2)
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    return {
        "test": f"Poisson rate comparison: {model_a} vs {model_b}",
        "rate_a": round(rate_a * 1000, 2),
        "rate_b": round(rate_b * 1000, 2),
        "rate_ratio": round(rate_a / rate_b, 2),
        "z_statistic": round(z, 3),
        "p_value": p_value,
        "significant": p_value < 0.05,
    }


def run_all_tests(df: pd.DataFrame):
    """Execute and report all statistical tests."""
    print("\n" + "=" * 70)
    print("STATISTICAL HYPOTHESIS TESTING")
    print("=" * 70)

    # 1. Chi-squared
    chi2 = chi_squared_test(df)
    print(f"\n1. {chi2['test']}")
    print(f"   H0: {chi2['H0']}")
    print(f"   Chi² = {chi2['chi2_statistic']}, "
          f"df = {chi2['degrees_of_freedom']}, "
          f"p = {chi2['p_value']:.2e}")
    print(f"   → {'REJECT' if chi2['reject_H0'] else 'FAIL TO REJECT'} H0"
          f" at α=0.05")
    if chi2["reject_H0"]:
        print("   Interpretation: Theft risk varies significantly by model.")
        print("   Fleet size alone does NOT explain the theft distribution.")

    # 2. Binomial test
    binom = binomial_test_aqua(df)
    print(f"\n2. {binom['test']}")
    print(f"   H0: {binom['H0']}")
    print(f"   Observed: {binom['observed_aqua_thefts']} Aqua thefts")
    print(f"   Expected under H0: {binom['expected_aqua_thefts']}")
    print(f"   Effect size: {binom['effect_size']}x overrepresentation")
    print(f"   p = {binom['p_value']:.2e}")
    print(f"   → {'REJECT' if binom['reject_H0'] else 'FAIL TO REJECT'} H0")
    if binom["reject_H0"]:
        print("   Interpretation: The Aqua is stolen significantly more often")
        print("   than its fleet share predicts. This is NOT random.")

    # 3. Bootstrap CIs
    print(f"\n3. Bootstrap 95% Confidence Intervals (n=10,000)")
    boot = bootstrap_theft_rates(df)
    print(boot[["model", "rate_per_1000", "ci_lower", "ci_upper"]].to_string(
        index=False
    ))

    # 4. Pairwise rate comparisons
    print(f"\n4. Pairwise Poisson Rate Tests")
    pairs = [
        ("Toyota Aqua", "Toyota Corolla"),
        ("Toyota Aqua", "Toyota Hilux"),
        ("Ford Courier", "Toyota Aqua"),
    ]
    for a, b in pairs:
        result = poisson_rate_test(df, a, b)
        print(f"\n   {result['test']}")
        print(f"   Rates: {result['rate_a']} vs {result['rate_b']} per 1,000")
        print(f"   Ratio: {result['rate_ratio']}x, z = {result['z_statistic']}, "
              f"p = {result['p_value']:.2e}")
        sig = "Significant" if result["significant"] else "Not significant"
        print(f"   → {sig} difference")

    return chi2, binom, boot


def main():
    df = build_merged_dataset()

    # Need theft rate
    total_fleet = df["fleet_registered"].sum()
    df["theft_rate_per_1000"] = (
        df["thefts_annual_est"] / df["fleet_registered"] * 1000
    )

    chi2, binom, boot = run_all_tests(df)

    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    boot.to_csv(out_dir / "bootstrap_confidence_intervals.csv", index=False)
    print(f"\nBootstrap CIs saved to {out_dir / 'bootstrap_confidence_intervals.csv'}")


if __name__ == "__main__":
    main()
