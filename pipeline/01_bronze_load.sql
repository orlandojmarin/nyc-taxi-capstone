-- ============================================================
-- Pattern A: Bronze Load (S3 RAW -> Snowflake BRONZE)
-- Capstone - Orlando
--
-- Run this in a Snowflake worksheet, section by section.
-- After each section, verify the output before moving on.
-- ============================================================

-- ============================================================
-- SECTION 1: Set context
-- ============================================================

USE ROLE DE;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE TECHCATALYST;

-- Create the BRONZE schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS TECHCATALYST.BRONZE;
USE SCHEMA BRONZE;

-- ============================================================
-- SECTION 2: File format and external stage
-- ============================================================

-- Parquet file format
CREATE OR REPLACE FILE FORMAT capstone_parquet_ff
  TYPE = PARQUET
  USE_LOGICAL_TYPE = TRUE;

-- External stage pointing at the capstone RAW bucket
-- Uses the pre-configured storage integration (no explicit AWS keys needed)
CREATE OR REPLACE STAGE capstone_raw_stage
  STORAGE_INTEGRATION = s3_int
  URL = 's3://techcatalyst-de-2026/raw/'
  FILE_FORMAT = capstone_parquet_ff;

-- ============================================================
-- SECTION 3: Verify stage access (run these and confirm output)
-- ============================================================

-- Should show 10 yellow taxi Parquet files
LIST @capstone_raw_stage/yellow_taxi/;

-- Should show 10 green taxi Parquet files
LIST @capstone_raw_stage/green_taxi/;

-- Should show taxi_zone_lookup.csv (and possibly shapefiles zip)
LIST @capstone_raw_stage/taxi_lookup/;

-- ============================================================
-- SECTION 4: Inspect schemas BEFORE loading
-- ============================================================

-- Yellow taxi schema (check all columns, especially cbd_congestion_fee)
SELECT *
FROM TABLE(
  INFER_SCHEMA(
    LOCATION => '@capstone_raw_stage/yellow_taxi/',
    FILE_FORMAT => 'capstone_parquet_ff'
  )
)
ORDER BY ORDER_ID;

-- Green taxi schema (notice lpep_ timestamps, ehail_fee, trip_type, no airport_fee)
SELECT *
FROM TABLE(
  INFER_SCHEMA(
    LOCATION => '@capstone_raw_stage/green_taxi/',
    FILE_FORMAT => 'capstone_parquet_ff'
  )
)
ORDER BY ORDER_ID;

-- ============================================================
-- SECTION 5: Create bronze tables
-- ============================================================

-- Yellow: create table from inferred Parquet schema
CREATE OR REPLACE TABLE yellow_raw
  USING TEMPLATE (
    SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
    FROM TABLE(
      INFER_SCHEMA(
        LOCATION => '@capstone_raw_stage/yellow_taxi/',
        FILE_FORMAT => 'capstone_parquet_ff'
      )
    )
  );

-- Green: create table from inferred Parquet schema
CREATE OR REPLACE TABLE green_raw
  USING TEMPLATE (
    SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
    FROM TABLE(
      INFER_SCHEMA(
        LOCATION => '@capstone_raw_stage/green_taxi/',
        FILE_FORMAT => 'capstone_parquet_ff'
      )
    )
  );

-- Zone lookup: simple known schema (CSV)
CREATE OR REPLACE TABLE zone_lookup (
    LocationID   INT,
    Borough      VARCHAR,
    Zone         VARCHAR,
    service_zone VARCHAR
);

-- Verify table structures
DESCRIBE TABLE yellow_raw;
DESCRIBE TABLE green_raw;
DESCRIBE TABLE zone_lookup;

-- ============================================================
-- SECTION 6: Load data (COPY INTO)
-- ============================================================

-- Load all 10 yellow taxi files at once
COPY INTO yellow_raw
FROM @capstone_raw_stage/yellow_taxi/
FILE_FORMAT = (FORMAT_NAME = capstone_parquet_ff)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'CONTINUE';

-- Load all 10 green taxi files at once
COPY INTO green_raw
FROM @capstone_raw_stage/green_taxi/
FILE_FORMAT = (FORMAT_NAME = capstone_parquet_ff)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'CONTINUE';

-- Load zone lookup CSV
COPY INTO zone_lookup
FROM @capstone_raw_stage/taxi_lookup/taxi_zone_lookup.csv
FILE_FORMAT = (TYPE = CSV, SKIP_HEADER = 1, FIELD_OPTIONALLY_ENCLOSED_BY = '"')
ON_ERROR = 'CONTINUE';

-- ============================================================
-- SECTION 7: Verify loads (DO NOT SKIP)
-- ============================================================

-- Check COPY history for yellow (were any rows skipped?)
SELECT file_name, status, row_count, row_parsed, first_error_message
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'YELLOW_RAW',
    START_TIME => DATEADD(hours, -1, CURRENT_TIMESTAMP())
))
ORDER BY file_name;

-- Check COPY history for green
SELECT file_name, status, row_count, row_parsed, first_error_message
FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'GREEN_RAW',
    START_TIME => DATEADD(hours, -1, CURRENT_TIMESTAMP())
))
ORDER BY file_name;

-- Total row counts (record these for your Data Quality Report)
-- Expected: ~33M yellow, ~600K green, 265 zones
SELECT 'yellow_raw' AS table_name, COUNT(*) AS row_count FROM yellow_raw
UNION ALL
SELECT 'green_raw', COUNT(*) FROM green_raw
UNION ALL
SELECT 'zone_lookup', COUNT(*) FROM zone_lookup;

-- Quick sanity checks on yellow
-- Column names are lowercase because INFER_SCHEMA preserves Parquet case
SELECT
    MIN("tpep_pickup_datetime") AS earliest_pickup,
    MAX("tpep_pickup_datetime") AS latest_pickup,
    COUNT(DISTINCT YEAR("tpep_pickup_datetime")) AS distinct_years
FROM yellow_raw;

-- Quick sanity checks on green
SELECT
    MIN("lpep_pickup_datetime") AS earliest_pickup,
    MAX("lpep_pickup_datetime") AS latest_pickup,
    COUNT(DISTINCT YEAR("lpep_pickup_datetime")) AS distinct_years
FROM green_raw;

-- Zone lookup check
SELECT * FROM zone_lookup LIMIT 10;
SELECT COUNT(*) FROM zone_lookup WHERE LocationID IN (264, 265);
