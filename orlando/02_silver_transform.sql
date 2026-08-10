-- ============================================================
-- Pattern A: Silver Transform (Snowflake BRONZE -> Snowflake SILVER)
-- Capstone - Orlando
--
-- This is the manual SQL version of what dbt will do.
-- Use this to test and validate the logic in a worksheet.
-- Once confirmed, port it into your dbt staging models.
-- ============================================================

USE ROLE DE;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE TECHCATALYST;

-- Create the SILVER schema (this maps to dbt's "staging" layer)
CREATE SCHEMA IF NOT EXISTS TECHCATALYST.SILVER;
USE SCHEMA SILVER;

-- ============================================================
-- SECTION 1: Union Yellow + Green into a single trips table
-- ============================================================

-- This unions both taxi types, renames timestamps to common names,
-- adds a taxi_type column, and computes derived time columns.
-- It does NOT filter bad records. That decision comes next.

CREATE OR REPLACE TABLE stg_trips AS

WITH yellow AS (
    SELECT
        'yellow'                    AS taxi_type,
        VendorID                    AS vendor_id,
        tpep_pickup_datetime        AS pickup_at,
        tpep_dropoff_datetime       AS dropoff_at,
        passenger_count,
        trip_distance,
        RatecodeID                  AS rate_code_id,
        store_and_fwd_flag,
        PULocationID                AS pickup_zone_id,
        DOLocationID                AS dropoff_zone_id,
        payment_type,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        total_amount,
        congestion_surcharge,
        airport_fee,
        cbd_congestion_fee,
        NULL::FLOAT                 AS ehail_fee,
        NULL::INT                   AS trip_type
    FROM TECHCATALYST.BRONZE.yellow_raw
),

green AS (
    SELECT
        'green'                     AS taxi_type,
        VendorID                    AS vendor_id,
        lpep_pickup_datetime        AS pickup_at,
        lpep_dropoff_datetime       AS dropoff_at,
        passenger_count,
        trip_distance,
        RatecodeID                  AS rate_code_id,
        store_and_fwd_flag,
        PULocationID                AS pickup_zone_id,
        DOLocationID                AS dropoff_zone_id,
        payment_type,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        total_amount,
        congestion_surcharge,
        NULL::FLOAT                 AS airport_fee,
        cbd_congestion_fee,
        ehail_fee,
        trip_type
    FROM TECHCATALYST.BRONZE.green_raw
),

combined AS (
    SELECT * FROM yellow
    UNION ALL
    SELECT * FROM green
)

SELECT
    *,
    DATEDIFF('minute', pickup_at, dropoff_at)   AS trip_duration_minutes,
    YEAR(pickup_at)                             AS pickup_year,
    MONTH(pickup_at)                            AS pickup_month,
    DAYOFWEEK(pickup_at)                        AS pickup_dayofweek,
    HOUR(pickup_at)                             AS pickup_hour
FROM combined;

-- ============================================================
-- SECTION 2: Zone lookup (clean copy in silver)
-- ============================================================

CREATE OR REPLACE TABLE stg_zones AS
SELECT
    LocationID      AS location_id,
    Borough         AS borough,
    Zone            AS zone_name,
    service_zone
FROM TECHCATALYST.BRONZE.zone_lookup;

-- ============================================================
-- SECTION 3: Verify Silver layer
-- ============================================================

-- Total row count (should equal yellow_raw + green_raw exactly)
SELECT COUNT(*) AS silver_total_rows FROM stg_trips;

-- Verify by taxi type
SELECT taxi_type, COUNT(*) AS row_count
FROM stg_trips
GROUP BY taxi_type;

-- Verify row count reconciliation (this number matters for your DQ report)
SELECT
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.yellow_raw) AS bronze_yellow,
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.green_raw) AS bronze_green,
    (SELECT COUNT(*) FROM stg_trips) AS silver_total,
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.yellow_raw) +
    (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.green_raw) AS expected_total,
    (SELECT COUNT(*) FROM stg_trips) -
    ((SELECT COUNT(*) FROM TECHCATALYST.BRONZE.yellow_raw) +
     (SELECT COUNT(*) FROM TECHCATALYST.BRONZE.green_raw)) AS difference;

-- Verify derived columns are sensible
SELECT
    pickup_year,
    pickup_month,
    COUNT(*) AS trips
FROM stg_trips
GROUP BY pickup_year, pickup_month
ORDER BY pickup_year, pickup_month;

-- Check for timestamps outside expected range (data quality issue to document)
SELECT COUNT(*) AS out_of_range_timestamps
FROM stg_trips
WHERE pickup_year NOT IN (2025, 2026)
   OR pickup_month NOT BETWEEN 1 AND 6;

-- Zone lookup verification
SELECT COUNT(*) AS zone_count FROM stg_zones;
SELECT * FROM stg_zones WHERE location_id IN (264, 265);

-- ============================================================
-- SECTION 4: Quick data quality preview (for your DQ report)
-- ============================================================

-- Negative fares
SELECT COUNT(*) AS negative_fares
FROM stg_trips WHERE fare_amount < 0;

-- Zero-distance trips with substantial fare
SELECT COUNT(*) AS zero_dist_with_fare
FROM stg_trips WHERE trip_distance = 0 AND fare_amount > 5;

-- Dropoff before pickup
SELECT COUNT(*) AS dropoff_before_pickup
FROM stg_trips WHERE trip_duration_minutes < 0;

-- Zero passenger count or NULL
SELECT COUNT(*) AS zero_or_null_passengers
FROM stg_trips WHERE passenger_count IS NULL OR passenger_count = 0;

-- Very long trips (over 4 hours)
SELECT COUNT(*) AS very_long_trips
FROM stg_trips WHERE trip_duration_minutes > 240;

-- Very short trips (under 1 minute)
SELECT COUNT(*) AS very_short_trips
FROM stg_trips WHERE trip_duration_minutes < 1 AND trip_duration_minutes >= 0;

-- Trips with distance > 100 miles
SELECT COUNT(*) AS extreme_distance
FROM stg_trips WHERE trip_distance > 100;
