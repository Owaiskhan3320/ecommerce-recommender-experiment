from csv import DictReader
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"


def load_csv_rows(file_name: str) -> list[dict[str, str]]:
    with (REPORTS_DIRECTORY / file_name).open(encoding="utf-8", newline="") as file:
        return list(DictReader(file))


def find_metric(
    rows: list[dict[str, str]],
    evaluation: str,
    model: str,
) -> dict[str, str]:
    for row in rows:
        if row["evaluation"] == evaluation and row["model"] == model and row["k"] == "10":
            return row

    raise ValueError(f"Missing HitRate@10 result for {evaluation} and {model}.")


def main() -> None:
    metrics = load_csv_rows("phase_3_recommender_metrics.csv")
    intervals = load_csv_rows("phase_3_hit_rate_intervals.csv")

    purchased_co_visit = find_metric(
        metrics,
        "Purchased-item retrieval",
        "Co-visitation",
    )
    purchased_popularity = find_metric(
        metrics,
        "Purchased-item retrieval",
        "Popularity baseline",
    )
    next_item_co_visit = find_metric(
        metrics,
        "Next-item retrieval",
        "Co-visitation",
    )
    next_item_popularity = find_metric(
        metrics,
        "Next-item retrieval",
        "Popularity baseline",
    )
    purchased_co_visit_interval = find_metric(
        intervals,
        "Purchased-item retrieval",
        "Co-visitation",
    )
    purchased_popularity_interval = find_metric(
        intervals,
        "Purchased-item retrieval",
        "Popularity baseline",
    )

    summary = f"""# Executive Summary

## Decision context

This case study examines whether session-level e-commerce behavior and a simple co-visitation recommender justify a controlled ranking experiment. RetailRocket provides observational clickstream data only; it contains neither recommendation exposures nor randomized variants.

## Evidence from the analysis

- **Funnel opportunity:** session-level analysis shows the largest observed loss occurs before add-to-cart. These logs do not identify its cause; product relevance is one hypothesis alongside price, availability, traffic quality, and shopper intent.
- **Model signal:** on a chronological 28-day holdout, purchased-item HitRate@10 is {purchased_co_visit['hit_rate_at_k_pct']}% for co-visitation and {purchased_popularity['hit_rate_at_k_pct']}% for an anchor-excluded popularity baseline. Visitor-bootstrap 95% intervals are {purchased_co_visit_interval['hit_rate_at_k_ci_low_pct']}%–{purchased_co_visit_interval['hit_rate_at_k_ci_high_pct']}% and {purchased_popularity_interval['hit_rate_at_k_ci_low_pct']}%–{purchased_popularity_interval['hit_rate_at_k_ci_high_pct']}%, respectively.
- **Broader retrieval check:** next-item HitRate@10 is {next_item_co_visit['hit_rate_at_k_pct']}% for co-visitation and {next_item_popularity['hit_rate_at_k_pct']}% for popularity. The tasks answer different retrieval questions and are not conversion metrics.
- **Candidate availability:** purchased-item coverage@10 is {purchased_co_visit['candidate_coverage_at_k_pct']}%. The detailed evaluation setup and uncertainty outputs are in the Phase 3 reports.
- **Experiment readiness:** the Phase 4 report provides illustrative sample-size planning. Production eligibility and qualified-assignment traffic must be measured before estimating experiment duration.

## Recommendation

Do not infer conversion impact from the offline result. Use the co-visitation model as the treatment in a controlled test against a popularity-ranking control, with identical placement and presentation. Randomize eligible visitors persistently, analyze the first qualified assignment using intent to treat, and monitor render-success and latency guardrails.

## What would change the decision

- **Advance:** the treatment's primary-conversion confidence-interval lower bound clears the pre-specified minimum practical effect, and guardrails pass.
- **Hold or revise:** the primary interval does not clear the practical threshold, candidate coverage is too low in production, or rendering/performance guardrails regress.

## Limits

The recommender was not deployed. The Phase 5 A/B report uses fabricated counts solely to demonstrate the analysis workflow and must not be presented as an observed experiment result.
"""
    (REPORTS_DIRECTORY / "executive_summary.md").write_text(summary, encoding="utf-8")
    print("Executive summary saved in reports/.")


if __name__ == "__main__":
    main()
