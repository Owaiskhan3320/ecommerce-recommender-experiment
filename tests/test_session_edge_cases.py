from pathlib import Path
import unittest

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIRECTORY = PROJECT_ROOT / "sql"
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "session_edge_cases.csv"


class SessionEdgeCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = duckdb.connect(":memory:")
        fixture_path = FIXTURE_PATH.as_posix().replace("'", "''")
        self.connection.execute(
            f"""
            CREATE TABLE stg_events AS
            SELECT
                CAST(raw_events.timestamp_ms AS BIGINT) AS timestamp_ms,
                to_timestamp(CAST(raw_events.timestamp_ms AS DOUBLE) / 1000.0)
                    AS event_time_utc,
                CAST(
                    to_timestamp(CAST(raw_events.timestamp_ms AS DOUBLE) / 1000.0)
                    AS DATE
                )
                    AS event_date,
                CAST(raw_events.visitorid AS BIGINT) AS visitorid,
                CAST(raw_events.event AS VARCHAR) AS event,
                CAST(raw_events.itemid AS BIGINT) AS itemid,
                CAST(raw_events.transactionid AS BIGINT) AS transactionid
            FROM read_csv(
                '{fixture_path}',
                header = true,
                delim = ',',
                columns = {{
                    'timestamp_ms': 'BIGINT',
                    'visitorid': 'BIGINT',
                    'event': 'VARCHAR',
                    'itemid': 'BIGINT',
                    'transactionid': 'BIGINT'
                }}
            ) AS raw_events
            """
        )
        self.connection.execute(
            (SQL_DIRECTORY / "02_int_session_events.sql").read_text(encoding="utf-8")
        )
        self.connection.execute(
            (SQL_DIRECTORY / "03_fct_sessions.sql").read_text(encoding="utf-8")
        )

    def tearDown(self) -> None:
        self.connection.close()

    def test_exactly_thirty_minutes_stays_in_the_same_session(self) -> None:
        session_numbers = [
            row[0]
            for row in self.connection.execute(
                """
                SELECT session_number
                FROM int_session_events
                WHERE visitorid = 100
                ORDER BY timestamp_ms
                """
            ).fetchall()
        ]

        self.assertEqual(session_numbers, [1, 1, 2])

    def test_tied_view_and_cart_do_not_create_a_strict_funnel_step(self) -> None:
        flags = self.connection.execute(
            """
            SELECT
                has_view,
                has_cart_after_view,
                has_transaction_after_view,
                has_transaction_after_cart
            FROM fct_sessions
            WHERE visitorid = 200
            """
        ).fetchone()

        self.assertEqual(flags, (True, False, True, False))

    def test_strictly_later_events_complete_the_session_funnel(self) -> None:
        flags = self.connection.execute(
            """
            SELECT
                has_view,
                has_cart_after_view,
                has_transaction_after_view,
                has_transaction_after_cart
            FROM fct_sessions
            WHERE visitorid = 300
            """
        ).fetchone()

        self.assertEqual(flags, (True, True, True, True))


if __name__ == "__main__":
    unittest.main()
