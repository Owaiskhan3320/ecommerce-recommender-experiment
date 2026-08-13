CREATE OR REPLACE TABLE fct_sessions AS
WITH session_summary AS (
    SELECT
        session_id,
        visitorid,
        MIN(session_number) AS visitor_session_number,
        MIN(event_time_utc) AS session_start_time,
        MAX(event_time_utc) AS session_end_time,
        COUNT(*) AS event_count,
        COUNT_IF(event = 'view') AS view_count,
        COUNT_IF(event = 'addtocart') AS cart_count,
        COUNT_IF(event = 'transaction') AS transaction_count
    FROM int_session_events
    GROUP BY
        session_id,
        visitorid
),

first_views AS (
    SELECT
        session_id,
        MIN(session_event_number) AS first_view_position,
        MIN(event_time_utc) AS first_view_time
    FROM int_session_events
    WHERE event = 'view'
    GROUP BY session_id
),

carts_after_view AS (
    SELECT
        events.session_id,
        MIN(events.session_event_number) AS first_cart_after_view_position,
        MIN(events.event_time_utc) AS first_cart_after_view_time
    FROM int_session_events AS events
    INNER JOIN first_views
        ON events.session_id = first_views.session_id
    WHERE
        events.event = 'addtocart'
        AND events.session_event_number > first_views.first_view_position
    GROUP BY events.session_id
),

funnel_flags AS (
    SELECT
        events.session_id,
        MAX(
            CASE
                WHEN
                    events.event = 'transaction'
                    AND events.session_event_number > first_views.first_view_position
                THEN 1
                ELSE 0
            END
        ) = 1 AS has_transaction_after_view,
        MAX(
            CASE
                WHEN
                    events.event = 'transaction'
                    AND events.session_event_number
                        > carts_after_view.first_cart_after_view_position
                THEN 1
                ELSE 0
            END
        ) = 1 AS has_transaction_after_cart
    FROM int_session_events AS events
    LEFT JOIN first_views
        ON events.session_id = first_views.session_id
    LEFT JOIN carts_after_view
        ON events.session_id = carts_after_view.session_id
    GROUP BY events.session_id
)

SELECT
    session_summary.*,
    date_diff(
        'second',
        session_start_time,
        session_end_time
    ) AS session_duration_seconds,
    first_views.first_view_time,
    carts_after_view.first_cart_after_view_time,
    view_count > 0 AS has_view,
    carts_after_view.session_id IS NOT NULL AS has_cart_after_view,
    funnel_flags.has_transaction_after_view,
    funnel_flags.has_transaction_after_cart
FROM session_summary
LEFT JOIN first_views
    ON session_summary.session_id = first_views.session_id
LEFT JOIN carts_after_view
    ON session_summary.session_id = carts_after_view.session_id
LEFT JOIN funnel_flags
    ON session_summary.session_id = funnel_flags.session_id;
