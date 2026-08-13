from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIRECTORY = PROJECT_ROOT / "sql"
RAW_EVENTS_PATH = PROJECT_ROOT / "data" / "raw" / "retailrocket" / "events.csv"
DATABASE_PATH = PROJECT_ROOT / "data" / "processed" / "analytics.duckdb"

SQL_FILES = [
    "01_stg_events.sql",
    "02_int_session_events.sql",
    "03_fct_sessions.sql",
    "04_fct_user_activity.sql",
    "05_fct_item_funnel.sql",
]


def load_sql_file(file_name: str) -> str:
    sql_path = SQL_DIRECTORY / file_name
    sql = sql_path.read_text(encoding="utf-8")

    raw_events_path = RAW_EVENTS_PATH.as_posix().replace("'", "''")

    return sql.replace("{{ raw_events_path }}", raw_events_path)


def main() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(DATABASE_PATH))

    try:
        for file_name in SQL_FILES:
            print(f"Running {file_name}...")
            connection.execute(load_sql_file(file_name))

        checks = connection.execute(
            """
            SELECT 'stg_events' AS table_name, COUNT(*) AS row_count
            FROM stg_events

            UNION ALL

            SELECT 'int_session_events' AS table_name, COUNT(*) AS row_count
            FROM int_session_events

            UNION ALL

            SELECT 'fct_sessions' AS table_name, COUNT(*) AS row_count
            FROM fct_sessions

            UNION ALL

            SELECT 'fct_user_activity' AS table_name, COUNT(*) AS row_count
            FROM fct_user_activity

            UNION ALL

            SELECT 'fct_item_funnel' AS table_name, COUNT(*) AS row_count
            FROM fct_item_funnel
            """
        ).fetchdf()

        print("\nPipeline complete:")
        print(checks.to_string(index=False))
        print(f"\nDatabase created at: {DATABASE_PATH}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()