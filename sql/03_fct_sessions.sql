CREATE OR REPLACE TABLE fct_sessions AS
WITH session_times AS (
    SELECT
        session_id,
        visitorid,
        MIN(event_time_utc) AS session_start_time,
        MAX(event_time_utc) AS session_end_time,
        COUNT(*) AS event_count,
        COUNT_IF(event = 'view') AS view_count,
        COUNT_IF(event = 'addtocart') AS cart_count,
        COUNT_IF(event = 'transaction') AS transaction_count,
        MIN(CASE WHEN event = 'view' THEN event_time_utc END) AS first_view_time,
        MIN(CASE WHEN event = 'addtocart' THEN event_time_utc END) AS first_cart_time,
        MIN(CASE WHEN event = 'transaction' THEN event_time_utc END) AS first_transaction_time
    FROM int_session_events
    GROUP BY
        session_id,
        visitorid
)

SELECT
    *,
    date_diff(
        'second',
        session_start_time,
        session_end_time
    ) AS session_duration_seconds,
    first_view_time IS NOT NULL AS has_view,
    CASE
        WHEN first_view_time IS NOT NULL
            AND first_cart_time IS NOT NULL
            AND first_cart_time >= first_view_time
        THEN TRUE
        ELSE FALSE
    END AS has_cart_after_view,
    CASE
        WHEN first_view_time IS NOT NULL
            AND first_transaction_time IS NOT NULL
            AND first_transaction_time >= first_view_time
        THEN TRUE
        ELSE FALSE
    END AS has_transaction_after_view,
    CASE
        WHEN first_cart_time IS NOT NULL
            AND first_transaction_time IS NOT NULL
            AND first_transaction_time >= first_cart_time
        THEN TRUE
        ELSE FALSE
    END AS has_transaction_after_cart
FROM session_times;