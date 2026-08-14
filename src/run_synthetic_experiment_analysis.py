from pathlib import Path
from math import sqrt

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ab_analysis import compare_proportions, sample_ratio_mismatch_p_value


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"
FIGURES_DIRECTORY = REPORTS_DIRECTORY / "figures"
ALPHA = 0.05
MINIMUM_RELATIVE_LIFT = 0.20
RENDER_GUARDRAIL_LIMIT = -0.002
SYNTHETIC_VARIANTS = {
    "Control": {
        "assigned_visitors": 75_000,
        "purchase_conversions": 480,
        "successful_renders": 74_775,
    },
    "Treatment": {
        "assigned_visitors": 75_000,
        "purchase_conversions": 592,
        "successful_renders": 74_738,
    },
}


def save_figure(file_name: str) -> None:
    FIGURES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURES_DIRECTORY / file_name, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> None:
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")

    control = SYNTHETIC_VARIANTS["Control"]
    treatment = SYNTHETIC_VARIANTS["Treatment"]
    primary_comparison = compare_proportions(
        control_successes=control["purchase_conversions"],
        control_total=control["assigned_visitors"],
        treatment_successes=treatment["purchase_conversions"],
        treatment_total=treatment["assigned_visitors"],
        alpha=ALPHA,
    )
    render_comparison = compare_proportions(
        control_successes=control["successful_renders"],
        control_total=control["assigned_visitors"],
        treatment_successes=treatment["successful_renders"],
        treatment_total=treatment["assigned_visitors"],
        alpha=ALPHA,
    )
    sample_ratio_p_value = sample_ratio_mismatch_p_value(
        control_total=control["assigned_visitors"],
        treatment_total=treatment["assigned_visitors"],
    )

    variant_results = pd.DataFrame(
        [
            {
                "variant": variant,
                "assigned_visitors": values["assigned_visitors"],
                "purchase_conversions": values["purchase_conversions"],
                "purchase_conversion_rate_pct": round(
                    100
                    * values["purchase_conversions"]
                    / values["assigned_visitors"],
                    3,
                ),
                "successful_renders": values["successful_renders"],
                "render_success_rate_pct": round(
                    100 * values["successful_renders"] / values["assigned_visitors"],
                    3,
                ),
            }
            for variant, values in SYNTHETIC_VARIANTS.items()
        ]
    )
    variant_results.to_csv(
        REPORTS_DIRECTORY / "phase_5_synthetic_ab_variant_results.csv",
        index=False,
    )

    primary_passes = (
        primary_comparison.confidence_interval_low > 0
        and primary_comparison.relative_lift >= MINIMUM_RELATIVE_LIFT
    )
    render_guardrail_passes = (
        render_comparison.confidence_interval_low > RENDER_GUARDRAIL_LIMIT
    )
    decision = (
        "Would meet the pre-specified decision rule in a real experiment"
        if primary_passes and render_guardrail_passes
        else "Would not meet the pre-specified decision rule in a real experiment"
    )

    analysis_checks = pd.DataFrame(
        [
            {
                "check": "Sample-ratio mismatch p-value",
                "value": round(sample_ratio_p_value, 6),
                "threshold": ">= 0.01",
                "result": "Pass" if sample_ratio_p_value >= 0.01 else "Fail",
            },
            {
                "check": "Primary absolute conversion difference (percentage points)",
                "value": round(primary_comparison.absolute_difference * 100, 3),
                "threshold": "> 0 with 95% CI fully positive",
                "result": "Pass"
                if primary_comparison.confidence_interval_low > 0
                else "Fail",
            },
            {
                "check": "Primary relative lift (%)",
                "value": round(primary_comparison.relative_lift * 100, 3),
                "threshold": f">= {MINIMUM_RELATIVE_LIFT * 100:.0f}",
                "result": "Pass"
                if primary_comparison.relative_lift >= MINIMUM_RELATIVE_LIFT
                else "Fail",
            },
            {
                "check": "Render-success difference (percentage points)",
                "value": round(render_comparison.absolute_difference * 100, 3),
                "threshold": f"95% CI lower bound > {RENDER_GUARDRAIL_LIMIT * 100:.1f}",
                "result": "Pass" if render_guardrail_passes else "Fail",
            },
        ]
    )
    analysis_checks.to_csv(
        REPORTS_DIRECTORY / "phase_5_synthetic_ab_checks.csv",
        index=False,
    )

    fig, ax = plt.subplots(figsize=(7, 4))
    plot_data = pd.DataFrame(
        {
            "variant": ["Control", "Treatment"],
            "conversion_rate_pct": [
                primary_comparison.control_rate * 100,
                primary_comparison.treatment_rate * 100,
            ],
            "error_pct": [
                1.96
                * sqrt(
                    primary_comparison.control_rate
                    * (1 - primary_comparison.control_rate)
                    / control["assigned_visitors"]
                )
                * 100,
                1.96
                * sqrt(
                    primary_comparison.treatment_rate
                    * (1 - primary_comparison.treatment_rate)
                    / treatment["assigned_visitors"]
                )
                * 100,
            ],
        }
    )
    ax.bar(
        plot_data["variant"],
        plot_data["conversion_rate_pct"],
        yerr=plot_data["error_pct"],
        capsize=5,
        color=["#7faac3", "#2f6f8f"],
    )
    ax.set_title("Synthetic A/B Scenario: Purchase Conversion")
    ax.set_xlabel("")
    ax.set_ylabel("Purchase conversion (%)")
    save_figure("phase_5_synthetic_ab_conversion.png")

    summary = f"""# Phase 5 Synthetic A/B Analysis

## Synthetic-data statement
**Every count in this report is deliberately fabricated for an analysis demonstration.** The RetailRocket dataset contains observational behavior only and did not provide experiment assignments, module exposures, or treatment outcomes.

## Scenario
The fixed scenario assigns 75,000 eligible visitors to each variant. It mirrors the Phase 4 design: control receives a global-popularity ranking and treatment receives a co-visitation ranking. The results are not sampled from customer data and do not estimate business impact.

## Data-quality check
The 50/50 assignment check has p = {sample_ratio_p_value:.6f}. With the pre-specified threshold of 0.01, the synthetic assignment passes the sample-ratio check.

## Intent-to-treat primary analysis
Control conversion is {primary_comparison.control_rate:.3%}; treatment conversion is {primary_comparison.treatment_rate:.3%}. The synthetic treatment-control difference is {primary_comparison.absolute_difference:.3%} ({primary_comparison.relative_lift:.1%} relative lift), with a two-sided 95% confidence interval of [{primary_comparison.confidence_interval_low:.3%}, {primary_comparison.confidence_interval_high:.3%}] and p = {primary_comparison.p_value:.6f}.

## Guardrail
The treatment-control render-success difference is {render_comparison.absolute_difference:.3%}. Its 95% confidence interval lower bound is {render_comparison.confidence_interval_low:.3%}, compared with the pre-specified non-inferiority limit of {RENDER_GUARDRAIL_LIMIT:.1%}.

## Decision exercise
{decision}. This statement describes only how the rule would be applied to the fabricated scenario. It is not a deployment recommendation and must not be represented as a live A/B-test outcome.
"""
    (REPORTS_DIRECTORY / "phase_5_synthetic_ab_summary.md").write_text(
        summary,
        encoding="utf-8",
    )

    print("Synthetic A/B demonstration reports and figure saved in reports/.")


if __name__ == "__main__":
    main()
