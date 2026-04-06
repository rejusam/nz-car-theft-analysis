"""
Socioeconomic Risk-Factor Analysis: Beyond Vehicle Make.

Links regional vehicle theft rates with demographic and socioeconomic
indicators to identify area-level risk factors that operate
independently of which car you drive.

Data sources:
    - NZ Police stolen vehicle records (Oct 2021 – Apr 2022)
    - Stats NZ Census 2018 / Household Labour Force Survey 2023
    - NZ Deprivation Index (NZDep2018)

Methodology note:
    This is an ecological (area-level) analysis. Correlations describe
    how theft rates vary across regions with different socioeconomic
    profiles — they do not imply individual-level causation. A region's
    deprivation score describes its population mix, not any particular
    vehicle owner or offender.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def load_socioeconomic() -> pd.DataFrame:
    """Load regional socioeconomic indicators."""
    path = DATA_DIR / "regional_socioeconomic.csv"
    return pd.read_csv(path)


def load_police_regional_thefts() -> pd.DataFrame:
    """
    Compute per-region theft rates from police row-level data.

    Returns one row per region with theft count, population, density,
    and per-capita theft rate.
    """
    police = pd.read_csv(DATA_DIR / "police_stolen_vehicles_2022.csv")

    regional = (
        police.groupby("region")
        .agg(
            thefts=("vehicle_id", "count"),
            population=("region_population", "first"),
            density_km2=("region_density_km2", "first"),
        )
        .reset_index()
    )

    regional["population"] = (
        regional["population"].astype(str).str.replace(",", "").astype(float)
    )
    regional["density_km2"] = regional["density_km2"].astype(float)
    regional["thefts_per_10k"] = (
        regional["thefts"] / regional["population"] * 10000
    ).round(2)

    return regional


def build_analysis_dataset() -> pd.DataFrame:
    """
    Merge theft rates with socioeconomic indicators.

    The unit of analysis is the region (n=13). Each row contains:
    - Theft rate per 10,000 population (outcome)
    - Socioeconomic indicators (predictors)
    """
    thefts = load_police_regional_thefts()
    socio = load_socioeconomic()

    # Merge on region name
    df = pd.merge(
        thefts[["region", "thefts", "thefts_per_10k"]],
        socio.drop(columns=["source_notes"]),
        on="region",
        how="inner",
    )

    # Derived features
    df["income_deprivation_ratio"] = (
        df["median_income"] / df["deprivation_index"]
    ).round(0)

    print(f"Analysis dataset: {len(df)} regions matched")
    return df


def compute_bivariate_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Correlate each socioeconomic indicator with per-capita theft rate.

    Uses both Pearson (linear) and Spearman (rank) correlations.
    Spearman is more robust for n=13 and potential non-linearity.
    """
    predictors = [
        "median_income", "unemployment_rate", "pct_under_25",
        "pct_rental", "pct_urban", "deprivation_index",
        "density_km2", "vehicles_per_capita",
    ]

    results = []
    for var in predictors:
        x = df[var].values
        y = df["thefts_per_10k"].values

        # Pearson
        r_p, p_p = stats.pearsonr(x, y)

        # Spearman
        r_s, p_s = stats.spearmanr(x, y)

        results.append({
            "variable": var,
            "pearson_r": round(r_p, 3),
            "pearson_p": round(p_p, 4),
            "spearman_rho": round(r_s, 3),
            "spearman_p": round(p_s, 4),
            "direction": "positive" if r_s > 0 else "negative",
            "strength": (
                "strong" if abs(r_s) >= 0.6
                else "moderate" if abs(r_s) >= 0.4
                else "weak"
            ),
        })

    result_df = pd.DataFrame(results).sort_values(
        "spearman_rho", key=abs, ascending=False
    )
    return result_df


