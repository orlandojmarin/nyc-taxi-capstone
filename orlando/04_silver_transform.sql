-- ============================================================
-- Pattern A: Silver Transform (Snowflake BRONZE -> Snowflake SILVER)
-- Capstone - Orlando
--
-- REFERENCE ONLY. The production Silver layer is built by dbt.
-- This file documents the logic and can be run manually in a
-- Snowflake worksheet for testing or debugging.
-- ============================================================

USE ROLE DE;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE TECHCATALYST;

CREATE SCHEMA IF NOT EXISTS TECHCATALYST.SILVER;
USE SCHEMA SILVER;

-- ============================================================
-- SECTION 1: stg_trips (union Yellow + Green, derive columns, flag DQ)
-- ============================================================

CREATE OR REPLACE TABLE stg_trips AS

WITH yellow AS (
    SELECT
        'yellow'                    AS taxi_type,
        "VendorID"                  AS vendor_id,
        "tpep_pickup_datetime"      AS pickup_at,
        "tpep_dropoff_datetime"     AS dropoff_at,
        "passenger_count",
        "trip_distance",
        "RatecodeID"                AS rate_code_id,
        "store_and_fwd_flag",
        "PULocationID"              AS pickup_zone_id,
        "DOLocationID"              AS dropoff_zone_id,
        "payment_type",
        "fare_amount",
        "extra",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "congestion_surcharge",
        "Airport_fee"               AS airport_fee,
        "cbd_congestion_fee",
        NULL::FLOAT                 AS ehail_fee,
        NULL::INT                   AS trip_type
    FROM TECHCATALYST.BRONZE.yellow_raw
),

green AS (
    SELECT
        'green'                     AS taxi_type,
        "VendorID"                  AS vendor_id,
        "lpep_pickup_datetime"      AS pickup_at,
        "lpep_dropoff_datetime"     AS dropoff_at,
        "passenger_count",
        "trip_distance",
        "RatecodeID"                AS rate_code_id,
        "store_and_fwd_flag",
        "PULocationID"              AS pickup_zone_id,
        "DOLocationID"              AS dropoff_zone_id,
        "payment_type",
        "fare_amount",
        "extra",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "congestion_surcharge",
        NULL::FLOAT                 AS airport_fee,
        "cbd_congestion_fee",
        "ehail_fee",
        "trip_type"
    FROM TECHCATALYST.BRONZE.green_raw
),

combined AS (
    SELECT * FROM yellow
    UNION ALL
    SELECT * FROM green
),

with_derived AS (
    SELECT
        *,
        DATEDIFF('minute', pickup_at, dropoff_at)   AS trip_duration_minutes,
        YEAR(pickup_at)                             AS pickup_year,
        MONTH(pickup_at)                            AS pickup_month,
        DAYOFWEEK(pickup_at)                        AS pickup_dayofweek,
        HOUR(pickup_at)                             AS pickup_hour,
        CASE WHEN HOUR(pickup_at) >= 20 OR HOUR(pickup_at) < 6 THEN TRUE ELSE FALSE END AS is_night,
        CASE WHEN DAYOFWEEK(pickup_at) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
        CASE
            WHEN DAYOFWEEK(pickup_at) NOT IN (0, 6)
             AND (HOUR(pickup_at) BETWEEN 7 AND 8 OR HOUR(pickup_at) BETWEEN 17 AND 18)
            THEN TRUE ELSE FALSE
        END AS is_rush_hour
    FROM combined
)

SELECT
    *,
    CASE
        WHEN trip_duration_minutes < 0 THEN FALSE
        WHEN fare_amount < 0 THEN FALSE
        WHEN total_amount < 0 THEN FALSE
        WHEN trip_distance < 0 THEN FALSE
        WHEN trip_distance > 100 THEN FALSE
        WHEN pickup_year NOT IN (2025, 2026) THEN FALSE
        WHEN pickup_month NOT BETWEEN 1 AND 5 THEN FALSE
        ELSE TRUE
    END AS is_valid,
    ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(
        CASE WHEN trip_duration_minutes < 0 THEN 'dropoff_before_pickup' END,
        CASE WHEN fare_amount < 0 THEN 'negative_fare' END,
        CASE WHEN total_amount < 0 THEN 'negative_total' END,
        CASE WHEN trip_distance < 0 THEN 'negative_distance' END,
        CASE WHEN trip_distance > 100 THEN 'extreme_distance' END,
        CASE WHEN pickup_year NOT IN (2025, 2026) THEN 'out_of_range_year' END,
        CASE WHEN pickup_month NOT BETWEEN 1 AND 5 THEN 'out_of_range_month' END
    ), ', ') AS dq_flag_reason
