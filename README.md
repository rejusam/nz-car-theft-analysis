# Is the Toyota Aqua Really NZ's Most Theft-Prone Car? A Base Rate Analysis

**A data science investigation into whether the Toyota Aqua's reputation as New Zealand's "most stolen car" reflects genuine theft vulnerability or a statistical artefact of fleet prevalence.**

## Background

Since 2022, the Toyota Aqua (Prius C) has been named New Zealand's most stolen car by AMI Insurance for four consecutive years. Media coverage consistently leads with raw theft counts, but this framing ignores a critical statistical question: **are Aquas stolen more often *because they're targeted*, or simply because there are so many on the road?**

This project applies rigorous base-rate correction, statistical testing, and confound modelling to separate genuine theft risk from fleet-size bias.

## Data Sources

| Source | Type | Period | Access |
|--------|------|--------|--------|
| AMI Insurance (IAG) | Theft claims + per-1000 insured rates | 2022–2025 | [ami.co.nz/hub/driving/2025-top-10-stolen-cars](https://www.ami.co.nz/hub/driving/2025-top-10-stolen-cars) |
| AA Insurance | Theft claims, top-10 models | 2024 | [aa.co.nz/membership/aa-directions/features](https://www.aa.co.nz/membership/aa-directions/features/) |
| NZ Police Stolen Vehicle Database | Row-level records (4,538 vehicles) | Oct 2021 – Apr 2022 | [kaggle.com/datasets/mattop/new-zealand-stolen-vehicles](https://www.kaggle.com/datasets/mattop/new-zealand-stolen-vehicles) |
| MoneyHub / NZ Police | 4,373 police-reported thefts, Jun–Dec 2025 | H2 2025 | [moneyhub.co.nz/most-stolen-cars.html](https://www.moneyhub.co.nz/most-stolen-cars.html) |
| NZTA Waka Kotahi | Motor Vehicle Register — fleet by make/model | Current | [nzta.govt.nz/resources/new-zealand-motor-vehicle-register-statistics](https://www.nzta.govt.nz/resources/new-zealand-motor-vehicle-register-statistics/new-zealand-vehicle-fleet-open-data-sets) |
| CarJam | Fleet counts by model (derived from MVR) | Current | [carjam.co.nz/nz-fleet](https://www.carjam.co.nz/nz-fleet/) |

## Methodology

### 1. Base Rate Correction
Raw theft counts are normalised by fleet size to compute **theft rate per 1,000 registered vehicles** for each model. This transforms the question from "which car is stolen most?" to "which car is most *likely* to be stolen?"

### 2. Statistical Hypothesis Testing
- **Chi-squared test**: Is the Toyota Aqua's theft rate significantly higher than expected under uniform risk?
- **Binomial test**: Given fleet proportion, is the observed theft count for the Aqua statistically anomalous?
- **Bootstrap confidence intervals**: Non-parametric 95% CIs on per-model theft rates.

### 3. Confound Analysis
Theft risk is not solely a function of "targeting". We model known confounders:
- **Vehicle age**: 70% of stolen cars are 15+ years old; Aquas entered NZ from ~2012.
- **Security features**: Older models lack encrypted immobilisers.
- **Parts market demand**: High-volume imports create robust second-hand parts ecosystems.
- **Geographic concentration**: Aqua fleet is concentrated in Auckland, also the theft capital.
- **Insurance selection bias**: AMI data reflects *insured* vehicles only; uninsured thefts are invisible.

### 4. Comparative Risk Ranking
We rank all top-20 models by adjusted theft rate and compare the Aqua against:
- Ford Courier (highest adjusted risk: 1 in 55 annually)
- Mazda Bounty (1 in 59)
- Toyota Hilux (drops from #1 raw to #12 adjusted)

### 5. NZ Police Stolen Vehicle Database Analysis
Row-level analysis of 4,538 police-reported stolen vehicle records provides an independent (non-insurance) view of theft patterns:
- **Model distribution**: Hilux and Courier dominate police records (#1 and #2); Aqua was #13 in the 2021–22 period before its subsequent rise
- **Vehicle age**: 92% of stolen vehicles are 10+ years old; the Aqua (median age 8 years at theft) is an outlier — far younger than typical targets
- **Temporal patterns**: Monday is the peak theft day; day-of-week distribution is statistically non-uniform (χ² p = 0.018)
- **Regional per-capita rates**: Gisborne (27.3 per 10,000 population) has 4× the per-capita theft rate of Auckland (6.5)

### 6. Cross-Source Validation
Four independent data sources are compared using Spearman rank correlations to test whether theft patterns are robust or source-dependent:
- **AMI vs AA Insurance (both 2024)**: ρ = 0.786 (p = 0.02) — strong agreement despite different policyholder pools
- **Insurance vs Police (2024 vs 2021–22)**: ρ ≈ 0.1 — weak correlation, expected given the 2-year temporal gap and the Aqua's rise post-2022
- Consensus finding: the Aqua's prominence is confirmed across all sources that cover the post-2022 period

### 7. Regional Breakdown
Theft rates are computed per model within each major region using NZTA fleet data aggregated by territorial authority. Auckland and Canterbury show starkly different risk profiles:
- **Auckland**: Dominated by imported passenger car theft (Aqua, Tiida, Demio)
- **Canterbury**: NZ's "ute theft capital" — Hilux, Courier, and Bounty rates exceed Auckland

### 9. Time Series Analysis (2022–2025)
Four years of AMI claims data reveal the trajectory of theft risk:
- National claims spiked in 2023 (ram-raid crisis: ~17,000 claims) then declined to ~9,000 in 2025
- The Aqua's share dropped from 11% (2022) to 8% (2025), though it has held rank #1 every year
- Absolute Aqua claims peaked in 2023 (~1,360) and have since declined ~47%

## Project Structure

```
nz-car-theft-analysis/
├── README.md
├── requirements.txt
├── Makefile                            # Reproducible pipeline
├── data/
│   ├── ami_theft_claims_2025.csv       # AMI top-10 + per-1000 rates
│   ├── ami_theft_claims_historical.csv # AMI claims 2022-2025 (4-year series)
│   ├── moneyhub_police_thefts_2025.csv # Police-sourced theft counts (6-month)
│   ├── police_stolen_vehicles_2022.csv # NZ Police row-level records (4,538)
│   ├── aa_insurance_claims_2024.csv    # AA Insurance top-10 (2024)
│   ├── police_rcvs_vehicle_theft.csv   # RCVS vehicle theft time series
│   ├── regional_thefts_2025.csv        # Theft counts by region and model
│   ├── nz_fleet_by_model.csv           # Registered vehicles per model
│   ├── nzta_fleet_regional_summary.csv # Fleet by model and region (from MVR)
│   └── data_sources.md                 # Provenance and collection notes
├── src/
│   ├── load_data.py                    # Data ingestion and validation
│   ├── base_rate_analysis.py           # Core theft-rate normalisation
│   ├── statistical_tests.py           # Hypothesis tests (chi-sq, binomial, bootstrap)
│   ├── confound_model.py              # Age, geography, security confound scoring
│   ├── regional_analysis.py           # Auckland vs Canterbury breakdown
│   ├── time_series_analysis.py        # AMI 2022-2025 trend analysis
│   ├── police_data_analysis.py        # NZ Police row-level analysis
│   ├── cross_source_validation.py     # Multi-source rank correlation
│   ├── nzta_fetcher.py                # NZTA MVR download and processing
│   ├── visualisation.py               # All plot generation (13 figures)
│   └── report_generator.py           # Markdown report builder
├── notebooks/
│   └── 01_exploratory_analysis.py     # Standalone exploration script
└── output/
    └── figures/                       # Generated plots
```

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd nz-car-theft-analysis
pip install -r requirements.txt

# Run the full pipeline
make all

# Or step-by-step
python src/base_rate_analysis.py
python src/statistical_tests.py
python src/confound_model.py
python src/visualisation.py
python src/report_generator.py
```

## Key Findings

The Aqua's theft rate of **54 per 1,000 insured vehicles** (AMI data) is nearly 4× the Corolla's rate (15 per 1,000), confirming it is **genuinely disproportionately targeted** — not merely a volume artefact. However, when police data is normalised by total fleet (not just insured fleet), older utes like the Ford Courier and Mazda Bounty show *higher* per-vehicle risk. The full picture is nuanced: the Aqua is both the most *frequently* stolen and among the most *disproportionately* targeted passenger cars, but it is not the highest-risk vehicle category in absolute terms.

**Cross-source validation**: Four independent data sources (AMI Insurance, AA Insurance, NZ Police records, MoneyHub/Police compiled stats) broadly agree. AMI and AA rankings correlate at ρ = 0.786 (p = 0.02) despite covering different policyholder pools. The weak correlation between 2024 insurance rankings and 2021–22 police data (ρ ≈ 0.1) is itself informative — it captures the Aqua's rise from #13 in police records to #1 in insurance claims, validating the temporal narrative.

**Vehicle age profile**: 92% of stolen vehicles in police data are 10+ years old, with a median age of 18 years. The Aqua is a stark outlier: its median theft age of 8 years suggests its vulnerability stems from specific factors (lack of encrypted immobilisers in early models, parts demand) rather than the general age-related decay that drives most vehicle theft.

**Regional divergence**: Auckland drives the Aqua's national theft numbers — its rate there substantially exceeds Canterbury, where utes dominate the theft landscape. Canterbury is NZ's "ute theft capital", with Hilux and Courier rates exceeding Auckland. Police data shows Gisborne has the highest per-capita theft rate (27.3 per 10,000), 4× Auckland's rate.

**Trending down**: National claims peaked at ~17,000 in 2023 (ram-raid crisis) and have since fallen to ~9,000 in 2025. The Aqua's absolute claims have declined in parallel, and its share of total claims has dropped from 11% to 8%.

## Updating with Live NZTA Data

The pre-computed fleet estimates can be replaced with authoritative counts from the full NZTA Motor Vehicle Register (5M+ rows, CC-BY 4.0):

```bash
# Download and process the full MVR dataset
make fetch-nzta

# Or specify a year range for lighter download
python src/nzta_fetcher.py --fetch-nzta --years 2005-2025
```

This updates `data/nzta_fleet_regional_summary.csv` and `data/nz_fleet_by_model.csv` with MVR-derived fleet counts broken down by territorial authority (mapped to regions). Re-run `make all` afterwards to regenerate all analysis outputs with the updated fleet data.

## License

MIT
