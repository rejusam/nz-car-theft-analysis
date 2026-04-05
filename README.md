# The Base Rate Trap

**Is the Toyota Aqua really New Zealand's most stolen car — or is that just what happens when you count without dividing?**

*A data-driven investigation across 21,000+ theft records, four independent sources, and the question the headlines never ask*

*[Reju Sam John](https://rejusamjohn.pages.dev/) | Auckland, New Zealand*

---

> **By the end of this investigation, you will know what happens when you add two words to a headline: *per what?***
>
> Those two words change the answer from "Toyota Aqua" to "Ford Courier." They reveal why Gisborne — not Auckland — is New Zealand's car theft capital per capita. And they give you a framework for questioning any statistic that counts without dividing.

---

Every February, AMI Insurance releases its annual list of New Zealand's most stolen cars. Every February, the Toyota Aqua — a compact hybrid hatchback common on Auckland's school-run circuit — takes the top spot. Four consecutive years now: 2022, 2023, 2024, 2025. The press coverage writes itself. *"Aqua tops list again." "NZ's most targeted car revealed."*

But here is the thing about counting: **the car with the most thefts is not necessarily the car most likely to be stolen.** Auckland has the most car thefts in New Zealand. Auckland also has the most cars. The meaningful question — the one the headline never asks — is what happens when you divide.

This investigation started with that question and followed a structured analytical workflow to answer it: observe the system, clean the noise, model the relationships, evaluate the model against independent evidence, and project what comes next.

---

## Observe the System

*Explore the data. Understand what exists before touching a model.*

The first step was assembling independent lines of evidence. No single source can answer the base rate question alone: insurance data excludes uninsured vehicles, police data covers limited time windows, and compiled statistics may carry editorial filtering. But four sources, cross-validated, can reach conclusions that no individual dataset could support.

| Source | Records | Period | What It Captures |
|--------|---------|--------|------------------|
| **AMI Insurance** (IAG NZ) | ~46,500 claims | 2022–2025 | Insured vehicle thefts |
| **AA Insurance** | 8,204 claims | 2024 | Insured vehicle thefts (different insurer) |
| **NZ Police Database** | 4,538 stolen vehicles | Oct 2021 – Apr 2022 | All reported thefts, row-level |
| **MoneyHub / NZ Police** | 4,373 thefts | Jun – Dec 2025 | Police-reported thefts, compiled |

Fleet denominators came from the NZTA Waka Kotahi Motor Vehicle Register — New Zealand's authoritative record of every registered vehicle, broken down by make, model, and territorial authority.

At face value, the sources tell different stories. AMI and AA both rank the Aqua #1 for 2024. But the NZ Police database — covering 2021–22, before the Aqua's rise — ranks it only **#13**, behind the Toyota Hilux (#1), Ford Courier (#2), and Mazda Demio (#3). That shift from #13 to #1 in roughly two years is itself a signal worth investigating.

![Raw vs Adjusted Rankings](output/figures/01_raw_vs_adjusted_ranking.png)
*When theft counts are adjusted for fleet size, the ranking changes dramatically. The Ford Courier rises 11 places; the Toyota Corolla drops 14.*

---

## Clean the Noise

*Handle inconsistencies across sources before they become false conclusions.*

Four sources built by different organisations, covering different periods, using different conventions. Before any analysis could proceed, three consistency problems needed solving.

**Naming.** Police records use uppercase abbreviations: `AQUA`, `HILUX`, `MARKX`. Insurance data uses full names: "Toyota Aqua", "Toyota Mark X". I built a standardisation mapping of 35 model name variants to enable matching across all four sources — every record had to land on the same key before a join could be trusted.

**Temporal alignment.** The four datasets share zero overlapping days. The police database ends in April 2022. AMI and AA report on calendar year 2024. MoneyHub covers mid-2025. Any cross-source comparison must account for the fact that New Zealand's theft landscape changed dramatically between these windows — the ram-raid crisis of 2023 doubled national claims from 8,500 to 17,000 before enforcement operations brought them back down.

**Denominators.** AMI reports theft rates per 1,000 *insured* vehicles — a metric that systematically undercounts risk for cheaper, older models (which are less likely to carry comprehensive insurance). For fleet-adjusted analysis, I normalised all rates against NZTA Motor Vehicle Register counts: the total registered population, regardless of insurance status.

The output: a unified comparison table with standardised model names, comparable rates, and rankings from each source — the foundation for every analysis that follows.

---

## Model the Relationships

*Fit a function. Quantify what drives theft beyond fleet size.*

### The denominator fix

When raw theft counts are divided by fleet size, the rankings transform:

| Model | Raw Rank | Adjusted Rank | Rate per 1,000 |
|-------|----------|---------------|----------------|
| Ford Courier | #12 | **#1** | 18.2 |
| Mazda Bounty | #13 | **#2** | 16.8 |
| Toyota Caldina | #15 | **#3** | 8.2 |
| Subaru Legacy | #6 | **#4** | 7.5 |
| Toyota Aqua | #3 | **#8** | 6.0 |
| Toyota Corolla | #2 | **#16** | 1.0 |

The Ford Courier — a utilitarian ute that has never appeared in an AMI headline — has a per-vehicle theft rate **three times** the Aqua's and **eighteen times** the Corolla's. But with only 5,060 on New Zealand roads, its raw count never breaks into the top 10.

The Aqua's drop from #3 to #8 matters. It remains disproportionately targeted — its theft-to-fleet ratio of 2.5x confirms it is stolen more than fleet size alone predicts — but it is not the highest-risk vehicle an individual owner faces. Not by a wide margin.

### What makes a car stealable?

Base rate correction answers one question but raises another: *why* do rates vary so dramatically? I modelled four structural confounders.

**Vehicle age.** In the police dataset, **92% of stolen vehicles were over 10 years old**, with a median age of 18 years. The Aqua, at a median theft age of just 7.5 years, is a stark outlier — significantly younger than typical targets. This suggests its vulnerability stems from specific technical factors, not the general decay that drives most vehicle theft.

**Security features.** Pre-2014 Aquas lack encrypted immobilisers. Models equipped with modern immobiliser technology (Toyota RAV4, Mazda CX-5, Ford Ranger) consistently show theft rates below 1.3 per 1,000 — a clear threshold effect.

**Geographic concentration.** The Aqua's fleet is heavily concentrated in Auckland, which accounts for 37% of all national vehicle thefts. More Aquas in Auckland means more exposure to the highest-theft environment in the country.

**Parts demand.** The Aqua's hybrid battery pack retails for $2,000–$4,000 on the second-hand market, making it a high-value stripping target. High-volume imports also create robust parts ecosystems.

I combined these into a **composite vulnerability index** and regressed it against observed theft rates:

> **Pearson r = 0.625, p = 0.004; Spearman ρ = 0.805, p < 0.001**

Structural vulnerability explains a substantial portion of theft rate variation across models. For the Aqua specifically, the model predicts a rate of 6.93 per 1,000 based on its vulnerability profile. The observed rate is 5.96 per 1,000. The residual — the "unexplained targeting" after accounting for all four confounders — is **-0.97 per 1,000**.

The Aqua is not being singled out. It is structurally vulnerable. And those vulnerabilities — age profile, missing immobilisers, Auckland concentration, parts value — are measurable and fixable.

![Confound Heatmap](output/figures/05_confound_heatmap.png)
*Vulnerability scores across models. Security (immobiliser status) and vehicle age are the strongest drivers of theft risk.*

---

## Evaluate How Well the Model Captures Reality

*Independent validation: do the sources agree?*

A model built on one dataset is a hypothesis. A model confirmed across independent datasets is evidence.

I computed Spearman rank correlations between every pair of sources to test whether they agree on which cars face the highest risk.

| Comparison | ρ | n | p-value | Result |
|-----------|---|---|---------|--------|
| AMI vs AA (both 2024) | **0.786** | 8 | 0.021 | Strong agreement |
| AMI vs Police (2024 vs 2021–22) | 0.127 | 10 | 0.726 | Weak |
| AA vs Police (2024 vs 2021–22) | -0.079 | 10 | 0.829 | Weak |

**The AMI–AA correlation is the critical finding.** These are rival insurers with different policyholder demographics, different pricing strategies, and no shared claims data. Yet their theft rankings correlate at ρ = 0.786 — strong agreement that the Aqua, Tiida, and Demio face the highest insured-vehicle theft risk. The Aqua's #1 position is not an artefact of any single insurer's portfolio.

**The weak insurance–police correlations are equally informative.** The police data covers 2021–22, when the Hilux and Courier dominated and the Aqua ranked only #13. By 2024, the Aqua had climbed to #1 in insurance rankings. This is not a contradiction — it is a **temporal signature**, capturing the Aqua's rapid ascent as early-import models aged into the security vulnerability window. The divergence validates the temporal narrative; it does not undermine the findings.

### Statistical confirmation

Beyond rank correlations, three classical tests validate the core results:

- **Chi-squared goodness-of-fit** (χ² = 2,934, df = 18, p < 0.001): Theft risk varies significantly by model. Fleet size alone does not explain the distribution.
- **Binomial exact test** (p = 3.4 x 10⁻⁴⁸): The Aqua's observed theft count is 2.5x what its fleet share predicts. This is not random variation.
- **Bootstrap 95% CIs** (n = 10,000 resamples): The Aqua's rate interval (5.0–6.9 per 1,000) does not overlap the Corolla's (0.9–1.2). The difference is real and measurable.

![Cross-Source Rankings](output/figures/12_cross_source_rankings.png)
*Ranking comparison across four independent sources. The Aqua's #1 insurance position is consistent across both AMI and AA; its lower police ranking reflects the earlier time period.*

---

## Predict New Outcomes

*What does the trajectory look like — and where is it heading?*

Four years of AMI data provide enough signal to track risk trajectories.

| Year | National Claims | Aqua Claims | Aqua Share | Rank |
|------|----------------|-------------|------------|------|
| 2022 | 8,492 | 934 | 11.0% | #1 |
| 2023 | 17,000 | 1,360 | 8.0% | #1 |
| 2024 | 12,000 | 960 | 8.0% | #1 |
| 2025 | 9,000 | 720 | 8.0% | #1 |

National claims doubled in 2023 during the ram-raid crisis, then fell 47% as enforcement intensified — including the NZ Police's dedicated ram-raid squad — and ram-raid-related thefts dropped by half. The Aqua's absolute claims have tracked this national decline almost exactly, falling from a peak of 1,360 to 720.

The Aqua's *share* of claims dropped from 11% to 8% in the first year and has held steady since. That plateau suggests its risk relative to other models is no longer worsening. Meanwhile, models rising in the rankings — Toyota Corolla (+6 places), Toyota Hilux (+4), Subaru Impreza (+2) — point to a broadening of the theft target base as other fleets age into the vulnerability window.

### The regional dimension

National statistics mask stark geographic divergence that matters more for prevention than any model-level ranking.

In **Canterbury** — NZ's ute theft capital — the Ford Courier's theft rate (32.6 per 1,000) is five times the Aqua's Canterbury rate (7.4 per 1,000). The Hilux rate in Canterbury (4.0 per 1,000) is double its Auckland rate (1.9 per 1,000). Different regions face fundamentally different theft profiles.

At the population level, **Gisborne's** per-capita theft rate of 27.3 per 10,000 population is **four times Auckland's** (6.5 per 10,000). The most frequently stolen *car* is an Auckland story. The most theft-affected *community* is not.

![Claims Time Series](output/figures/08_claims_time_series.png)
*National theft claims spiked during the 2023 ram-raid crisis, then declined as enforcement increased.*

![Vehicle Age Distribution](output/figures/11_vehicle_age_distribution.png)
*92% of police-recorded stolen vehicles were over 10 years old. The Aqua (median 7.5 years) is a clear outlier — younger, and vulnerable for different reasons.*

![Regional Theft Rates](output/figures/13_police_regional_percapita.png)
*Per-capita theft rates by region. Gisborne's rate dwarfs Auckland's — a pattern invisible in model-level national rankings.*

---

## The Verdict

The Toyota Aqua is New Zealand's most frequently stolen car. That is a fact supported by two independent insurers and four consecutive years of data. It is not a base rate artefact.

But the headline "most stolen car" carries an implication — *most dangerous to own* — that the data does not support.

**Per-vehicle risk.** The Ford Courier (18.2 per 1,000) faces three times the Aqua's theft rate. The Mazda Bounty is close behind. Neither has ever appeared in an AMI press release.

**Structural, not targeted.** A composite vulnerability model (r = 0.625, p = 0.004) shows the Aqua's theft rate is fully explained by its age profile, absent immobilisers, Auckland concentration, and parts demand. Its residual targeting score is slightly *negative*. It is not being singled out — it is exposed by fixable structural factors.

**Declining.** Aqua theft claims have fallen 47% from the 2023 peak. Its share has stabilised at 8%. Fleet turnover is gradually shrinking the population of vulnerable pre-2014 models.

**Regional.** Auckland drives the Aqua's national numbers. Canterbury is ute country. Gisborne's per-capita rate is four times Auckland's. A single national ranking obscures the geographic patterns that actually matter for policy and prevention.

**Cross-validated.** AMI and AA agree (ρ = 0.786, p = 0.021). Insurance and police rankings diverge — because they should, given a two-year temporal gap and a dramatically shifted theft landscape. The divergence is itself a finding, not a flaw.

---

The next time a headline tells you which car is "most stolen," ask the question it left out:

***Most stolen per what?***

---

### Data & Methodology

| Source | Access |
|--------|--------|
| AMI Insurance (IAG NZ) | Annual top-10 stolen vehicle reports, 2022–2025 |
| AA Insurance | 2024 theft claims report (8,204 claims, $34M payouts) |
| NZ Police Vehicle of Interest Database | 4,538 row-level records, Oct 2021 – Apr 2022 (CC0 Public Domain) |
| MoneyHub / NZ Police | Compiled theft statistics, Jun–Dec 2025 |
| NZTA Waka Kotahi Motor Vehicle Register | Fleet by make, model, territorial authority (CC-BY 4.0) |

**Statistical methods:** Chi-squared goodness-of-fit, binomial exact test, Poisson rate comparisons, non-parametric bootstrap confidence intervals (10,000 resamples), Spearman rank correlations for cross-source validation, OLS regression for composite vulnerability modelling.

**Reproducibility:** Full code and data pipeline available in this repository. Run `make all` to reproduce all analysis outputs, 13 figures, and the complete technical report.

*For the full technical report with detailed tables and all figures, see [analysis_report.md](output/analysis_report.md).*

*For project structure, pipeline commands, and reproducibility details, see [TECHNICAL.md](TECHNICAL.md).*
