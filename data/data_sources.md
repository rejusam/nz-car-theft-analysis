# Data Sources and Provenance

## 1. AMI Insurance Theft Claims (2025)

**Source**: AMI Insurance (part of IAG New Zealand)
**URL**: https://www.ami.co.nz/hub/driving/2025-top-10-stolen-cars
**Published**: 3 February 2026
**Coverage**: Full calendar year 2025
**Records**: 9,000+ vehicle theft and attempted theft claims across 760+ makes/models

**Key metrics provided**:
- Percentage share of total theft claims by model
- Theft rate per 1,000 insured vehicles (Aqua: 54, Corolla: 15)
- Top-10 ranking by raw frequency
- Regional breakdown (Auckland, Canterbury, Waikato, Wellington, Bay of Plenty)

**Limitations**:
- Represents insured vehicles only (AMI/IAG policyholders)
- Does not capture uninsured vehicle thefts
- IAG is NZ's largest general insurer but not the total market
- Per-1,000 rates only published for Aqua and Corolla

## 2. MoneyHub / NZ Police Theft Data (H2 2025)

**Source**: MoneyHub analysis of NZ Police records
**URL**: https://www.moneyhub.co.nz/most-stolen-cars.html
**Published**: 22 December 2025
**Coverage**: 22 June 2025 – 20 December 2025 (182 days)
**Records**: 4,373 unique vehicle thefts (2 duplicates removed from 4,375)

**Key metrics**:
- Raw theft counts by model
- Fleet-adjusted theft rates using CarJam registration data
- Regional per-capita theft rates
- Vehicle age distribution of stolen cars

**Limitations**:
- 6-month window (annualised figures are extrapolations)
- Police-reported thefts only; some reported only to insurers
- Fleet numbers from CarJam (derived from NZTA MVR, may include deregistered vehicles)

## 3. NZTA Motor Vehicle Register

**Source**: NZ Transport Agency Waka Kotahi
**URL**: https://www.nzta.govt.nz/resources/new-zealand-motor-vehicle-register-statistics/new-zealand-vehicle-fleet-open-data-sets
**Format**: CSV files by vehicle year (5M+ rows total)
**Updated**: Monthly
**License**: CC-BY 4.0 International

**Fields used**: MAKE, MODEL, VEHICLE_YEAR, MOTIVE_POWER, TLA (territorial authority)

**How to fetch**: Download "Vehicle data – all vehicle years" from the NZTA Open Data Portal.
The data is split into yearly files (1990–current) or available as a single zipped CSV.

**Limitations**:
- Free-text fields subject to human error
- "Algorithmically cleaned" but not fully validated
- Includes vehicles that may not be actively used (e.g. stored, uninsured)

## 4. CarJam Fleet Data

**Source**: CarJam (derived from NZTA MVR)
**URL**: https://www.carjam.co.nz/nz-fleet/
**Used by**: MoneyHub for fleet-adjusted theft rate calculations

## 5. AMI Insurance Historical Data (2022-2025)

**Source**: AMI Insurance (IAG NZ) annual "Top 10 Stolen Cars" reports
**URLs**:
- 2022: https://www.ami.co.nz/hub/2022-top-10-stolen-cars
- 2023: https://www.ami.co.nz/hub/driving/2023-top-10-stolen-cars
- 2024: https://www.ami.co.nz/hub/driving/2024-top-10-stolen-cars
- 2025: https://www.ami.co.nz/hub/driving/2025-top-10-stolen-cars

**Published data points** (directly from AMI press releases):
- 2022: 8,492 total claims (+43% YoY); Aqua #1 at 11% of claims
- 2023: ~17,000 total claims; Aqua #1, Tiida #2, Corolla #3
- 2024: ~12,000 total claims; Aqua 8%, Corolla 6%, Tiida 5%
- 2025: 9,000+ claims across 760+ models; Aqua 8% (54/1000 insured), Corolla 7% (15/1000 insured)

**Limitations**:
- Per-1,000-insured rates only published for 2025 (Aqua and Corolla only)
- Estimated model claim counts for ranks 4-10 are derived from published percentages where available, interpolated for years/ranks without published percentages
- Regional leaders per year compiled from press coverage, not raw data

