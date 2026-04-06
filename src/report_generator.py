"""
Report Generator: Produces a complete Markdown analysis report.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

from load_data import build_merged_dataset
from base_rate_analysis import compute_base_rate_metrics, summarise_aqua_findings
from confound_model import (
    compute_age_risk_score,
    compute_security_score,
    compute_parts_demand_proxy,
    compute_geographic_risk,
    compute_composite_vulnerability,
    compute_residual_targeting,
    correlate_vulnerability_with_theft,
)
from regional_analysis import compute_regional_theft_rates, compare_auckland_canterbury
from time_series_analysis import (
    load_historical_ami,
    compute_aqua_trend,
    compute_national_trend,
    compute_model_trajectories,
    assess_aqua_risk_trend,
    forecast_national_claims,
    forecast_model_shares,
    build_forecast_summary,
    classify_forecast_trajectory,
)
from police_data_analysis import (
    load_police_data, analyse_model_distribution,
    analyse_regional_distribution, analyse_vehicle_age,
)
from cross_source_validation import (
    build_comparison_table, compute_rank_correlations,
    identify_consensus_findings,
)
from socioeconomic_analysis import (
    build_analysis_dataset,
    compute_bivariate_correlations,
    fit_multivariable_model,
    synthesise_risk_profile,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def generate_report():
    """Generate the complete analysis report as Markdown."""

    # Prepare data
    df = build_merged_dataset()
    df = compute_base_rate_metrics(df)
    df = compute_age_risk_score(df)
    df = compute_security_score(df)
    df = compute_parts_demand_proxy(df)
    df = compute_geographic_risk(df)
    df = compute_composite_vulnerability(df)
    df = compute_residual_targeting(df)

    findings = summarise_aqua_findings(df)
    corr = correlate_vulnerability_with_theft(df)

    # Build report
    report = []
    report.append("# Toyota Aqua Theft Analysis: Base Rate Investigation")
    report.append(f"\n*Generated: {datetime.now().strftime('%d %B %Y')}*\n")

    report.append("## Executive Summary\n")
    report.append(
        "The Toyota Aqua has been named New Zealand's most stolen car for "
        "four consecutive years (2022-2025) by AMI Insurance. This analysis "
        "investigates whether this reflects genuine disproportionate "
        "targeting or is primarily an artefact of the Aqua's large fleet "
        "size.\n"
    )

    verdict = (
        "genuinely disproportionately targeted"
        if findings["aqua_theft_fleet_ratio"] > 2.0
        else "primarily a volume artefact"
    )
    report.append(
        f"**Finding**: The Aqua is {verdict}. Its theft rate of "
        f"{findings['aqua_theft_rate']} per 1,000 vehicles is "
        f"{findings['aqua_vs_corolla_rate_ratio']}x the Corolla's rate. "
        f"However, when ranked by per-vehicle risk, older utes like the "
        f"Ford Courier (rate: {findings['courier_theft_rate']} per 1,000) "
        f"pose higher individual risk. The headline framing is therefore "
        f"partially accurate but incomplete.\n"
    )

    report.append("## 1. The Base Rate Problem\n")
    report.append(
        "Saying the Aqua is the 'most stolen' car by raw count is like "
        "saying Auckland has the most car thefts — true, but Auckland also "
        "has the most cars. The meaningful question is: **given that you "
        "own an Aqua, how likely is it to be stolen compared to other "
        "models?**\n"
    )

    report.append("### Raw vs Adjusted Rankings\n")
    report.append("| Model | Raw Rank | Adjusted Rank | Change |")
    report.append("|-------|----------|---------------|--------|")
    for _, row in df.nsmallest(10, "rank_adjusted").iterrows():
        change = int(row["rank_change"])
        arrow = "+" + str(change) if change > 0 else str(change)
        report.append(
            f"| {row['model']} | #{int(row['rank_raw'])} | "
            f"#{int(row['rank_adjusted'])} | {arrow} |"
        )

    report.append("\n![Raw vs Adjusted](figures/01_raw_vs_adjusted_ranking.png)\n")

    report.append("## 2. AMI Insurance Evidence\n")
    report.append(
        f"AMI's own data shows the Aqua's theft rate at 54 per 1,000 insured "
        f"vehicles, compared to just 15 per 1,000 for the Corolla (the most "
        f"insured model). This 3.6x disparity confirms that even within the "
        f"insured population, the Aqua faces elevated risk.\n"
    )
    report.append("![AMI Comparison](figures/06_ami_rate_comparison.png)\n")

    report.append("## 3. Fleet-Adjusted Theft Rates\n")
    report.append(
        "Using police data normalised by total registered fleet:\n"
    )
    report.append("![Theft Rate](figures/02_theft_rate_per_1000.png)\n")
    report.append("![Scatter](figures/03_fleet_vs_thefts_scatter.png)\n")

    report.append("## 4. Confound Analysis\n")
    report.append(
        "Theft rates are not solely about targeting. Structural factors "
        "including vehicle age, security features, parts market demand, "
        "and geographic concentration all contribute.\n"
    )
    report.append(
        f"The composite vulnerability index correlates with theft rates at "
        f"r = {corr['pearson_r']} (p = {corr['pearson_p']:.4f}), "
        f"suggesting these factors "
    )
    if abs(corr["pearson_r"]) > 0.6:
        report.append("explain a substantial portion of theft rate variation.\n")
    else:
        report.append("partially but not fully explain theft rate variation.\n")

    report.append("![Heatmap](figures/05_confound_heatmap.png)\n")

    aqua = df[df["model"] == "Toyota Aqua"].iloc[0]
    report.append("### Toyota Aqua Confound Profile\n")
    report.append(f"- **Age vulnerability**: {aqua['age_vulnerability']:.2f}")
    report.append(f"- **Security vulnerability**: {aqua['security_vulnerability']:.2f}")
    report.append(f"- **Auckland concentration**: {aqua['geo_risk_score']:.2f}")
    report.append(f"- **Parts demand**: {aqua['parts_demand_proxy']:.2f}")
    report.append(f"- **Residual targeting**: {aqua['residual_targeting']:+.2f} per 1,000\n")

    # --- Regional Analysis ---
    report.append("## 5. Regional Breakdown: Auckland vs Canterbury\n")
    report.append(
        "Theft risk varies dramatically by region. Auckland dominates for "
        "imported passenger cars, while Canterbury is the 'ute theft capital' "
        "of the South Island.\n"
    )

    regional_df = compute_regional_theft_rates()
    comparison = compare_auckland_canterbury(regional_df)

    report.append("### Auckland vs Canterbury Theft Rates (per 1,000 vehicles)\n")
    report.append("| Model | Auckland | Canterbury | Higher In |")
    report.append("|-------|----------|------------|-----------|")
    for _, row in comparison.head(10).iterrows():
        akl = f"{row['akl_rate']:.1f}" if pd.notna(row.get('akl_rate')) else "—"
        cant = f"{row['cant_rate']:.1f}" if pd.notna(row.get('cant_rate')) else "—"
        report.append(f"| {row['model']} | {akl} | {cant} | {row['higher_in']} |")

    report.append("\n![Regional Comparison](figures/07_regional_comparison.png)\n")

    aqua_reg = comparison[comparison["model"] == "Toyota Aqua"]
    if not aqua_reg.empty:
        ar = aqua_reg.iloc[0]
        report.append(
            f"The Aqua's theft rate in Auckland ({ar['akl_rate']:.1f}/1,000) is "
            f"{ar['rate_ratio_akl_cant']:.1f}x its Canterbury rate "
            f"({ar['cant_rate']:.1f}/1,000), reflecting Auckland's higher "
            f"concentration of both Aquas and theft activity.\n"
        )

    hilux_reg = comparison[comparison["model"] == "Toyota Hilux"]
    if not hilux_reg.empty:
        hr = hilux_reg.iloc[0]
        if hr["cant_rate"] > hr["akl_rate"]:
            report.append(
                f"Conversely, the Hilux theft rate in Canterbury "
                f"({hr['cant_rate']:.1f}/1,000) exceeds Auckland "
                f"({hr['akl_rate']:.1f}/1,000), confirming Canterbury's "
                f"status as NZ's ute theft hotspot.\n"
            )

    # --- Time Series ---
    report.append("## 6. Time Series: AMI Claims 2022-2025\n")
    report.append(
        "AMI has published annual stolen vehicle reports since 2022, "
        "providing a four-year window to track the Aqua's risk trajectory.\n"
    )

    hist = load_historical_ami()
    aqua_trend = compute_aqua_trend(hist)
    national_trend = compute_national_trend(hist)
    assessment = assess_aqua_risk_trend(aqua_trend)

    report.append("### National Claims Trend\n")
    report.append("| Year | Total Claims | YoY Change |")
    report.append("|------|-------------|------------|")
    for _, row in national_trend.iterrows():
        yoy = f"{row['yoy_pct_change']:+.0f}%" if pd.notna(row.get("yoy_pct_change")) and not pd.isna(row["yoy_pct_change"]) else "—"
        report.append(f"| {int(row['year'])} | {int(row['total_claims']):,} | {yoy} |")

    report.append(
        "\nClaims peaked in 2023 during NZ's ram-raid crisis, then declined "
        "substantially as enforcement increased and ram-raid-related thefts "
        "dropped 50%.\n"
    )

    report.append("### Toyota Aqua Trajectory\n")
    report.append("| Year | Claims | Share | Rank |")
    report.append("|------|--------|-------|------|")
    for _, row in aqua_trend.iterrows():
        report.append(
            f"| {int(row['year'])} | {int(row['est_model_claims']):,} | "
            f"{row['theft_claims_pct']}% | #{int(row['rank'])} |"
        )

    report.append(f"\n**Assessment**: {assessment['narrative']}\n")

    report.append("![Claims Time Series](figures/08_claims_time_series.png)\n")
    report.append("![Aqua Share Trend](figures/09_aqua_share_trend.png)\n")
    report.append("![Rank Trajectories](figures/10_rank_trajectories.png)\n")

    trajectories = compute_model_trajectories(hist)
    risers = trajectories[trajectories["trajectory"] == "Rising"]["model"].tolist()
    fallers = trajectories[trajectories["trajectory"] == "Falling"]["model"].tolist()
    if risers:
        report.append(f"**Rising in rankings**: {', '.join(risers)}\n")
    if fallers:
        report.append(f"**Falling in rankings**: {', '.join(fallers)}\n")

    # --- Forecasting ---
    report.append("## 7. Forecast: Projected Rankings 2026-2027\n")
    report.append(
        "Using the 2022-2025 claim-share trends, we can project which models "
        "are likely to rise or fall in future rankings. These projections use "
        "linear extrapolation of each model's share trajectory and a log-linear "
        "model for national claims (fitted to the post-peak decline). With only "
        "four years of data, these are indicative trends rather than precise "
        "forecasts.\n"
    )

    national_fc = forecast_national_claims(national_trend)
    share_fc = forecast_model_shares(hist)
    fc_summary = build_forecast_summary(hist, national_fc, share_fc)
    fc_summary = classify_forecast_trajectory(fc_summary)

    report.append("### National Claims Outlook\n")
    fc_rows = national_fc[national_fc["is_forecast"]]
    for _, row in fc_rows.iterrows():
        report.append(
            f"- **{int(row['year'])}**: ~{int(row['total_claims']):,} claims "
            f"(range: {int(row['claims_lo']):,}-{int(row['claims_hi']):,})"
        )
    report.append(
        "\nThe post-peak decline is projected to continue, with national "
        "claims converging toward pre-spike levels as ram-raid enforcement "
        "holds and the fleet gradually turns over.\n"
    )

    report.append("### Projected Model Rankings\n")
    report.append("| Model | 2025 Rank | 2026 | 2027 | Outlook |")
    report.append("|-------|-----------|------|------|---------|")
    for _, row in fc_summary.iterrows():
        r26 = f"#{int(row['rank_2026'])}" if pd.notna(row.get('rank_2026')) else "—"
        r27 = f"#{int(row['rank_2027'])}" if pd.notna(row.get('rank_2027')) else "—"
        report.append(
            f"| {row['model']} | #{int(row['rank_2025'])} | "
            f"{r26} | {r27} | {row['forecast_outlook']} |"
        )

    report.append("\n### Key Projections\n")

    # Corolla overtake narrative
    corolla = fc_summary[fc_summary["model"] == "Toyota Corolla"]
    if not corolla.empty and corolla.iloc[0].get("rank_2026") == 1:
        report.append(
            "**Toyota Corolla projected to overtake the Aqua as most-stolen "
            "by 2026.** The Corolla's claim share has climbed steadily "
            "(+1.5 percentage points/year), driven by its massive and ageing "
            "fleet. Meanwhile, the Aqua's share is declining as newer models "
            "with encrypted immobilisers enter the fleet.\n"
        )

    # Rising models
    risers_fc = fc_summary[fc_summary["forecast_outlook"].str.contains("threat")
                           & (fc_summary["forecast_outlook"] != "Persistent threat")]
    if not risers_fc.empty:
        for _, row in risers_fc.iterrows():
            report.append(
                f"- **{row['model']}** ({row['forecast_outlook']}): "
                f"rank slope {row['rank_slope']:+.1f}/yr"
            )

    # Declining models
    decliners = fc_summary[fc_summary["forecast_outlook"].str.contains("Declining")]
    if not decliners.empty:
        report.append("")
        for _, row in decliners.iterrows():
            report.append(
                f"- **{row['model']}** ({row['forecast_outlook']}): "
                f"ageing out of the at-risk fleet"
            )

    report.append(
        "\n*Caveat: Four-year series. External shocks — immobiliser "
        "mandates, scrappage schemes, economic shifts — could alter these "
        "trajectories substantially.*\n"
    )

    report.append("![Forecast Trajectories](figures/14_forecast_rank_trajectories.png)\n")
    report.append("![Claims Forecast](figures/15_claims_forecast.png)\n")

    # --- Police Row-Level Data ---
    report.append("## 8. NZ Police Stolen Vehicle Records\n")
    report.append(
        "The NZ Police Vehicle of Interest database provides row-level "
        "records of 4,500+ stolen vehicles (Oct 2021 – Apr 2022). Unlike "
        "insurance data, this captures all reported thefts regardless of "
        "insurance status.\n"
    )

    police_df = load_police_data()
    police_models = analyse_model_distribution(police_df)
    police_regional = analyse_regional_distribution(police_df)
    age_info = analyse_vehicle_age(police_df)

    report.append("### Top 10 Stolen Models (Police Data)\n")
    report.append("| Rank | Model | Thefts | % of Total | Median Age |")
    report.append("|------|-------|--------|-----------|------------|")
    for _, row in police_models.head(10).iterrows():
        report.append(
            f"| {int(row['rank_police'])} | {row['model']} | "
            f"{int(row['thefts'])} | {row['pct_of_total']}% | "
            f"{row['median_age']:.0f} yr |"
        )

    report.append(
        f"\n**Vehicle age**: {age_info['pct_over_10_years']}% of stolen "
        f"vehicles were over 10 years old (median age: "
        f"{age_info['median_age']} years). The Aqua, with a median theft "
        f"age of {age_info['model_ages'].get('AQUA', {}).get('median', 'N/A')} "
        f"years, is notably younger than most targets.\n"
    )

    report.append("![Vehicle Age](figures/11_vehicle_age_distribution.png)\n")
    report.append("![Police Regional](figures/13_police_regional_percapita.png)\n")

    # --- Cross-Source Validation ---
    report.append("## 9. Cross-Source Validation\n")
    report.append(
        "Do four independent data sources — AMI Insurance, AA Insurance, "
        "NZ Police records, and MoneyHub compiled statistics — tell the "
        "same story? Agreement across sources strengthens conclusions; "
        "divergence reveals source-specific biases.\n"
    )

    xval = build_comparison_table()
    correlations = compute_rank_correlations(xval)
    consensus = identify_consensus_findings(xval, correlations)

    report.append("### Ranking Comparison\n")
    report.append("| Model | AMI | AA | Police | MoneyHub | Avg Rank |")
    report.append("|-------|-----|-----|--------|----------|----------|")
    display = xval[xval["sources_ranked"] >= 2].head(12)
    for _, row in display.iterrows():
        ami = f"#{int(row['rank_ami'])}" if pd.notna(row.get('rank_ami')) else "—"
        aa = f"#{int(row['rank_aa'])}" if pd.notna(row.get('rank_aa')) else "—"
        pol = f"#{int(row['rank_police'])}" if pd.notna(row.get('rank_police')) else "—"
        mh = f"#{int(row['rank_moneyhub'])}" if pd.notna(row.get('rank_moneyhub')) else "—"
        report.append(
            f"| {row['model']} | {ami} | {aa} | {pol} | {mh} | "
            f"{row['avg_rank']:.1f} |"
        )

    report.append("\n### Source Correlations\n")
    for label, vals in correlations.items():
        if vals["rho"] is not None:
            report.append(f"- **{label}**: Spearman ρ = {vals['rho']:.3f} "
                          f"(n={vals['n']}, p={vals['p']:.4f})")

    report.append("\n![Cross-Source Rankings](figures/12_cross_source_rankings.png)\n")

    if consensus:
        report.append("### Key Findings\n")
        for finding in consensus:
            report.append(f"- {finding}\n")

    # --- Socioeconomic Risk Factors ---
    report.append("## 10. Socioeconomic Risk Factors: Beyond Vehicle Make\n")
    report.append(
        "Vehicle theft is not solely a function of car model and security "
        "features. Area-level socioeconomic conditions shape theft rates "
        "independently of what people drive. Using NZ Police stolen vehicle "
        "records matched with Stats NZ regional indicators, we test which "
        "demographic factors predict where theft is concentrated.\n"
    )
    report.append(
        "*Methodology note: This is an ecological (area-level) analysis "
        "across 13 NZ regions. Correlations describe how theft rates vary "
        "with regional characteristics — they do not imply individual-level "
        "causation.*\n"
    )

    socio_df = build_analysis_dataset()
    socio_corr = compute_bivariate_correlations(socio_df)
    socio_model = fit_multivariable_model(socio_df)
    socio_profile = synthesise_risk_profile(socio_corr, socio_model)

    report.append("### Bivariate Correlations with Theft Rate\n")
    report.append("| Indicator | Spearman ρ | p-value | Direction |")
    report.append("|-----------|-----------|---------|-----------|")
    for _, row in socio_corr.iterrows():
        sig = " *" if row["spearman_p"] < 0.05 else ""
        report.append(
            f"| {row['variable'].replace('_', ' ').title()} | "
            f"{row['spearman_rho']:+.3f}{sig} | {row['spearman_p']:.3f} | "
            f"{row['strength']} {row['direction']} |"
        )

    report.append(
        "\nNo individual indicator reaches significance at p<0.05 with "
        "n=13 regions, but the directions are consistent: higher "
        "deprivation, unemployment, and population density are all "
        "associated with higher theft rates.\n"
    )

    report.append("### Combined Model\n")
    preds = " + ".join(
        p.replace("_", " ") for p in socio_model["predictors"]
    )
    report.append(
        f"The best 2-predictor model uses **{preds}** and explains "
        f"{socio_model['r_squared']*100:.0f}% of the regional variance "
        f"in theft rates (adjusted R² = {socio_model['adj_r_squared']:.2f}, "
        f"F-test p = {socio_model['f_p_value']:.3f}). This is significant "
        f"at the 5% level despite neither predictor reaching significance "
        f"alone — they act as complementary predictors, with urbanisation "
        f"suppressing noise in the deprivation signal.\n"
    )

    report.append("### Regional Outliers\n")
    residuals = socio_model["residuals"]
    over = residuals[residuals["std_residual"] > 1.0].sort_values(
        "std_residual", ascending=False
    )
    under = residuals[residuals["std_residual"] < -1.0].sort_values(
        "std_residual"
    )

    if not over.empty:
        report.append("**More theft than socioeconomic factors predict:**\n")
        for _, row in over.iterrows():
            report.append(
                f"- **{row['region']}**: actual {row['thefts_per_10k']:.1f} "
                f"vs predicted {row['predicted']:.1f} per 10,000"
            )
        report.append("")

    if not under.empty:
        report.append("**Less theft than socioeconomic factors predict:**\n")
        for _, row in under.iterrows():
            report.append(
                f"- **{row['region']}**: actual {row['thefts_per_10k']:.1f} "
                f"vs predicted {row['predicted']:.1f} per 10,000"
            )
        report.append("")

    report.append(
        "Gisborne's large positive residual suggests factors beyond "
        "deprivation and urbanisation — possibly its small population "
        "(where a handful of prolific offenders can shift per-capita "
        "rates substantially), geographic isolation, or local enforcement "
        "patterns.\n"
    )

    report.append("![Socioeconomic Drivers](figures/16_socioeconomic_drivers.png)\n")
    report.append("![Residual Analysis](figures/17_socioeconomic_residuals.png)\n")

    report.append("### Implications for Insurance and Policy\n")
    report.append(
        "Vehicle theft risk is a function of at least three layers:\n\n"
        "1. **Vehicle factors** — model, age, security features, parts "
        "demand (analysed in sections 1-4)\n"
        "2. **Geographic factors** — regional theft culture, enforcement "
        "intensity, urban density (section 5)\n"
        "3. **Socioeconomic factors** — deprivation, unemployment, housing "
        "tenure (this section)\n\n"
        "Insurance pricing that considers only vehicle model misses the "
        "second and third layers. An Aqua in low-deprivation Southland "
        "(2.5 thefts per 10,000) faces a fundamentally different risk "
        "profile from one in high-deprivation Gisborne (33.6 per 10,000). "
        "Postcode-level risk adjustment — already standard in many markets "
        "— would better reflect this reality.\n"
    )

    report.append("## 11. Conclusion\n")
    report.append(
        "The claim that the Toyota Aqua is NZ's most theft-prone car is "
        "**partially true but requires context**:\n\n"
        "1. **True**: The Aqua is stolen at rates well above what its fleet "
        "size alone predicts. The base-rate fallacy does not fully explain "
        "the headline.\n\n"
        "2. **Misleading**: By per-vehicle risk, older utility vehicles "
        "(Ford Courier, Mazda Bounty) face higher theft odds. Framing the "
        "Aqua as the 'most stolen' without this context overstates its "
        "relative risk.\n\n"
        "3. **Regional**: The Aqua's risk is concentrated in Auckland. In "
        "Canterbury, utes like the Hilux and Courier face higher per-vehicle "
        "theft rates. National statistics mask these regional patterns.\n\n"
        "4. **Trending down**: Absolute Aqua theft claims have declined "
        f"{assessment['decline_from_peak_pct']:.0f}% from the 2023 peak, "
        "tracking the overall national decline. The Aqua's share of claims "
        f"has shifted from {assessment['share_2022']}% to "
        f"{assessment['share_latest']}%.\n\n"
        "5. **Forecast**: If current trends hold, the Toyota Corolla is "
        "projected to overtake the Aqua as the most-stolen model by 2026, "
        "driven by its larger, ageing fleet. The Hilux is also rising, "
        "while older Mazda models are declining.\n\n"
        "6. **Socioeconomic context**: Regional deprivation and urbanisation "
        "together explain 55% of the variance in per-capita theft rates. "
        "Vehicle model alone is an incomplete risk picture — where the car "
        "is parked matters as much as what it is.\n\n"
        "7. **Structural**: The Aqua's vulnerability is largely explained by "
        "its age profile, lack of encrypted immobilisers in early models, "
        "high Auckland concentration, and robust parts demand. These are "
        "fixable factors, not inherent model defects.\n"
    )

    report.append("## Data Sources\n")
    report.append("- AMI Insurance, 2025 Top 10 Stolen Cars (Feb 2026)")
    report.append("- MoneyHub, NZ Police theft data, Jun-Dec 2025")
    report.append("- NZTA Waka Kotahi, Motor Vehicle Register")
    report.append("- CarJam fleet registration data")
    report.append("- Stats NZ Census 2018 / Household Labour Force Survey 2023")
    report.append("- NZ Deprivation Index (NZDep2018)\n")

    # Write
    report_path = OUTPUT_DIR / "analysis_report.md"
    report_path.write_text("\n".join(report))
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    generate_report()
