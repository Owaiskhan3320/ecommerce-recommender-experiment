from pathlib import Path

import duckdb
import pandas as pd

from experiment_design import calculate_required_days, calculate_sample_size_per_variant


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "analytics.duckdb"
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"
HOLDOUT_MINIMUM_DAYS = 14
ALPHA = 0.05
POWER = 0.80
VARIANT_ALLOCATION = 0.50
RELATIVE_MDE_VALUES = [0.15, 0.20, 0.30]


def load_planning_baseline(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[int, int, int]:
    result = connection.execute(
        """
        SELECT
            SUM(has_view::INTEGER) AS view_sessions,
            SUM(has_transaction_after_cart::INTEGER) AS purchase_sessions,
            DATE_DIFF(
                'day',
                CAST(MIN(session_start_time) AS DATE),
                CAST(MAX(session_start_time) AS DATE)
            ) + 1 AS observed_days
        FROM fct_sessions
        """
    ).fetchone()

    return tuple(int(value) for value in result)


def build_planning_table(
    baseline_rate: float,
    eligible_exposures_per_day: float,
) -> pd.DataFrame:
    rows = []
    for relative_mde in RELATIVE_MDE_VALUES:
        plan = calculate_sample_size_per_variant(
            baseline_rate=baseline_rate,
            relative_mde=relative_mde,
            alpha=ALPHA,
            power=POWER,
        )
        days_required = calculate_required_days(
            sample_size_per_variant=plan.sample_size_per_variant,
            eligible_exposures_per_day=eligible_exposures_per_day,
            variant_allocation=VARIANT_ALLOCATION,
        )
        rows.append(
            {
                "relative_mde_pct": relative_mde * 100,
                "baseline_conversion_rate_pct": baseline_rate * 100,
                "target_conversion_rate_pct": plan.target_rate * 100,
                "alpha": ALPHA,
                "power": POWER,
                "sample_size_per_variant": plan.sample_size_per_variant,
                "total_sample_size": plan.sample_size_per_variant * 2,
                "historical_view_sessions_per_day": round(
                    eligible_exposures_per_day,
                    1,
                ),
                "estimated_days_to_sample_size": days_required,
                "minimum_planned_days": max(days_required, HOLDOUT_MINIMUM_DAYS),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(DATABASE_PATH), read_only=True)
    try:
        view_sessions, purchase_sessions, observed_days = load_planning_baseline(
            connection
        )
    finally:
        connection.close()

    baseline_rate = purchase_sessions / view_sessions
    view_sessions_per_day = view_sessions / observed_days
    planning_table = build_planning_table(
        baseline_rate=baseline_rate,
        eligible_exposures_per_day=view_sessions_per_day,
    )
    planning_table.to_csv(
        REPORTS_DIRECTORY / "phase_4_sample_size_scenarios.csv",
        index=False,
    )

    recommended_plan = planning_table.loc[
        planning_table["relative_mde_pct"] == 20.0
    ].iloc[0]
    design = f"""# Phase 4 Recommender Experiment Design

## Status
**Planning only. No A/B test was run for this project.** The historical clickstream is used to set directional sample-size scenarios; it is not treated as causal evidence.

## Decision question
Does a co-visitation recommendation module improve purchase conversion compared with a global-popularity module when both occupy the same product-page location?

## Variants
- **Control:** the top 10 globally popular, currently valid items in the recommendation slot.
- **Treatment:** the top 10 valid co-visitation candidates for the item currently viewed.
- Keep placement, number of tiles, visual treatment, lazy-loading behavior, and tracking identical. This isolates ranking logic rather than the effect of adding a new page component.

## Eligibility and assignment
- Qualify a visitor on their first product-detail-page view where the treatment can return 10 valid candidate items.
- Exclude bots and internal traffic using rules frozen before analysis. Keep failed renders in the assigned population and report them as a guardrail.
- Assign eligible visitors 50/50 by a stable hash of an anonymous visitor or device identifier. Persist the assignment across visits.
- Analyze only the first qualified assignment per visitor, by assigned variant (intent to treat), even if the module fails to render or the visitor does not click a recommendation.

## Metrics
- **Primary:** purchase conversion in the assignment session, defined as a transaction after the first qualified assignment divided by eligible assigned visitors.
- **Secondary:** recommendation click-through rate, add-to-cart rate after exposure, and revenue per exposed visitor if order value is available.
- **Guardrails:** module-render success, recommendation latency, product-page exit rate, and any support or error-rate signals available in production.

## Hypotheses and decision rule
- **Null hypothesis:** treatment and control have equal primary conversion rates.
- **Alternative:** the conversion rates differ. Use a two-sided 5% test and report the absolute conversion difference with a 95% confidence interval.
- Ship only if the primary confidence interval is entirely above zero, guardrails remain within pre-set limits, and the result meets the chosen minimum detectable effect. Do not stop early for a favorable interim result.

## Sample-size scenarios
The planning proxy is the historical strict view-to-transaction rate: {purchase_sessions:,} purchase sessions from {view_sessions:,} product-view sessions ({baseline_rate:.3%}) over {observed_days} calendar days. This is not the final experimental baseline because production eligibility and first-exposure measurement will differ.

For a {recommended_plan['relative_mde_pct']:.0f}% relative lift scenario, the two-sided calculation requires {int(recommended_plan['sample_size_per_variant']):,} eligible assigned visitors per variant ({int(recommended_plan['total_sample_size']):,} total). Historical product-view volume implies roughly {int(recommended_plan['estimated_days_to_sample_size'])} days to reach that count; the plan enforces at least {int(recommended_plan['minimum_planned_days'])} days to cover weekly behavior. Recalculate from actual qualified-assignment traffic before launch.

## Required production logging
Record `experiment_id`, `variant`, `visitor_id`, `session_id`, `exposure_time`, `anchor_itemid`, ranked candidate item IDs, render status, candidate clicks, add-to-cart events, and transactions. Log the assignment before rendering so the intent-to-treat population is recoverable.

## Interpretation boundary
An offline Recall@10 advantage justifies testing the ranking. Only this randomized experiment can estimate the module's causal impact on the defined conversion metric.
"""
    (REPORTS_DIRECTORY / "phase_4_experiment_design.md").write_text(
        design,
        encoding="utf-8",
    )

    print("Experiment-planning report saved in reports/.")


if __name__ == "__main__":
    main()
