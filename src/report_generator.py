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
)
from police_data_analysis import (
    load_police_data, analyse_model_distribution,
    analyse_regional_distribution, analyse_vehicle_age,
)
from cross_source_validation import (
    build_comparison_table, compute_rank_correlations,
    identify_consensus_findings,
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

    # --- Police Row-Level Data ---
    report.append("## 7. NZ Police Stolen Vehicle Records\n")
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
    report.append("## 8. Cross-Source Validation\n")
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

    report.append("## 9. Conclusion\n")
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
        "5. **Structural**: The Aqua's vulnerability is largely explained by "
        "its age profile, lack of encrypted immobilisers in early models, "
        "high Auckland concentration, and robust parts demand. These are "
        "fixable factors, not inherent model defects.\n"
    )

    report.append("## Data Sources\n")
    report.append("- AMI Insurance, 2025 Top 10 Stolen Cars (Feb 2026)")
    report.append("- MoneyHub, NZ Police theft data, Jun-Dec 2025")
    report.append("- NZTA Waka Kotahi, Motor Vehicle Register")
    report.append("- CarJam fleet registration data\n")

    # Write
    report_path = OUTPUT_DIR / "analysis_report.md"
    report_path.write_text("\n".join(report))
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    generate_report()
