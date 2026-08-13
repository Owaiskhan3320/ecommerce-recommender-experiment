CREATE OR REPLACE TABLE stg_events AS
WITH typed_events AS (
    SELECT
        CAST(timestamp AS BIGINT) AS timestamp_ms,
        CAST(visitorid AS BIGINT) AS visitorid,
        CAST(event AS VARCHAR) AS event,
        CAST(itemid AS BIGINT) AS itemid,
        CAST(transactionid AS BIGINT) AS transactionid,
        to_timestamp(CAST(timestamp AS DOUBLE) / 1000.0) AS event_time_utc
    FROM read_csv_auto('{{ raw_events_path }}', header = true)
),

deduplicated_events AS (
    SELECT *
    FROM typed_events
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY
            timestamp_ms,
            visitorid,
            event,
            itemid,
            transactionid
        ORDER BY timestamp_ms
    ) = 1
)

SELECT
    timestamp_ms,
    event_time_utc,
    CAST(event_time_utc AS DATE) AS event_date,
    visitorid,
    event,
    itemid,
    transactionid
FROM deduplicated_events;