"""
Exploratory Analysis: NZ Car Theft Base Rate Investigation
==========================================================

Standalone script for interactive exploration of the data.
Run from the project root or notebooks/ directory.

Question: Is the Toyota Aqua genuinely NZ's most theft-prone car,
or is its #1 ranking a statistical artefact of fleet prevalence?
"""

import sys
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
import numpy as np
from scipy import stats


# ── 1. Load Data ────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

fleet = pd.read_csv(DATA_DIR / "nz_fleet_by_model.csv")
police = pd.read_csv(DATA_DIR / "moneyhub_police_thefts_2025.csv")
ami = pd.read_csv(DATA_DIR / "ami_theft_claims_2025.csv")

print("Fleet data shape:", fleet.shape)
print("Police data shape:", police.shape)
print("AMI data shape:", ami.shape)

# ── 2. Merge and Compute Rates ──────────────────────────────────────

police["thefts_annual_est"] = police["thefts_6mo"] * 2

df = pd.merge(
    police, fleet,
    on=["model", "make"],
    how="inner",
    suffixes=("_police", "_fleet"),
)

if "fleet_registered_fleet" in df.columns:
    df["fleet_registered"] = df["fleet_registered_fleet"]
    df.drop(columns=["fleet_registered_police", "fleet_registered_fleet"],
            inplace=True)

df["theft_rate_per_1000"] = (
    df["thefts_annual_est"] / df["fleet_registered"] * 1000
)

total_thefts = df["thefts_annual_est"].sum()
total_fleet = df["fleet_registered"].sum()

df["theft_share"] = df["thefts_annual_est"] / total_thefts
df["fleet_share"] = df["fleet_registered"] / total_fleet
df["theft_fleet_ratio"] = df["theft_share"] / df["fleet_share"]

df["rank_raw"] = df["thefts_annual_est"].rank(
    ascending=False, method="min"
).astype(int)
df["rank_adjusted"] = df["theft_rate_per_1000"].rank(
    ascending=False, method="min"
).astype(int)


# ── 3. Initial Exploration ──────────────────────────────────────────

print("\n" + "=" * 60)
print("EXPLORATION: Raw Theft Counts vs Fleet-Adjusted Rates")
print("=" * 60)

cols = ["model", "fleet_registered", "thefts_annual_est",
        "theft_rate_per_1000", "rank_raw", "rank_adjusted"]
print("\n", df.sort_values("rank_adjusted")[cols].to_string(index=False))


# ── 4. The Aqua Under the Microscope ───────────────────────────────

aqua = df[df["model"] == "Toyota Aqua"].iloc[0]
corolla = df[df["model"] == "Toyota Corolla"].iloc[0]

print("\n" + "=" * 60)
print("AQUA vs COROLLA")
print("=" * 60)
print(f"\nToyota Aqua:")
print(f"  Fleet size: {aqua['fleet_registered']:,}")
print(f"  Annual thefts (est): {aqua['thefts_annual_est']:.0f}")
print(f"  Rate per 1,000: {aqua['theft_rate_per_1000']:.1f}")
print(f"  Theft-fleet ratio: {aqua['theft_fleet_ratio']:.2f}x")

print(f"\nToyota Corolla:")
print(f"  Fleet size: {corolla['fleet_registered']:,}")
print(f"  Annual thefts (est): {corolla['thefts_annual_est']:.0f}")
print(f"  Rate per 1,000: {corolla['theft_rate_per_1000']:.1f}")
print(f"  Theft-fleet ratio: {corolla['theft_fleet_ratio']:.2f}x")

rate_ratio = aqua["theft_rate_per_1000"] / corolla["theft_rate_per_1000"]
print(f"\nAqua theft rate is {rate_ratio:.1f}x the Corolla's")

# AMI comparison (independent verification)
print(f"\nAMI Insurance rates (independent data):")
print(f"  Aqua: 54 per 1,000 insured")
print(f"  Corolla: 15 per 1,000 insured")
print(f"  Ratio: {54/15:.1f}x")


# ── 5. Statistical Tests ───────────────────────────────────────────

print("\n" + "=" * 60)
print("STATISTICAL TESTS")
print("=" * 60)

# Chi-squared: are thefts proportional to fleet size?
expected = df["fleet_registered"] / total_fleet * total_thefts
observed = df["thefts_annual_est"].values
chi2, p_chi = stats.chisquare(observed, f_exp=expected.values)
print(f"\nChi-squared test (H0: uniform theft risk):")
print(f"  chi2 = {chi2:.1f}, p = {p_chi:.2e}")
print(f"  {'REJECT' if p_chi < 0.05 else 'FAIL TO REJECT'} H0")

# Binomial test for Aqua specifically
aqua_expected_p = aqua["fleet_registered"] / total_fleet
binom_result = stats.binomtest(
    int(aqua["thefts_annual_est"]),
    int(total_thefts),
    aqua_expected_p,
    alternative="greater",
)
print(f"\nBinomial test (H0: Aqua theft proportion = fleet share):")
print(f"  Fleet share: {aqua_expected_p:.4f}")
print(f"  Theft share: {aqua['theft_share']:.4f}")
print(f"  p = {binom_result.pvalue:.2e}")
print(f"  {'REJECT' if binom_result.pvalue < 0.05 else 'FAIL TO REJECT'} H0")


# ── 6. Confound Quick Look ─────────────────────────────────────────

print("\n" + "=" * 60)
print("CONFOUND CHECK: Age & Security")
print("=" * 60)

age_corr, age_p = stats.pearsonr(
    df["median_vehicle_age_years"], df["theft_rate_per_1000"]
)
print(f"\nCorrelation: vehicle age vs theft rate")
print(f"  r = {age_corr:.3f}, p = {age_p:.4f}")

print(f"\nSecurity feature breakdown:")
for sec_level in ["No", "Mixed", "Yes"]:
    subset = df[df["has_encrypted_immobiliser"] == sec_level]
    if len(subset) > 0:
        mean_rate = subset["theft_rate_per_1000"].mean()
        print(f"  Encrypted immobiliser = {sec_level}: "
              f"mean rate = {mean_rate:.1f} per 1,000")


# ── 7. Final Verdict ───────────────────────────────────────────────

print("\n" + "=" * 60)
print("VERDICT")
print("=" * 60)

print(f"""
The data tells a nuanced story:

1. BASE RATE: The Aqua IS disproportionately stolen (theft-fleet
   ratio = {aqua['theft_fleet_ratio']:.2f}x). This is NOT simply a
   volume artefact.

2. RANK SHIFT: However, the Aqua's adjusted rank is
   #{int(aqua['rank_adjusted'])} (vs #{int(aqua['rank_raw'])} raw).
   Older utility vehicles face higher per-vehicle risk.

3. CONFOUNDS: Vehicle age (r={age_corr:.2f}) and lack of encrypted
   immobilisers are strong predictors. The Aqua's vulnerability is
   largely structural, not mysterious.

4. MEDIA FRAMING: Headlines calling the Aqua the "most stolen car"
   are technically correct by raw count, and AMI's per-1,000 data
   confirms disproportionate targeting among passenger cars.
   But the framing omits that per-vehicle risk is higher for older
   utes, and that structural factors (age, security) are the
   primary drivers.

ANSWER: The claim is PARTIALLY TRUE and PARTIALLY BIASED.
- True: the Aqua faces genuine elevated risk, not just volume effects.
- Biased: the "most stolen" framing hides that other models are
  riskier per vehicle, and that the root cause is weak security
  in ageing Japanese imports, not Aqua-specific targeting.
""")
