CREATE OR REPLACE TABLE fct_item_funnel AS
WITH item_metrics AS (
    SELECT
        itemid,
        COUNT(*) AS event_count,
        COUNT_IF(event = 'view') AS view_event_count,
        COUNT_IF(event = 'addtocart') AS cart_event_count,
        COUNT_IF(event = 'transaction') AS transaction_event_count,
        COUNT(DISTINCT visitorid) AS unique_visitors,
        COUNT(DISTINCT CASE WHEN event = 'view' THEN visitorid END) AS unique_viewers,
        COUNT(DISTINCT CASE WHEN event = 'transaction' THEN visitorid END) AS unique_purchasers
    FROM int_session_events
    GROUP BY itemid
)

SELECT
    *,
    ROUND(
        100.0 * cart_event_count / NULLIF(view_event_count, 0),
        3
    ) AS carts_per_view_pct,
    ROUND(
        100.0 * transaction_event_count / NULLIF(view_event_count, 0),
        3
    ) AS transactions_per_view_pct
FROM item_metrics;