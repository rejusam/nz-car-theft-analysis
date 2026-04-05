"""
Cross-Source Validation: Are the data sources telling the same story?

Compares theft rankings and patterns across four independent sources:
    1. AMI Insurance claims (2022-2025)
    2. AA Insurance claims (2024)
    3. NZ Police stolen vehicle records (2021-2022)
    4. MoneyHub / NZ Police compiled data (H2 2025)

Agreement across sources strengthens conclusions. Disagreement
reveals source-specific biases (e.g., insurance portfolio composition,
reporting rates, geographic coverage).

This is the methodological backbone of the project: any single source
can be questioned, but convergent findings across independent sources
cannot be easily dismissed.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def load_ami_rankings() -> pd.DataFrame:
    """Load AMI Insurance 2024 rankings for comparison year."""
    df = pd.read_csv(DATA_DIR / "ami_theft_claims_historical.csv")
    ami_2024 = df[df["year"] == 2024][["model", "rank"]].copy()
    ami_2024.rename(columns={"rank": "rank_ami"}, inplace=True)
    return ami_2024


def load_aa_rankings() -> pd.DataFrame:
    """Load AA Insurance 2024 rankings."""
    df = pd.read_csv(DATA_DIR / "aa_insurance_claims_2024.csv")
    aa = df[["model", "rank"]].copy()

    # Standardise model names to match project convention
    name_map = {
        "Toyota Mark X": "Toyota Mark X",
        "Subaru Forester": "Subaru Forester",
    }
    aa["model"] = aa["model"].map(lambda x: name_map.get(x, x))
    aa.rename(columns={"rank": "rank_aa"}, inplace=True)
    return aa


def load_police_rankings() -> pd.DataFrame:
    """Load police stolen vehicle database rankings (2021-22)."""
    path = OUTPUT_DIR / "police_model_ranking.csv"
    if not path.exists():
        from police_data_analysis import load_police_data, analyse_model_distribution
        df = load_police_data()
        model_dist = analyse_model_distribution(df)
        model_dist.to_csv(path, index=False)

    df = pd.read_csv(path)
    # Use standardised names for matching
    police = df[df["model_std"].notna()][
        ["model_std", "rank_police", "thefts"]
    ].copy()
    police.rename(columns={"model_std": "model", "thefts": "thefts_police"},
                  inplace=True)
    return police


def load_moneyhub_rankings() -> pd.DataFrame:
    """Load MoneyHub/Police H2 2025 raw theft rankings."""
    df = pd.read_csv(DATA_DIR / "moneyhub_police_thefts_2025.csv")
    # model column already has full names like "Ford Courier"
    df["rank_moneyhub"] = df["thefts_6mo"].rank(
        ascending=False, method="min"
    ).astype(int)
    mh = df[["model", "rank_moneyhub"]].copy()
    return mh


def build_comparison_table() -> pd.DataFrame:
    """
    Merge all four source rankings into a single comparison table.

    Models are matched by standardised name. Missing ranks mean the
    model didn't appear in that source's top-N.
    """
    ami = load_ami_rankings()
    aa = load_aa_rankings()
    police = load_police_rankings()
    moneyhub = load_moneyhub_rankings()

    # Start with all unique models across sources
    all_models = set()
    for src in [ami, aa, police, moneyhub]:
        all_models.update(src["model"].tolist())

    comparison = pd.DataFrame({"model": sorted(all_models)})
    comparison = comparison.merge(ami, on="model", how="left")
    comparison = comparison.merge(aa, on="model", how="left")
    comparison = comparison.merge(police, on="model", how="left")
    comparison = comparison.merge(moneyhub, on="model", how="left")

    # Count how many sources rank this model
    rank_cols = ["rank_ami", "rank_aa", "rank_police", "rank_moneyhub"]
    comparison["sources_ranked"] = comparison[rank_cols].notna().sum(axis=1)

    # Average rank across available sources
    comparison["avg_rank"] = comparison[rank_cols].mean(axis=1).round(1)

    comparison.sort_values("avg_rank", inplace=True)
    comparison.reset_index(drop=True, inplace=True)

    return comparison


def compute_rank_correlations(comparison: pd.DataFrame) -> dict:
    """
    Compute pairwise rank correlations between sources.

    High Spearman rho = sources agree on relative risk ordering.
    Low rho = sources diverge, suggesting portfolio/coverage bias.
    """
    pairs = [
        ("rank_ami", "rank_aa", "AMI vs AA (both 2024)"),
        ("rank_ami", "rank_police", "AMI vs Police (2024 vs 2021-22)"),
        ("rank_aa", "rank_police", "AA vs Police (2024 vs 2021-22)"),
        ("rank_ami", "rank_moneyhub", "AMI vs MoneyHub (2024 vs H2 2025)"),
    ]

    results = {}
    for col_a, col_b, label in pairs:
        # Need models present in both rankings
        mask = comparison[col_a].notna() & comparison[col_b].notna()
        subset = comparison[mask]

        if len(subset) < 4:
            results[label] = {"n": len(subset), "rho": None, "p": None}
            continue

        rho, p = stats.spearmanr(subset[col_a], subset[col_b])
        results[label] = {
            "n": len(subset),
            "rho": round(rho, 3),
            "p": round(p, 4),
        }

    return results


def compute_source_summary() -> dict:
    """
    Summary statistics for each data source.

    Highlights the differences in coverage, time period, and scope
    that explain ranking discrepancies.
    """
    return {
        "AMI Insurance": {
            "type": "Insurance claims",
            "period": "2024 calendar year",
            "total_claims": "~12,000",
            "scope": "AMI/IAG policyholders only",
            "bias": "Excludes uninsured vehicles; portfolio skews toward urban, newer vehicles",
        },
        "AA Insurance": {
            "type": "Insurance claims",
            "period": "2024 calendar year",
            "total_claims": "8,204",
            "scope": "AA Insurance policyholders only",
            "bias": "Different policyholder demographics than AMI; AA skews toward AA members",
        },
        "NZ Police Database": {
            "type": "Police-reported thefts (row-level)",
            "period": "Oct 2021 – Apr 2022 (6 months)",
            "total_records": "4,538 (2,958 cars)",
            "scope": "All reported thefts regardless of insurance",
            "bias": "Only captures reported thefts; 6-month window predates 2023 spike",
        },
        "MoneyHub / Police": {
            "type": "Compiled police statistics",
            "period": "Jun – Dec 2025 (6 months)",
            "total_thefts": "4,373",
            "scope": "Police-reported thefts, all vehicles",
            "bias": "Compiled by MoneyHub, may include editorial filtering",
        },
    }


def identify_consensus_findings(comparison: pd.DataFrame,
                                 correlations: dict) -> list:
    """
    Synthesise cross-source findings into consensus statements.
    """
    findings = []

    # Check if Aqua is top-ranked across sources
    aqua = comparison[comparison["model"] == "Toyota Aqua"]
    if not aqua.empty:
        a = aqua.iloc[0]
        ranks = []
        if pd.notna(a.get("rank_ami")): ranks.append(("AMI", int(a["rank_ami"])))
        if pd.notna(a.get("rank_aa")): ranks.append(("AA", int(a["rank_aa"])))
        if pd.notna(a.get("rank_police")): ranks.append(("Police", int(a["rank_police"])))

        if all(r <= 5 for _, r in ranks):
            findings.append(
                f"CONSENSUS: Toyota Aqua ranks in top 5 across all sources "
                f"({', '.join(f'{s} #{r}' for s, r in ranks)}). "
                f"Its prominence is not an artefact of any single insurer's portfolio."
            )

    # Check AMI vs AA agreement
    ami_aa = correlations.get("AMI vs AA (both 2024)", {})
    if ami_aa.get("rho") and ami_aa["rho"] > 0.7:
        findings.append(
            f"AGREEMENT: AMI and AA Insurance rankings are strongly correlated "
            f"(Spearman ρ = {ami_aa['rho']}, n = {ami_aa['n']}), despite "
            f"covering different policyholder pools."
        )
    elif ami_aa.get("rho") and ami_aa["rho"] < 0.5:
        findings.append(
            f"DIVERGENCE: AMI and AA rankings show weak correlation "
            f"(ρ = {ami_aa['rho']}), suggesting insurer portfolio composition "
            f"matters. Rankings should not be taken at face value from any "
            f"single insurer."
        )

    # Check police vs insurance agreement
    for label, vals in correlations.items():
        if "Police" in label and vals.get("rho"):
            if vals["rho"] > 0.5:
                findings.append(
                    f"VALIDATION: {label} shows moderate-to-strong agreement "
                    f"(ρ = {vals['rho']}), suggesting insurance rankings "
                    f"reflect genuine theft patterns, not just claims behaviour."
                )

    return findings


def print_cross_source_report(comparison, correlations, findings):
    """Print the cross-source validation report."""
    print("\n" + "=" * 70)
    print("CROSS-SOURCE VALIDATION")
    print("Do independent data sources tell the same story?")
    print("=" * 70)

    print("\n--- Source Summary ---\n")
    summaries = compute_source_summary()
    for source, info in summaries.items():
        print(f"  {source}:")
        for k, v in info.items():
            print(f"    {k}: {v}")
        print()

    print("--- Ranking Comparison (Top Models) ---\n")
    display = comparison[comparison["sources_ranked"] >= 2].head(20)
    cols = ["model", "rank_ami", "rank_aa", "rank_police",
            "rank_moneyhub", "avg_rank"]
    print(display[cols].to_string(index=False, na_rep="—"))

    print("\n--- Rank Correlations ---\n")
    for label, vals in correlations.items():
        if vals["rho"] is not None:
            sig = "***" if vals["p"] < 0.01 else "**" if vals["p"] < 0.05 else ""
            print(f"  {label}: ρ = {vals['rho']:+.3f}  "
                  f"(n={vals['n']}, p={vals['p']}){sig}")
        else:
            print(f"  {label}: insufficient overlap (n={vals['n']})")

    print("\n--- Consensus Findings ---\n")
    for i, finding in enumerate(findings, 1):
        print(f"  {i}. {finding}")

    if not findings:
        print("  No strong consensus findings identified.")


def main():
    comparison = build_comparison_table()
    correlations = compute_rank_correlations(comparison)
    findings = identify_consensus_findings(comparison, correlations)

    print_cross_source_report(comparison, correlations, findings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(OUTPUT_DIR / "cross_source_comparison.csv", index=False)
    print(f"\nResults saved to {OUTPUT_DIR / 'cross_source_comparison.csv'}")

    return comparison, correlations, findings


if __name__ == "__main__":
    main()
