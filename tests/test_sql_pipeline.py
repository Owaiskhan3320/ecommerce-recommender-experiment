from pathlib import Path
import unittest

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "analytics.duckdb"


class AnalyticsDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = duckdb.connect(str(DATABASE_PATH), read_only=True)

    def tearDown(self) -> None:
        self.connection.close()

    def test_database_has_expected_tables(self) -> None:
        tables = {
            row[0]
            for row in self.connection.execute("SHOW TABLES").fetchall()
        }

        self.assertSetEqual(
            tables,
            {
                "stg_events",
                "int_session_events",
                "fct_sessions",
                "fct_user_activity",
                "fct_item_funnel",
            },
        )

    def test_staging_table_has_no_exact_duplicates(self) -> None:
        duplicate_groups = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    timestamp_ms,
                    visitorid,
                    event,
                    itemid,
                    transactionid
                FROM stg_events
                GROUP BY ALL
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        self.assertEqual(duplicate_groups, 0)

    def test_session_ids_are_unique(self) -> None:
        duplicate_session_ids = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT session_id
                FROM fct_sessions
                GROUP BY session_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        self.assertEqual(duplicate_session_ids, 0)

    def test_strict_funnel_flags_are_consistent(self) -> None:
        invalid_funnel_rows = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM fct_sessions
            WHERE
                has_cart_after_view
                AND NOT has_view
                OR has_transaction_after_view
                AND NOT has_view
                OR has_transaction_after_cart
                AND NOT has_cart_after_view
            """
        ).fetchone()[0]

        self.assertEqual(invalid_funnel_rows, 0)


if __name__ == "__main__":
    unittest.main()
