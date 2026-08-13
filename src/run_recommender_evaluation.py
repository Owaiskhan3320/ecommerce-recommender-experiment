from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from item_recommender import (
    build_co_visit_candidates,
    rank_popular_items,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "analytics.duckdb"
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"
FIGURES_DIRECTORY = REPORTS_DIRECTORY / "figures"
HOLDOUT_DAYS = 28
MAX_ITEMS_PER_SESSION = 50
K_VALUES = [1, 5, 10, 20]


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


def load_holdout_examples(
    connection: duckdb.DuckDBPyConnection,
    cutoff_time: str,
) -> list[tuple[int, int]]:
    rows = connection.execute(
        """
        WITH held_out_transactions AS (
            SELECT
                session_id,
                session_event_number AS transaction_position,
                itemid AS purchased_itemid
            FROM int_session_events
            WHERE
                event = 'transaction'
                AND event_time_utc >= CAST(? AS TIMESTAMPTZ)
        ),
        eligible_views AS (
            SELECT
                transactions.session_id,
                transactions.purchased_itemid,
                events.itemid AS anchor_itemid,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        transactions.session_id,
                        transactions.transaction_position,
                        transactions.purchased_itemid
                    ORDER BY events.session_event_number DESC
                ) AS view_rank
            FROM held_out_transactions AS transactions
            INNER JOIN int_session_events AS events
                ON transactions.session_id = events.session_id
                AND events.event = 'view'
                AND events.session_event_number < transactions.transaction_position
                AND events.itemid <> transactions.purchased_itemid
        )
        SELECT anchor_itemid, purchased_itemid
        FROM eligible_views
        WHERE view_rank = 1
        """,
        [cutoff_time],
    ).fetchall()

    return [(anchor_itemid, purchased_itemid) for anchor_itemid, purchased_itemid in rows]


def evaluate_ranking_model(
    model_name: str,
    candidates_by_item: dict[int, list[int]],
    holdout_examples: list[tuple[int, int]],
    fallback_candidates: list[int] | None = None,
) -> pd.DataFrame:
    fallback_candidates = fallback_candidates or []
    recommendation_lists = [
        candidates_by_item.get(anchor_item, fallback_candidates)
        for anchor_item, _ in holdout_examples
    ]
    coverage_count = sum(bool(candidates) for candidates in recommendation_lists)
    coverage_pct = 100 * coverage_count / len(holdout_examples)

    rows = []
    for top_k in K_VALUES:
        hits = sum(
            purchased_item in candidates[:top_k]
            for candidates, (_, purchased_item) in zip(
                recommendation_lists,
                holdout_examples,
            )
        )
        rows.append(
            {
                "model": model_name,
                "k": top_k,
                "eligible_purchase_examples": len(holdout_examples),
                "examples_with_recommendations": coverage_count,
                "candidate_coverage_pct": round(coverage_pct, 3),
                "hits": hits,
                "recall_at_k_pct": round(100 * hits / len(holdout_examples), 3),
            }
        )

    return pd.DataFrame(rows)


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
        holdout_examples = load_holdout_examples(connection, cutoff_time)
        candidates_by_item = build_co_visit_candidates(
            training_sequences,
            max_items_per_session=MAX_ITEMS_PER_SESSION,
        )
        popular_items = rank_popular_items(training_sequences)

        co_visit_metrics = evaluate_ranking_model(
            "Co-visitation",
            candidates_by_item,
            holdout_examples,
        )
        popularity_metrics = evaluate_ranking_model(
            "Popularity baseline",
            {},
            holdout_examples,
            fallback_candidates=popular_items,
        )
        evaluation_metrics = pd.concat(
            [co_visit_metrics, popularity_metrics],
            ignore_index=True,
        )
        co_visit_coverage_pct = co_visit_metrics.loc[
            co_visit_metrics["k"] == 10, "candidate_coverage_pct"
        ].iloc[0]
        evaluation_setup = pd.DataFrame(
            {
                "metric": [
                    "Training end time",
                    "Holdout duration (days)",
                    "Training sessions",
                    "Holdout eligible purchase examples",
                    "Co-visitation candidate coverage (%)",
                ],
                "value": [
                    cutoff_time,
                    HOLDOUT_DAYS,
                    len(training_sequences),
                    len(holdout_examples),
                    co_visit_coverage_pct,
                ],
            }
        )

        evaluation_setup.to_csv(
            REPORTS_DIRECTORY / "phase_3_recommender_evaluation_setup.csv",
            index=False,
        )
        evaluation_metrics.to_csv(
            REPORTS_DIRECTORY / "phase_3_recommender_metrics.csv",
            index=False,
        )

        fig, ax = plt.subplots(figsize=(7, 4))
        sns.lineplot(
            data=evaluation_metrics,
            x="k",
            y="recall_at_k_pct",
            hue="model",
            marker="o",
            ax=ax,
        )
        ax.set_title("Co-Visitation Recommender: Time-Based Recall")
        ax.set_xlabel("Number of recommendations (K)")
        ax.set_ylabel("Recall@K (%)")
        ax.set_xticks(K_VALUES)
        save_figure("phase_3_recommender_recall_at_k.png")

        co_visit_recall_at_10 = co_visit_metrics.loc[
            co_visit_metrics["k"] == 10, "recall_at_k_pct"
        ].iloc[0]
        popularity_recall_at_10 = popularity_metrics.loc[
            popularity_metrics["k"] == 10, "recall_at_k_pct"
        ].iloc[0]

        summary = f"""# Phase 3 Recommender Evaluation Summary

## Model
This is a non-personalized item-to-item co-visitation recommender. For a viewed item, it ranks items that appeared in the same earlier session most often. It uses product interactions only and removes duplicate items within a session before counting co-visits.

## Evaluation design
The model trains on events before {cutoff_time}. The final {HOLDOUT_DAYS} days form a chronological holdout. Each holdout example uses the last different product viewed before a transaction as the anchor and asks whether the purchased item is in the recommendations. This avoids training on future events.

## Result
The co-visitation recommender reaches Recall@10 of {co_visit_recall_at_10:.3f}% across eligible holdout purchase examples, compared with {popularity_recall_at_10:.3f}% for a global popularity baseline. It can produce at least one recommendation for {co_visit_coverage_pct:.3f}% of those examples.

## Interpretation limits
Recall here measures whether a later purchased item is retrieved after a prior view in historical logs. It does not estimate conversion lift, revenue lift, relevance to every shopper, or the effect of showing recommendations in a product interface. A controlled experiment would be needed for those claims.
"""
        (REPORTS_DIRECTORY / "phase_3_recommender_summary.md").write_text(
            summary,
            encoding="utf-8",
        )

        print("Recommender evaluation reports and figure saved in reports/.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