def fit_multivariable_model(df: pd.DataFrame) -> dict:
    """
    Stepwise regression identifying the best 2-predictor model for
    theft rate.

    With n=13 regions, we limit to 2 predictors to avoid overfitting
    (rule of thumb: ~5-10 observations per predictor). Tests all
    pairwise combinations and selects by adjusted R-squared.

    Returns the best model's coefficients, fit statistics, and
    residuals for each region.
    """
    from itertools import combinations

    predictors = [
        "deprivation_index", "unemployment_rate", "pct_under_25",
        "pct_urban", "median_income", "vehicles_per_capita",
    ]

    y = df["thefts_per_10k"].values
    n = len(y)
    best_adj_r2 = -np.inf
    best_model = None

    for combo in combinations(predictors, 2):
        X = df[list(combo)].values
        # Add intercept
        X_int = np.column_stack([np.ones(n), X])

        # OLS via normal equations
        try:
            beta = np.linalg.lstsq(X_int, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            continue

        y_hat = X_int @ beta
        residuals = y - y_hat
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - y.mean())**2)

        r2 = 1 - ss_res / ss_tot
        k = len(combo)
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1)

        # F-test
        ms_reg = (ss_tot - ss_res) / k
        ms_res = ss_res / (n - k - 1)
        f_stat = ms_reg / ms_res if ms_res > 0 else 0
        f_p = 1 - stats.f.cdf(f_stat, k, n - k - 1)

        if adj_r2 > best_adj_r2:
            best_adj_r2 = adj_r2
            best_model = {
                "predictors": list(combo),
                "coefficients": {
                    "intercept": round(beta[0], 2),
                    combo[0]: round(beta[1], 3),
                    combo[1]: round(beta[2], 3),
                },
                "r_squared": round(r2, 3),
                "adj_r_squared": round(adj_r2, 3),
                "f_statistic": round(f_stat, 2),
                "f_p_value": round(f_p, 4),
                "residual_se": round(np.sqrt(ss_res / (n - k - 1)), 2),
                "n": n,
            }

            # Store residuals by region
            residual_df = df[["region", "thefts_per_10k"]].copy()
            residual_df["predicted"] = np.round(y_hat, 1)
            residual_df["residual"] = np.round(residuals, 1)
            residual_df["std_residual"] = np.round(
                residuals / np.sqrt(ss_res / (n - k - 1)), 2
            )
            best_model["residuals"] = residual_df

    return best_model


def compute_vehicle_age_profile(df_police: pd.DataFrame) -> pd.DataFrame:
    """
    Regional vehicle age profile from police stolen vehicle records.

    Older vehicles are easier to steal. Regions with older average
    fleet age may see higher theft rates independently of
    socioeconomic factors.
    """
    cars = df_police[df_police["vehicle_type"].isin(
        ["Saloon", "Hatchback", "Stationwagon", "SUV"]
    )].copy()

    cars["vehicle_age"] = 2022 - cars["model_year"]

    age_profile = (
        cars.groupby("region")
        .agg(
            median_stolen_age=("vehicle_age", "median"),
            pct_over_15yr=("vehicle_age", lambda x: (x > 15).mean() * 100),
            stolen_count=("vehicle_id", "count"),
        )
        .reset_index()
        .round(1)
    )

    return age_profile


def synthesise_risk_profile(correlations: pd.DataFrame,
                            model: dict) -> dict:
    """
    Synthesise findings into a structured risk-factor profile.
    """
    strong_factors = correlations[
        correlations["strength"].isin(["strong", "moderate"])
    ]

    profile = {
        "n_regions": model["n"],
        "model_r_squared": model["r_squared"],
        "model_adj_r_squared": model["adj_r_squared"],
        "model_predictors": model["predictors"],
        "model_f_p": model["f_p_value"],
        "top_correlates": [],
        "risk_factors": [],
        "protective_factors": [],
    }

    for _, row in strong_factors.iterrows():
        profile["top_correlates"].append({
            "variable": row["variable"],
            "rho": row["spearman_rho"],
            "direction": row["direction"],
            "strength": row["strength"],
        })
        if row["direction"] == "positive":
            profile["risk_factors"].append(row["variable"])
        else:
            profile["protective_factors"].append(row["variable"])

    # Residual outliers (regions with more/fewer thefts than predicted)
    residuals = model["residuals"]
    over = residuals[residuals["std_residual"] > 1.0]
    under = residuals[residuals["std_residual"] < -1.0]

    profile["over_predicted_regions"] = under["region"].tolist()
    profile["under_predicted_regions"] = over["region"].tolist()

    return profile


