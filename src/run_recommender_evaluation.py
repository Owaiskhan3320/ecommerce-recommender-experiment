from pathlib import Path
from random import Random

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from item_recommender import (
    build_co_visit_candidates,
    candidate_count,
    rank_popular_items,
    recommend_items,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "analytics.duckdb"
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"
FIGURES_DIRECTORY = REPORTS_DIRECTORY / "figures"
HOLDOUT_DAYS = 28
MAX_ITEMS_PER_SESSION = 50
K_VALUES = [1, 5, 10, 20]
BOOTSTRAP_ITERATIONS = 300
BOOTSTRAP_SEED = 2026


def save_figure(file_name: str) -> None:
    FIGURES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURES_DIRECTORY / file_name, dpi=150, bbox_inches="tight")
    plt.close()


def load_training_sequences(
    connection: duckdb.DuckDBPyConnection,
    cutoff_time: str,
) -> list[list[int]]:
    rows = connection.execute(
        """
        SELECT
            session_id,
            itemid
        FROM int_session_events
        WHERE
            event IN ('view', 'addtocart', 'transaction')
            AND event_time_utc < CAST(? AS TIMESTAMPTZ)
        ORDER BY session_id, session_event_number
        """,
        [cutoff_time],
    ).fetchall()

    sequences: list[list[int]] = []
    current_session_id: str | None = None
    current_sequence: list[int] = []

    for session_id, itemid in rows:
        if current_session_id is not None and session_id != current_session_id:
            sequences.append(current_sequence)
            current_sequence = []

        current_session_id = session_id
        current_sequence.append(itemid)

    if current_sequence:
        sequences.append(current_sequence)

    return sequences


def load_holdout_purchase_examples(
    connection: duckdb.DuckDBPyConnection,
    cutoff_time: str,
) -> pd.DataFrame:
    return connection.execute(
        """
        WITH held_out_transactions AS (
            SELECT
                visitorid,
                session_id,
                event_time_utc AS transaction_time,
                itemid AS purchased_itemid
            FROM int_session_events
            WHERE
                event = 'transaction'
                AND event_time_utc >= CAST(? AS TIMESTAMPTZ)
        ),
        prior_different_views AS (
            SELECT DISTINCT
                transactions.visitorid,
                transactions.session_id,
                transactions.transaction_time,
                transactions.purchased_itemid,
                events.event_time_utc AS anchor_time,
                events.itemid AS anchor_itemid
            FROM held_out_transactions AS transactions
            INNER JOIN int_session_events AS events
                ON transactions.session_id = events.session_id
                AND events.event = 'view'
                AND events.event_time_utc < transactions.transaction_time
                AND events.itemid <> transactions.purchased_itemid
        ),
        latest_anchor_times AS (
            SELECT
                visitorid,
                session_id,
                transaction_time,
                purchased_itemid,
                MAX(anchor_time) AS anchor_time
            FROM prior_different_views
            GROUP BY
                visitorid,
                session_id,
                transaction_time,
                purchased_itemid
        ),
        unique_latest_anchors AS (
            SELECT
                views.visitorid,
                views.session_id,
                MIN(views.anchor_itemid) AS anchor_itemid,
                views.purchased_itemid
            FROM prior_different_views AS views
            INNER JOIN latest_anchor_times
                ON views.visitorid = latest_anchor_times.visitorid
                AND views.session_id = latest_anchor_times.session_id
                AND views.transaction_time = latest_anchor_times.transaction_time
                AND views.purchased_itemid = latest_anchor_times.purchased_itemid
                AND views.anchor_time = latest_anchor_times.anchor_time
            GROUP BY
                views.visitorid,
                views.session_id,
                views.purchased_itemid,
                views.transaction_time
            HAVING COUNT(DISTINCT views.anchor_itemid) = 1
        )
        SELECT
            visitorid,
            session_id,
            anchor_itemid,
            purchased_itemid AS target_itemid
        FROM unique_latest_anchors
        """,
        [cutoff_time],
    ).fetchdf()