FROM with_derived;

-- ============================================================
-- SECTION 2: stg_zones (clean copy in Silver)
-- ============================================================

CREATE OR REPLACE TABLE stg_zones AS
SELECT
    LocationID      AS location_id,
    Borough         AS borough,
    Zone            AS zone_name,
    service_zone
FROM TECHCATALYST.BRONZE.zone_lookup;

-- ============================================================
-- SECTION 3: stg_weather (Bronze -> Silver with derived categories)
-- ============================================================

CREATE OR REPLACE TABLE stg_weather AS
SELECT
    DATETIME_LOCAL,
    DATE(DATETIME_LOCAL)                AS weather_date,
    HOUR(DATETIME_LOCAL)                AS weather_hour,
    TEMPERATURE_F,
    APPARENT_TEMPERATURE_F,
    PRECIPITATION_INCH,
    RAIN_INCH,
    SNOWFALL_INCH,
    SNOW_DEPTH_INCH,
    WEATHER_CODE,
    WEATHER_DESCRIPTION,
    WIND_SPEED_MPH,
    WIND_GUSTS_MPH,
    RELATIVE_HUMIDITY_PCT,
    VISIBILITY_FT,
    CASE
        WHEN WEATHER_CODE IN (0, 1)         THEN 'Clear'
        WHEN WEATHER_CODE IN (2, 3)         THEN 'Cloudy'
        WHEN WEATHER_CODE IN (45, 48)       THEN 'Fog'
        WHEN WEATHER_CODE BETWEEN 51 AND 57 THEN 'Drizzle'
        WHEN WEATHER_CODE BETWEEN 61 AND 67 THEN 'Rain'
        WHEN WEATHER_CODE BETWEEN 71 AND 77 THEN 'Snow'
        WHEN WEATHER_CODE BETWEEN 80 AND 82 THEN 'Rain Showers'
        WHEN WEATHER_CODE BETWEEN 85 AND 86 THEN 'Snow Showers'
        WHEN WEATHER_CODE BETWEEN 95 AND 99 THEN 'Thunderstorm'
        ELSE 'Other'
    END AS weather_category,
    CASE
        WHEN WEATHER_CODE >= 61 OR SNOWFALL_INCH > 0 OR WIND_SPEED_MPH > 25
        THEN TRUE ELSE FALSE
    END AS is_adverse_weather
FROM TECHCATALYST.BRONZE.WEATHER_HOURLY;

-- ============================================================
-- SECTION 4: Verification queries
-- ============================================================

SELECT COUNT(*) AS silver_total_rows FROM stg_trips;

SELECT taxi_type, COUNT(*) AS row_count
FROM stg_trips
GROUP BY taxi_type;

SELECT
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.yellow_raw) AS bronze_yellow,
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.green_raw) AS bronze_green,
    (SELECT COUNT(*) FROM stg_trips) AS silver_total,
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.yellow_raw) +
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.green_raw) AS expected_total,
    (SELECT COUNT(*) FROM stg_trips) -
    ((SELECT COUNT(*) FROM TECHCATALYST.BRONZE.yellow_raw) +
     (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.green_raw)) AS difference;

SELECT pickup_year, pickup_month, COUNT(*) AS trips
FROM stg_trips
GROUP BY pickup_year, pickup_month
ORDER BY pickup_year, pickup_month;

SELECT COUNT(*) AS zone_count FROM stg_zones;
SELECT COUNT(*) AS silver_weather_rows FROM stg_weather;

-- ============================================================
-- SECTION 5: Data quality summary (for DQ report)
-- ============================================================

SELECT is_valid, COUNT(*) AS row_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM stg_trips
GROUP BY is_valid;

SELECT dq_flag_reason, COUNT(*) AS row_count
FROM stg_trips
WHERE NOT is_valid
GROUP BY dq_flag_reason
ORDER BY row_count DESC
LIMIT 20;

SELECT COUNT(*) AS zero_or_null_passengers
FROM stg_trips WHERE passenger_count IS NULL OR passenger_count = 0;

SELECT COUNT(*) AS very_long_trips
FROM stg_trips WHERE trip_duration_minutes > 240;

SELECT COUNT(*) AS very_short_trips
FROM stg_trips WHERE trip_duration_minutes < 1 AND trip_duration_minutes >= 0;

SELECT COUNT(*) AS zero_dist_with_fare
FROM stg_trips WHERE trip_distance = 0 AND fare_amount > 5;