## 6. Regional Theft Data (H2 2025)

**Source**: Compiled from MoneyHub/NZ Police data and AMI regional reporting
**Regional shares** (published): Auckland ~37%, Canterbury ~17%, Waikato ~12%
**Per-capita rates** (published): Northland 14/10,000 (highest), Auckland 8/10,000

**How regional model-level counts were estimated**:
Model-level regional breakdowns are not published at the individual model×region level. The estimates in `regional_thefts_2025.csv` were constructed by:
1. Starting with published national model counts (MoneyHub)
2. Allocating to regions using published regional share percentages
3. Adjusting model-level allocation based on published regional leader data (e.g., "Canterbury is the ute theft capital")
4. Cross-checking against known fleet distribution by region

These are informed estimates, not exact police counts. The NZTA fetcher (`src/nzta_fetcher.py`) provides authoritative fleet-by-region data from the MVR when run.

## 7. AA Insurance Claims (2024)

**Source**: AA Insurance New Zealand
**Published**: 2025 (AA Directions feature article)
**Coverage**: Full calendar year 2024
**Records**: 8,204 theft and attempted theft claims; $34 million in payouts

**Key metrics provided**:
- Top-10 stolen models with rank
- Total claims count and financial cost
- Commentary on theft trends and vehicle security

**How data was compiled**:
Rankings and figures sourced from AA Insurance's published annual stolen vehicle report, cross-referenced with coverage in AA Directions magazine and NZ media.

**Limitations**:
- AA Insurance policyholders only (different demographic from AMI/IAG)
- Only top-10 models published; no per-1,000 rates
- AA membership skews toward certain demographics

## 8. NZ Police Stolen Vehicle Database (2021–2022)

**Source**: NZ Police Vehicle of Interest database, via Maven Analytics / Kaggle
**URL**: https://www.kaggle.com/datasets/mattop/new-zealand-stolen-vehicles
**Coverage**: 7 October 2021 – 6 April 2022 (6 months)
**Records**: 4,538 individual stolen vehicle records
**License**: CC0 Public Domain

**Fields used**: vehicle_id, vehicle_type, make, model, model_year, colour, date_stolen, region, region_population, region_density_km2

**Key advantages**:
- Row-level granularity (every other source provides only aggregates)
- Captures all reported thefts regardless of insurance status
- Includes non-car vehicle types (trailers, motorcycles, boats)
- Regional population data enables per-capita analysis

**Limitations**:
- 6-month window only; predates the 2023 ram-raid spike and the Aqua's rise to #1
- Only captures police-reported thefts (some thefts reported only to insurers)
- Model field uses uppercase abbreviations (AQUA, HILUX) requiring standardisation
- Temporal window means this data cannot confirm post-2022 rankings

## 9. NZ Police Recorded Crime Victims Statistics (RCVS)

**Source**: NZ Police via policedata.nz
**URL**: https://policedata.nz/table/rcvs
**Coverage**: 2017–2023 calendar years
**Offence codes**: O0811 (Unlawful Takes Motor Vehicle), O08 (Theft/Related)

**Key metrics**:
- Annual victimisation counts for vehicle theft offences
- National trend showing 2023 peak (ram-raid crisis) and subsequent decline

**Limitations**:
- Aggregate counts only; no model or vehicle-type breakdown
- Annual granularity (no monthly or weekly data)
- Most recent available year is 2023; 2024 data not yet published at time of collection

## Notes on Data Assembly

Fleet registration counts in `nz_fleet_by_model.csv` are compiled from:
- CarJam fleet data as cited by MoneyHub (Ford Courier: 5,060; Mazda Bounty: 5,112; Toyota Hilux: 153,884)
- NZTA open data for models not individually published
- Toyota Aqua fleet estimated from NZTA MVR filtering by MAKE=TOYOTA, MODEL containing "AQUA"

The `has_encrypted_immobiliser` field is a qualitative assessment:
- "No": Models predominantly pre-2014 without factory-fitted encrypted immobilisers
- "Mixed": Models spanning generations with and without modern security
- "Yes": Models predominantly post-2015 with encrypted key systems