def load_holdout_next_item_examples(
    connection: duckdb.DuckDBPyConnection,
    cutoff_time: str,
) -> pd.DataFrame:
    return connection.execute(
        """
        WITH held_out_views AS (
            SELECT
                visitorid,
                session_id,
                event_time_utc AS anchor_time,
                itemid AS anchor_itemid
            FROM int_session_events
            WHERE
                event = 'view'
                AND event_time_utc >= CAST(? AS TIMESTAMPTZ)
        ),
        first_view_times AS (
            SELECT
                visitorid,
                session_id,
                MIN(anchor_time) AS anchor_time
            FROM held_out_views
            GROUP BY visitorid, session_id
        ),
        first_views AS (
            SELECT
                views.visitorid,
                views.session_id,
                views.anchor_time,
                MIN(views.anchor_itemid) AS anchor_itemid
            FROM held_out_views AS views
            INNER JOIN first_view_times
                ON views.visitorid = first_view_times.visitorid
                AND views.session_id = first_view_times.session_id
                AND views.anchor_time = first_view_times.anchor_time
            GROUP BY
                views.visitorid,
                views.session_id,
                views.anchor_time
            HAVING COUNT(DISTINCT views.anchor_itemid) = 1
        ),
        later_distinct_items AS (
            SELECT DISTINCT
                first_views.visitorid,
                first_views.session_id,
                first_views.anchor_time,
                first_views.anchor_itemid,
                events.event_time_utc AS target_time,
                events.itemid AS target_itemid
            FROM first_views
            INNER JOIN int_session_events AS events
                ON first_views.session_id = events.session_id
                AND events.event IN ('view', 'addtocart', 'transaction')
                AND events.event_time_utc > first_views.anchor_time
                AND events.event_time_utc >= CAST(? AS TIMESTAMPTZ)
                AND events.itemid <> first_views.anchor_itemid
        ),
        earliest_target_times AS (
            SELECT
                visitorid,
                session_id,
                anchor_time,
                anchor_itemid,
                MIN(target_time) AS target_time
            FROM later_distinct_items
            GROUP BY
                visitorid,
                session_id,
                anchor_time,
                anchor_itemid
        ),
        unique_earliest_targets AS (
            SELECT
                items.visitorid,
                items.session_id,
                items.anchor_itemid,
                MIN(items.target_itemid) AS target_itemid
            FROM later_distinct_items AS items
            INNER JOIN earliest_target_times
                ON items.visitorid = earliest_target_times.visitorid
                AND items.session_id = earliest_target_times.session_id
                AND items.anchor_time = earliest_target_times.anchor_time
                AND items.anchor_itemid = earliest_target_times.anchor_itemid
                AND items.target_time = earliest_target_times.target_time
            GROUP BY
                items.visitorid,
                items.session_id,
                items.anchor_itemid,
                items.target_time
            HAVING COUNT(DISTINCT items.target_itemid) = 1
        )
        SELECT
            visitorid,
            session_id,
            anchor_itemid,
            target_itemid
        FROM unique_earliest_targets
        """,
        [cutoff_time, cutoff_time],
    ).fetchdf()


def build_session_length_distribution(
    training_sequences: list[list[int]],
) -> pd.DataFrame:
    unique_item_counts = [len(set(sequence)) for sequence in training_sequences]
    rows = []
    for bucket_name, lower_bound, upper_bound in [
        ("1", 1, 1),
        ("2-5", 2, 5),
        ("6-20", 6, 20),
        ("21-50", 21, 50),
        ("51+", 51, None),
    ]:
        count = sum(
            item_count >= lower_bound
            and (upper_bound is None or item_count <= upper_bound)
            for item_count in unique_item_counts
        )
        rows.append(
            {
                "unique_items_per_session": bucket_name,
                "session_count": count,
                "share_of_training_sessions_pct": round(
                    100 * count / len(training_sequences),
                    3,
                ),
            }
        )

    return pd.DataFrame(rows)


def evaluate_ranking_model(
    model_name: str,
    evaluation_name: str,
    candidates_by_item: dict[int, list[int]],
    evaluation_examples: pd.DataFrame,
    fallback_candidates: list[int] | None = None,
    fallback_candidate_set: set[int] | None = None,
) -> pd.DataFrame:
    rows = []
    examples = list(evaluation_examples.itertuples(index=False))

    for top_k in K_VALUES:
        eligible_count = sum(
            candidate_count(
                example.anchor_itemid,
                candidates_by_item,
                fallback_candidates,
                fallback_candidate_set,
            )
            >= top_k
            for example in examples
        )
        hits = sum(
            example.target_itemid
            in recommend_items(
                example.anchor_itemid,
                candidates_by_item,
                top_k,
                fallback_candidates,
            )
            for example in examples
        )
        rows.append(
            {
                "evaluation": evaluation_name,
                "model": model_name,
                "k": top_k,
                "evaluation_examples": len(examples),
                "examples_with_at_least_k_candidates": eligible_count,
                "candidate_coverage_at_k_pct": round(
                    100 * eligible_count / len(examples),
                    3,
                ),
                "hits": hits,
                "hit_rate_at_k_pct": round(100 * hits / len(examples), 3),
            }
        )

    return pd.DataFrame(rows)


def metric_value(
    metrics: pd.DataFrame,
    evaluation_name: str,
    model_name: str,
    column_name: str,
    top_k: int = 10,
) -> float:
    return metrics.loc[
        (metrics["evaluation"] == evaluation_name)
        & (metrics["model"] == model_name)
        & (metrics["k"] == top_k),
        column_name,
    ].iloc[0]


