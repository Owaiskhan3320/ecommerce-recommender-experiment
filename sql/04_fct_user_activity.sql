CREATE OR REPLACE TABLE fct_user_activity AS
WITH user_metrics AS (
    SELECT
        visitorid,
        MIN(event_time_utc) AS first_event_time,
        MAX(event_time_utc) AS last_event_time,
        COUNT(*) AS event_count,
        COUNT(DISTINCT session_id) AS session_count,
        COUNT_IF(event = 'view') AS view_count,
        COUNT_IF(event = 'addtocart') AS cart_count,
        COUNT_IF(event = 'transaction') AS transaction_count,
        COUNT(DISTINCT transactionid) AS transaction_id_count
    FROM int_session_events
    GROUP BY visitorid
)

SELECT
    *,
    session_count >= 2 AS is_repeat_visitor,
    transaction_count > 0 AS has_transaction
FROM user_metrics;