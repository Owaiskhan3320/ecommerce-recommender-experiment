CREATE OR REPLACE TABLE int_session_events AS
WITH ordered_events AS (
    SELECT
        *,
        LAG(event_time_utc) OVER (
            PARTITION BY visitorid
            ORDER BY
                event_time_utc,
                itemid,
                event,
                COALESCE(transactionid, -1)
        ) AS previous_event_time
    FROM stg_events
),

marked_sessions AS (
    SELECT
        *,
        CASE
            WHEN previous_event_time IS NULL THEN 1
            WHEN event_time_utc - previous_event_time > INTERVAL 30 MINUTE THEN 1
            ELSE 0
        END AS starts_new_session
    FROM ordered_events
),

numbered_sessions AS (
    SELECT
        *,
        SUM(starts_new_session) OVER (
            PARTITION BY visitorid
            ORDER BY
                event_time_utc,
                itemid,
                event,
                COALESCE(transactionid, -1)
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_number
    FROM marked_sessions
)

SELECT
    CONCAT(
        CAST(visitorid AS VARCHAR),
        '-',
        CAST(session_number AS VARCHAR)
    ) AS session_id,
    visitorid,
    session_number,
    timestamp_ms,
    event_time_utc,
    event_date,
    event,
    itemid,
    transactionid
FROM numbered_sessions;