def percentile(values: list[float], probability: float) -> float:
    ordered_values = sorted(values)
    position = (len(ordered_values) - 1) * probability
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered_values) - 1)
    interpolation = position - lower_index
    return (
        ordered_values[lower_index] * (1 - interpolation)
        + ordered_values[upper_index] * interpolation
    )


def visitor_bootstrap_hit_rate_interval(
    candidates_by_item: dict[int, list[int]],
    evaluation_examples: pd.DataFrame,
    fallback_candidates: list[int] | None = None,
    top_k: int = 10,
) -> tuple[float, float]:
    visitor_totals: dict[int, list[int]] = {}
    for example in evaluation_examples.itertuples(index=False):
        visitor_total = visitor_totals.setdefault(example.visitorid, [0, 0])
        visitor_total[0] += int(
            example.target_itemid
            in recommend_items(
                example.anchor_itemid,
                candidates_by_item,
                top_k,
                fallback_candidates,
            )
        )
        visitor_total[1] += 1

    random_generator = Random(BOOTSTRAP_SEED)
    visitor_values = list(visitor_totals.values())
    rates = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        sampled_totals = [
            visitor_values[random_generator.randrange(len(visitor_values))]
            for _ in range(len(visitor_values))
        ]
        sampled_hits = sum(total[0] for total in sampled_totals)
        sampled_examples = sum(total[1] for total in sampled_totals)
        rates.append(100 * sampled_hits / sampled_examples)

    return percentile(rates, 0.025), percentile(rates, 0.975)


