from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "analytics.duckdb"
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"
FIGURES_DIRECTORY = REPORTS_DIRECTORY / "figures"


def save_figure(file_name: str) -> None:
    FIGURES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURES_DIRECTORY / file_name, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> None:
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")

    connection = duckdb.connect(str(DATABASE_PATH), read_only=True)

    try:
        funnel_metrics = connection.execute(
            """
            SELECT
                SUM(has_view::INTEGER) AS sessions_with_view,
                SUM(has_cart_after_view::INTEGER) AS sessions_with_cart_after_view,
                SUM(has_transaction_after_cart::INTEGER)
                    AS sessions_with_full_funnel_transaction
            FROM fct_sessions
            """
        ).fetchdf()

        session_stage_counts = pd.DataFrame(
            {
                "stage": [
                    "Viewed a product",
                    "Cart after view",
                    "Transaction after cart",
                ],
                "session_count": [
                    int(funnel_metrics.loc[0, "sessions_with_view"]),
                    int(funnel_metrics.loc[0, "sessions_with_cart_after_view"]),
                    int(
                        funnel_metrics.loc[
                            0, "sessions_with_full_funnel_transaction"
                        ]
                    ),
                ],
            }
        )
        session_stage_counts["share_of_view_sessions_pct"] = (
            session_stage_counts["session_count"]
            / session_stage_counts.loc[0, "session_count"]
            * 100
        ).round(3)
        session_stage_counts.to_csv(
            REPORTS_DIRECTORY / "phase_2_session_funnel.csv",
            index=False,
        )

        view_sessions = int(funnel_metrics.loc[0, "sessions_with_view"])
        cart_sessions = int(funnel_metrics.loc[0, "sessions_with_cart_after_view"])
        transaction_sessions = int(
            funnel_metrics.loc[0, "sessions_with_full_funnel_transaction"]
        )
        view_to_cart_rate = cart_sessions / view_sessions * 100
        cart_to_transaction_rate = transaction_sessions / cart_sessions * 100
        full_funnel_rate = transaction_sessions / view_sessions * 100

        fig, ax = plt.subplots(figsize=(11, 3.5))
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 1)
        ax.axis("off")
        funnel_colors = ["#8ab0ca", "#4e88b2", "#24516f"]
        stage_details = [
            ("Viewed a product", view_sessions, "100.000% of view sessions"),
            ("Cart after view", cart_sessions, f"{view_to_cart_rate:.3f}% of view sessions"),
            (
                "Transaction after cart",
                transaction_sessions,
                f"{full_funnel_rate:.3f}% of view sessions",
            ),
        ]
        for index, (stage, session_count, share) in enumerate(stage_details):
            box = FancyBboxPatch(
                (index + 0.08, 0.25),
                0.84,
                0.5,
                boxstyle="round,pad=0.02",
                facecolor=funnel_colors[index],
                edgecolor="none",
            )
            ax.add_patch(box)
            ax.text(index + 0.5, 0.61, stage, ha="center", va="center", color="white")
            ax.text(
                index + 0.5,
                0.48,
                f"{session_count:,} sessions",
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
            )
            ax.text(index + 0.5, 0.36, share, ha="center", va="center", color="white")

        for index, continuation_rate in enumerate(
            [view_to_cart_rate, cart_to_transaction_rate]
        ):
            ax.annotate(
                "",
                xy=(index + 1.05, 0.5),
                xytext=(index + 0.95, 0.5),
                arrowprops={"arrowstyle": "->", "color": "#5a5a5a", "lw": 1.5},
            )
            ax.text(
                index + 1,
                0.16,
                f"{continuation_rate:.3f}% continue",
                ha="center",
                va="center",
                color="#404040",
            )
        ax.set_title("Strict Session Funnel: View to Transaction", pad=12)
        save_figure("phase_2_strict_session_funnel.png")

        visitor_session_summary = connection.execute(
            """
            SELECT
                CASE
                    WHEN visitor_session_number = 1
                        THEN 'First observed session'
                    ELSE 'Later observed session'
                END AS session_group,
                COUNT(*) AS total_sessions,
                SUM(has_view::INTEGER) AS sessions_with_view,
                SUM(has_transaction_after_cart::INTEGER)
                    AS sessions_with_full_funnel_transaction,
                ROUND(
                    100.0 * SUM(has_transaction_after_cart::INTEGER)
                    / NULLIF(SUM(has_view::INTEGER), 0),
                    3
                ) AS transaction_rate_per_view_session_pct
            FROM fct_sessions
            GROUP BY session_group
            ORDER BY
                CASE session_group
                    WHEN 'First observed session' THEN 1
                    ELSE 2
                END
            """
        ).fetchdf()
        visitor_session_summary.to_csv(
            REPORTS_DIRECTORY / "phase_2_first_vs_later_sessions.csv",
            index=False,
        )

        fig, ax = plt.subplots(figsize=(8, 4))
        sns.barplot(
            data=visitor_session_summary,
            x="session_group",
            y="transaction_rate_per_view_session_pct",
            hue="session_group",
            palette="Greens_d",
            legend=False,
            ax=ax,
        )
        ax.set_title("Transaction Rate by Observed Session Number")
        ax.set_xlabel("")
        ax.set_ylabel("Strict transaction rate per view session (%)")
        save_figure("phase_2_first_vs_later_sessions.png")

        duration_summary = connection.execute(
            """
            SELECT
                duration_bucket,
                duration_order,
                COUNT(*) AS total_sessions,
                SUM(has_view::INTEGER) AS sessions_with_view,
                SUM(has_transaction_after_cart::INTEGER)
                    AS sessions_with_full_funnel_transaction,
                ROUND(
                    100.0 * SUM(has_transaction_after_cart::INTEGER)
                    / NULLIF(SUM(has_view::INTEGER), 0),
                    3
                ) AS transaction_rate_per_view_session_pct
            FROM (
                SELECT
                    *,
                    CASE
                        WHEN session_duration_seconds = 0 THEN '0 seconds'
                        WHEN session_duration_seconds <= 60 THEN '1-60 seconds'
                        WHEN session_duration_seconds <= 300 THEN '1-5 minutes'
                        WHEN session_duration_seconds <= 900 THEN '5-15 minutes'
                        ELSE 'More than 15 minutes'
                    END AS duration_bucket,
                    CASE
                        WHEN session_duration_seconds = 0 THEN 1
                        WHEN session_duration_seconds <= 60 THEN 2
                        WHEN session_duration_seconds <= 300 THEN 3
                        WHEN session_duration_seconds <= 900 THEN 4
                        ELSE 5
                    END AS duration_order
                FROM fct_sessions
            )
            GROUP BY duration_bucket, duration_order
            ORDER BY duration_order
            """
        ).fetchdf()
        duration_summary.to_csv(
            REPORTS_DIRECTORY / "phase_2_session_duration.csv",
            index=False,
        )

        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(
            data=duration_summary,
            x="duration_bucket",
            y="transaction_rate_per_view_session_pct",
            hue="duration_bucket",
            palette="Purples_d",
            legend=False,
            ax=ax,
        )
        ax.set_title("Transaction Rate by Session Duration")
        ax.set_xlabel("Session duration")
        ax.set_ylabel("Strict transaction rate per view session (%)")
        ax.tick_params(axis="x", rotation=20)
        save_figure("phase_2_session_duration.png")

        summary = f"""# Phase 2 Product Analytics Summary

## Finding
The largest observed drop-off is between a product view and an add-to-cart event. Of {view_sessions:,} sessions with a product view, {cart_sessions:,} reached an add-to-cart after the view ({view_to_cart_rate:.3f}%). Among those cart sessions, {transaction_sessions:,} reached a transaction after the cart ({cart_to_transaction_rate:.3f}%). The strict view-to-transaction rate is {full_funnel_rate:.3f}%.

## Recommendation
The largest observed loss occurs before add-to-cart, but this log does not identify the cause. Product-page relevance is one testable hypothesis alongside price, availability, traffic quality, and shopper intent. A simple item-to-item recommender is a reasonable feature to evaluate offline; a controlled experiment would still be required before making any claim about causal conversion impact.

## Interpretation limits
The event log is observational. Longer or later sessions may be associated with transactions, but these patterns do not show that session duration, repeat visits, or recommendations cause transactions.
"""
        (REPORTS_DIRECTORY / "phase_2_product_analysis_summary.md").write_text(
            summary,
            encoding="utf-8",
        )

        print("Product-analysis reports and figures saved in reports/.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
