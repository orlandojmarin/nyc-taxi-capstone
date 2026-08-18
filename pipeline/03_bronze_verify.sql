-- ============================================================
-- Bronze Verification: Confirm all tables loaded correctly
-- Capstone - Orlando
--
-- Run this AFTER 01_bronze_load.sql and 02_fetch_weather.py
-- All checks should pass before moving to Silver.
-- ============================================================

USE ROLE DE;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE TECHCATALYST;
USE SCHEMA BRONZE;

-- ============================================================
-- SECTION 1: Row counts (record these for your DQ report)
-- ============================================================

SELECT 'yellow_raw' AS table_name, COUNT(*) AS row_count FROM yellow_raw
UNION ALL
SELECT 'green_raw', COUNT(*) FROM green_raw
UNION ALL
SELECT 'zone_lookup', COUNT(*) FROM zone_lookup
UNION ALL
SELECT 'weather_hourly', COUNT(*) FROM weather_hourly;

-- Expected:
--   yellow_raw:     ~33,000,000
--   green_raw:      ~600,000
--   zone_lookup:    265
--   weather_hourly: 7,248

-- ============================================================
-- SECTION 2: Yellow taxi checks
-- ============================================================

SELECT
    MIN("tpep_pickup_datetime") AS earliest_pickup,
    MAX("tpep_pickup_datetime") AS latest_pickup,
    COUNT(DISTINCT YEAR("tpep_pickup_datetime")) AS distinct_years
FROM yellow_raw;

-- Spot check a few rows
SELECT * FROM yellow_raw LIMIT 5;

-- ============================================================
-- SECTION 3: Green taxi checks
-- ============================================================

SELECT
    MIN("lpep_pickup_datetime") AS earliest_pickup,
    MAX("lpep_pickup_datetime") AS latest_pickup,
    COUNT(DISTINCT YEAR("lpep_pickup_datetime")) AS distinct_years
FROM green_raw;

SELECT * FROM green_raw LIMIT 5;

-- ============================================================
-- SECTION 4: Zone lookup checks
-- ============================================================

SELECT * FROM zone_lookup LIMIT 10;

-- Confirm the "Unknown" and "Outside NYC" entries exist
SELECT * FROM zone_lookup WHERE LocationID IN (264, 265);

-- ============================================================
-- SECTION 5: Weather checks
-- ============================================================

SELECT * FROM weather_hourly LIMIT 10;

SELECT
    YEAR(DATETIME_LOCAL) AS yr,
    COUNT(*) AS hours
FROM weather_hourly
GROUP BY yr
ORDER BY yr;

-- Expected: ~3624 hours per year (2025 and 2026)

-- ============================================================
-- SECTION 6: COPY history (check for skipped/error rows)
-- ============================================================

SELECT file_name, status, row_count, row_parsed, first_error_message
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'YELLOW_RAW',
    START_TIME => DATEADD(hours, -24, CURRENT_TIMESTAMP())
))
ORDER BY file_name;

SELECT file_name, status, row_count, row_parsed, first_error_message
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'GREEN_RAW',
    START_TIME => DATEADD(hours, -24, CURRENT_TIMESTAMP())
))
ORDER BY file_name;

-- ============================================================
-- If all sections return expected results, Bronze is complete.
-- Proceed to 04_silver_transform.sql
-- ============================================================