def main() -> None:
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")

    connection = duckdb.connect(str(DATABASE_PATH), read_only=True)
    try:
        cutoff_time = connection.execute(
            """
            SELECT CAST(MAX(event_time_utc) - ? * INTERVAL '1 day' AS VARCHAR)
            FROM int_session_events
            """,
            [HOLDOUT_DAYS],
        ).fetchone()[0]

        training_sequences = load_training_sequences(connection, cutoff_time)
        purchase_examples = load_holdout_purchase_examples(connection, cutoff_time)
        next_item_examples = load_holdout_next_item_examples(connection, cutoff_time)
    finally:
        connection.close()

    candidates_by_item = build_co_visit_candidates(
        training_sequences,
        max_items_per_session=MAX_ITEMS_PER_SESSION,
    )
    popular_items = rank_popular_items(training_sequences)
    popular_item_set = set(popular_items)
    session_length_distribution = build_session_length_distribution(training_sequences)
    session_length_distribution.to_csv(
        REPORTS_DIRECTORY / "phase_3_training_session_item_counts.csv",
        index=False,
    )

    evaluation_sets = {
        "Purchased-item retrieval": purchase_examples,
        "Next-item retrieval": next_item_examples,
    }
    all_metrics = []
    interval_rows = []
    for evaluation_name, evaluation_examples in evaluation_sets.items():
        all_metrics.append(
            evaluate_ranking_model(
                "Co-visitation",
                evaluation_name,
                candidates_by_item,
                evaluation_examples,
            )
        )
        co_visit_interval = visitor_bootstrap_hit_rate_interval(
            candidates_by_item,
            evaluation_examples,
        )
        popularity_interval = visitor_bootstrap_hit_rate_interval(
            {},
            evaluation_examples,
            fallback_candidates=popular_items,
        )
        interval_rows.extend(
            [
                {
                    "evaluation": evaluation_name,
                    "model": "Co-visitation",
                    "k": 10,
                    "bootstrap_unit": "visitorid",
                    "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
                    "hit_rate_at_k_ci_low_pct": round(co_visit_interval[0], 3),
                    "hit_rate_at_k_ci_high_pct": round(co_visit_interval[1], 3),
                },
                {
                    "evaluation": evaluation_name,
                    "model": "Popularity baseline",
                    "k": 10,
                    "bootstrap_unit": "visitorid",
                    "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
                    "hit_rate_at_k_ci_low_pct": round(popularity_interval[0], 3),
                    "hit_rate_at_k_ci_high_pct": round(popularity_interval[1], 3),
                },
            ]
        )
        all_metrics.append(
            evaluate_ranking_model(
                "Popularity baseline",
                evaluation_name,
                {},
                evaluation_examples,
                fallback_candidates=popular_items,
                fallback_candidate_set=popular_item_set,
            )
        )

    evaluation_metrics = pd.concat(all_metrics, ignore_index=True)
    evaluation_metrics.to_csv(
        REPORTS_DIRECTORY / "phase_3_recommender_metrics.csv",
        index=False,
    )
    pd.DataFrame(interval_rows).to_csv(
        REPORTS_DIRECTORY / "phase_3_hit_rate_intervals.csv",
        index=False,
    )

    purchase_co_visit_hit_rate = metric_value(
        evaluation_metrics,
        "Purchased-item retrieval",
        "Co-visitation",
        "hit_rate_at_k_pct",
    )
    purchase_popularity_hit_rate = metric_value(
        evaluation_metrics,
        "Purchased-item retrieval",
        "Popularity baseline",
        "hit_rate_at_k_pct",
    )
    purchase_coverage_at_10 = metric_value(
        evaluation_metrics,
        "Purchased-item retrieval",
        "Co-visitation",
        "candidate_coverage_at_k_pct",
    )
    next_item_co_visit_hit_rate = metric_value(
        evaluation_metrics,
        "Next-item retrieval",
        "Co-visitation",
        "hit_rate_at_k_pct",
    )
    next_item_popularity_hit_rate = metric_value(
        evaluation_metrics,
        "Next-item retrieval",
        "Popularity baseline",
        "hit_rate_at_k_pct",
    )
    truncated_sessions = int(
        session_length_distribution.loc[
            session_length_distribution["unique_items_per_session"] == "51+",
            "session_count",
        ].iloc[0]
    )

    evaluation_setup = pd.DataFrame(
        {
            "metric": [
                "Training end time",
                "Holdout duration (days)",
                "Training sessions",
                "Purchased-item retrieval examples",
                "Next-item retrieval examples",
                "Maximum items per training session",
                "Training sessions truncated at the cap",
                "Purchased-item co-visitation coverage@10 (%)",
            ],
            "value": [
                cutoff_time,
                HOLDOUT_DAYS,
                len(training_sequences),
                len(purchase_examples),
                len(next_item_examples),
                MAX_ITEMS_PER_SESSION,
                truncated_sessions,
                purchase_coverage_at_10,
            ],
        }
    )
    evaluation_setup.to_csv(
        REPORTS_DIRECTORY / "phase_3_recommender_evaluation_setup.csv",
        index=False,
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.lineplot(
        data=evaluation_metrics,
        x="k",
        y="hit_rate_at_k_pct",
        hue="model",
        style="evaluation",
        marker="o",
        ax=ax,
    )
    ax.set_title("Time-Based Item Recommendation Evaluation")
    ax.set_xlabel("Number of recommendations (K)")
    ax.set_ylabel("HitRate@K (%)")
    ax.set_xticks(K_VALUES)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
    save_figure("phase_3_recommender_hit_rate_at_k.png")

    summary = f"""# Phase 3 Recommender Evaluation Summary

## Model
This is a non-personalized item-to-item co-visitation recommender. For a viewed item, it ranks items that appeared in the same earlier session most often. It uses product interactions only and removes duplicate items within a session before counting co-visits.

## Evaluation design
The model trains on events before {cutoff_time}. The final {HOLDOUT_DAYS} days form a chronological holdout. Purchased-item retrieval uses the last uniquely timestamped different product view before a transaction as the anchor. Next-item retrieval is a broader secondary evaluation that uses a product view and the next uniquely timestamped different item interaction in the same held-out session. Equal-timestamp event order is not interpreted as behavioral order.

Each example has one target item, so HitRate@K is numerically equivalent to Recall@K. The report uses HitRate@K because it states the retrieval question directly. Both the co-visitation model and popularity baseline remove the current anchor item before selecting K candidates. The committed interval report uses 300 visitor-level bootstrap resamples for HitRate@10 uncertainty.

## Result
For purchased-item retrieval, co-visitation reaches HitRate@10 of {purchase_co_visit_hit_rate:.3f}%, compared with {purchase_popularity_hit_rate:.3f}% for the anchor-excluded popularity baseline. Co-visitation coverage@10 is {purchase_coverage_at_10:.3f}% for this selected evaluation population. In the broader next-item retrieval task, co-visitation reaches HitRate@10 of {next_item_co_visit_hit_rate:.3f}% compared with {next_item_popularity_hit_rate:.3f}% for popularity.

The 50-item session cap limits pairwise computation. It truncates {truncated_sessions:,} of {len(training_sequences):,} training sessions; the committed session-length distribution reports the full context.

## Interpretation limits
These offline tasks measure historical item retrieval, not conversion lift, revenue lift, or relevance across all product-page impressions. Purchased-item retrieval is deliberately conditioned on a later transaction, while next-item retrieval broadens the population but still excludes one-item and tied-timestamp paths. A controlled experiment would be required before any causal product claim.
"""
    (REPORTS_DIRECTORY / "phase_3_recommender_summary.md").write_text(
        summary,
        encoding="utf-8",
    )

    print("Recommender evaluation reports and figure saved in reports/.")


if __name__ == "__main__":
    main()