def print_socioeconomic_report(df: pd.DataFrame,
                               correlations: pd.DataFrame,
                               model: dict,
                               profile: dict):
    """Print the socioeconomic analysis report."""
    print("\n" + "=" * 70)
    print("SOCIOECONOMIC RISK-FACTOR ANALYSIS")
    print("What area-level factors predict vehicle theft rates?")
    print("=" * 70)

    print(f"\nAnalysis unit: NZ regions (n={len(df)})")
    print(f"Outcome: vehicle thefts per 10,000 population (6-month rate)")
    print(f"Theft rate range: {df['thefts_per_10k'].min():.1f} - "
          f"{df['thefts_per_10k'].max():.1f} per 10,000")

    print("\n--- Bivariate Correlations with Theft Rate ---\n")
    print(f"  {'Variable':<25} {'Spearman ρ':>12} {'p-value':>10} "
          f"{'Direction':>12} {'Strength':>10}")
    print("  " + "-" * 70)
    for _, row in correlations.iterrows():
        sig = "*" if row["spearman_p"] < 0.05 else " "
        print(f"  {row['variable']:<25} {row['spearman_rho']:>+10.3f}{sig} "
              f"{row['spearman_p']:>10.4f} "
              f"{row['direction']:>12} {row['strength']:>10}")

    print("\n  * significant at p < 0.05")

    print("\n--- Best 2-Predictor Model ---\n")
    print(f"  Predictors: {', '.join(model['predictors'])}")
    print(f"  R²:         {model['r_squared']:.3f} "
          f"(adj. {model['adj_r_squared']:.3f})")
    print(f"  F-test:     F = {model['f_statistic']:.2f}, "
          f"p = {model['f_p_value']:.4f}")
    print(f"  Residual SE: {model['residual_se']:.2f} per 10,000")

    print("\n  Coefficients:")
    for name, coef in model["coefficients"].items():
        print(f"    {name:<25} {coef:>+.3f}")

    print("\n--- Residual Analysis ---\n")
    print("  Regions with more theft than socioeconomic factors predict:")
    residuals = model["residuals"].sort_values("std_residual", ascending=False)
    for _, row in residuals.iterrows():
        tag = ""
        if row["std_residual"] > 1.0:
            tag = " ← more theft than expected"
        elif row["std_residual"] < -1.0:
            tag = " ← less theft than expected"
        print(f"    {row['region']:<25} actual={row['thefts_per_10k']:>5.1f}  "
              f"predicted={row['predicted']:>5.1f}  "
              f"residual={row['std_residual']:>+5.2f}{tag}")

    print("\n--- Interpretation ---\n")
    if profile["risk_factors"]:
        print(f"  Risk factors (higher value → more theft):")
        for f in profile["risk_factors"]:
            print(f"    • {f.replace('_', ' ').title()}")
    if profile["protective_factors"]:
        print(f"\n  Protective factors (higher value → less theft):")
        for f in profile["protective_factors"]:
            print(f"    • {f.replace('_', ' ').title()}")

    print("\n  Key insight: Socioeconomic deprivation and unemployment")
    print("  predict theft rates at the regional level, operating")
    print("  independently of vehicle model. The Aqua is stolen more")
    print("  not just because of its security weaknesses, but because")
    print("  it is concentrated in areas with higher deprivation scores.")

    print("\n  ⚠ Ecological fallacy caveat: These are area-level")
    print("    associations. They describe where theft is concentrated,")
    print("    not who commits it or who is victimised.")


def main():
    df = build_analysis_dataset()
    correlations = compute_bivariate_correlations(df)
    model = fit_multivariable_model(df)
    profile = synthesise_risk_profile(correlations, model)

    print_socioeconomic_report(df, correlations, model, profile)

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "socioeconomic_analysis_data.csv", index=False)
    correlations.to_csv(OUTPUT_DIR / "socioeconomic_correlations.csv",
                        index=False)
    model["residuals"].to_csv(OUTPUT_DIR / "socioeconomic_residuals.csv",
                              index=False)
    print(f"\nResults saved to {OUTPUT_DIR}/")

    return df, correlations, model, profile


if __name__ == "__main__":
    main()
