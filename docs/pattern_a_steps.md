# Pattern A: Step-by-Step Process Log

What was done at each stage, why, and how to reproduce it. Issues encountered and how they were resolved are noted inline.

---

## Bronze Layer (S3 RAW to Snowflake BRONZE)

### Step 1: Create external stage and file format

**File:** `orlando/01_bronze_load.sql` (Sections 1-2)

Created a Parquet file format (`capstone_parquet_ff`) with `USE_LOGICAL_TYPE = TRUE` so timestamps come through correctly. Created an external stage (`capstone_raw_stage`) pointing at `s3://techcatalyst-de-2026/raw/` using the pre-configured `s3_int` storage integration.

**Why:** Snowflake needs a stage object to read from S3. The storage integration handles AWS credentials so we never store keys in code.

### Step 2: Inspect schemas before loading

**File:** `orlando/01_bronze_load.sql` (Section 4)

Used `INFER_SCHEMA` to read the Parquet column names and types from both Yellow and Green taxi files before creating any tables.

**Why:** Yellow and Green have different column names (`tpep_*` vs `lpep_*`, `airport_fee` vs `ehail_fee`). We needed to confirm what was actually in the files rather than assuming the documentation was correct.

**Issue found:** `INFER_SCHEMA` preserves the original Parquet column casing (all lowercase). This means the Bronze table columns are lowercase (e.g., `tpep_pickup_datetime`, not `TPEP_PICKUP_DATETIME`). In Snowflake, unquoted identifiers resolve to uppercase, so any query referencing these columns without double quotes fails silently or errors. This affected every downstream query.

### Step 3: Create Bronze tables and load data

**File:** `orlando/01_bronze_load.sql` (Sections 5-6)

- `yellow_raw`: created using `USING TEMPLATE` from inferred schema, loaded with `COPY INTO ... MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE`
- `green_raw`: same approach
- `zone_lookup`: created with explicit schema (simple CSV, 4 columns), loaded with `COPY INTO` from CSV

**Why:** `USING TEMPLATE` + `MATCH_BY_COLUMN_NAME` means we don't have to manually type out 19+ column definitions or worry about column order in the Parquet files. `ON_ERROR = 'CONTINUE'` ensures one bad record doesn't block the entire load.

**Issue resolved (case-sensitivity):** After loading, verification queries like `SELECT MIN(tpep_pickup_datetime)` failed with "invalid identifier." Fixed by wrapping all Bronze column references in double quotes: `SELECT MIN("tpep_pickup_datetime")`. This applies to yellow_raw and green_raw but NOT to zone_lookup (which was created with explicit uppercase column names).

**Result:** 38,759,706 yellow rows, 465,029 green rows, 265 zones.

### Step 4: Load weather enrichment

**File:** `orlando/02_fetch_weather.py`

Python script that calls the Open-Meteo Historical Weather API for NYC Central Park (Jan 2025 through May 2026), transforms the response into a DataFrame with imperial units and human-readable descriptions, then loads directly into `AMO_BRONZE.WEATHER_HOURLY` via the Snowflake Python connector.

**Why:** Weather is a natural enrichment for taxi demand analysis. Open-Meteo is free, requires no API key, and provides hourly granularity which matches well with trip pickup timestamps.

**Issue resolved (timestamp type):** Initial load using `write_pandas` with auto-create stored `DATETIME_LOCAL` as a string (VARCHAR), not a timestamp. Snowflake's `DATE()` and `HOUR()` functions failed on it downstream. Fixed by: (1) formatting the datetime as a string in Python before loading, and (2) creating the table with an explicit schema specifying `TIMESTAMP_NTZ` for the datetime column before calling `write_pandas`.

**Result:** 7,248 hourly weather records.

### Step 5: Verify Bronze

**File:** `orlando/03_bronze_verify.sql`

Row counts for all four tables, date range checks, and sample queries to confirm data looks reasonable.

**Why:** Reconciling row counts against source files is the single clearest signal of a trustworthy pipeline (per the rubric). We confirmed no rows were silently dropped during load.

---

## Silver Layer (Snowflake BRONZE to Snowflake SILVER via dbt)

### Step 6: Set up dbt project

**Files:** `dbt/dbt_project.yml`, `dbt/macros/generate_schema_name.sql`, `~/.dbt/profiles.yml`

Installed dbt Core 1.12.0 with the Snowflake adapter. Configured it to write staging models as tables in `TECHCATALYST.SILVER`. Added a `generate_schema_name` macro so dbt writes directly to the schema name specified (e.g., `SILVER`) rather than prefixing it with the target schema (which would produce `SILVER_SILVER`).

**Why:** dbt gives us repeatable builds (`dbt run` recreates everything), automated testing (`dbt test`), documentation with lineage graphs (`dbt docs generate`), and version-controlled SQL. The rubric requires a dbt Core project with staging models and tests.

### Step 7: Build stg_trips (union, derive, flag)

**File:** `dbt/models/staging/stg_trips.sql`

1. **Conform:** Union Yellow and Green into one table, renaming `tpep_*`/`lpep_*` to `pickup_at`/`dropoff_at`, adding `taxi_type` column. Columns that exist in only one source (`airport_fee` for Yellow, `ehail_fee` and `trip_type` for Green) carried through as NULLs for the other.

2. **Derive:** Computed `trip_duration_minutes`, `pickup_year`, `pickup_month`, `pickup_dayofweek`, `pickup_hour`, `is_night`, `is_weekend`, `is_rush_hour`. These power most analytical groupings without repeating CASE/DATEDIFF logic in every downstream query.

3. **Flag data quality:** Added `is_valid` (boolean) and `dq_flag_reason` (comma-separated list of which checks failed). A row is flagged invalid if it has: dropoff before pickup, negative fare, negative total, negative distance, distance over 100 miles, or pickup timestamp outside Jan-May 2025/2026.

**Why flag instead of delete:** The rubric says "finding a problem and silently deleting the rows is not an acceptable answer." By flagging, we can report exact counts per defect type in the DQ report, and Gold layer models can filter with `WHERE is_valid = TRUE` while preserving full traceability.

**Issue resolved (case-sensitivity in dbt):** First `dbt run` failed with "invalid identifier 'FARE_AMOUNT'." The Bronze columns are lowercase (from INFER_SCHEMA), and `SELECT *` in a CTE preserves that casing. But references like `fare_amount` in a later CTE get uppercased by Snowflake. Fixed by double-quoting all Bronze-originating column references in the is_valid/dq_flag_reason logic (e.g., `"fare_amount"`, `"trip_distance"`, `"total_amount"`). Derived columns we created ourselves (like `trip_duration_minutes`, `pickup_year`) don't need quotes because they were assigned as unquoted aliases.

**Issue resolved (rush hour definition):** Initial `is_rush_hour` used single-hour windows (7am and 5pm only). Adjusted to 2-hour windows (7-8am and 5-6pm) to better reflect actual NYC rush hour patterns.

**Result:** 39,224,735 rows (38,759,706 yellow + 465,029 green, zero row loss from Bronze to Silver).

### Step 8: Build stg_zones

**File:** `dbt/models/staging/stg_zones.sql`

Clean copy of `zone_lookup` with renamed columns (`LOCATIONID` to `location_id`, etc.) for consistent snake_case naming across Silver.

**Issue resolved (different casing than taxi tables):** Unlike the taxi tables (created via INFER_SCHEMA with lowercase columns), `zone_lookup` was created with an explicit `CREATE TABLE` statement, so its columns are uppercase. First dbt run failed when referencing `"LocationID"` (mixed case). Fixed by using unquoted uppercase column names (`LOCATIONID`, `BOROUGH`, `ZONE`, `SERVICE_ZONE`).

**Why:** Reference table that Gold models join to for readable borough/zone names instead of raw IDs.

### Step 9: Build stg_weather

**File:** `dbt/models/staging/stg_weather.sql`

Added derived columns: `weather_date`, `weather_hour`, `weather_category` (Clear/Cloudy/Fog/Drizzle/Rain/Snow/etc. based on WMO weather codes), and `is_adverse_weather` (TRUE when rain, snow, or high wind).

**Why:** Gold models can join trips to weather on date + hour to analyze weather impact on demand. The category and boolean flag simplify grouping without repeating weather code logic.

### Step 10: Configure and run dbt tests

**File:** `dbt/models/staging/_models.yml`, `dbt/models/staging/_sources.yml`

16 automated tests:
- `not_null` on key columns (pickup_at, dropoff_at, taxi_type, is_valid, location_id, borough, weather_date, weather_hour, weather_category)
- `unique` on zone location_id
- `accepted_values` on taxi_type (yellow/green), payment_type (1-6, warn severity), weather_category
- `relationships` on pickup_zone_id to zone_lookup LocationID (warn severity)

**Why:** Tests catch silent data corruption on rebuild. The warn-severity tests document known issues (undocumented payment_type values, potential zone mismatches) without blocking the pipeline. These feed directly into the DQ report.

**Issue found (payment_type):** Test revealed at least one `payment_type` value outside the documented 1-6 range. Set to warn (not error) because the trips themselves are valid; the unknown payment type is documented for the DQ report but doesn't invalidate the row's fare/distance/time data.

**Result:** 15 pass, 1 warn. Silver layer complete.

---

## Gold Layer (Snowflake SILVER to Snowflake GOLD via dbt)

### Step 11: Choose analytical question

**Question:** "How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?"

**Why this question:** It uses all three data sources (trips, zones, weather), produces a clear YoY comparison, generates visually compelling borough-level maps and charts, and leads to a concrete business recommendation (where to stage drivers during storms). The weather enrichment we built in Bronze becomes the core analytical differentiator rather than a decorative addition.

### Step 12: Build fct_trips (enriched fact table)

**File:** `dbt/models/marts/fct_trips.sql`

Joins `stg_trips` (filtered to `IS_VALID = TRUE`) with `stg_zones` (for pickup and dropoff borough/zone names) and `stg_weather` (on date + hour for weather conditions at time of pickup). Carries through all revenue columns: fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge, congestion_surcharge, cbd_congestion_fee, airport_fee, total_amount, and payment_type.

**Why:** A single enriched table that downstream models and ad-hoc queries can use without repeating joins. Filtering to valid records here means Gold consumers never accidentally include flagged rows.

**Issue resolved (mixed-case columns from Silver):** The Silver table `STG_TRIPS` has mixed column casing: columns we aliased in stg_trips.sql (like `pickup_at`, `taxi_type`) are stored as UPPERCASE, but columns passed through with double-quoted lowercase names from Bronze (like `"fare_amount"`, `"tip_amount"`) remain lowercase. Had to reference each column with the correct case: uppercase for aliased columns, double-quoted lowercase for pass-through columns. All columns are re-aliased to clean lowercase names in the output.

**Result:** 38,053,445 rows (filtered from 39.2M; ~1.17M rows flagged invalid in Silver were excluded).

### Step 13: Build mart_weather_demand (analytical aggregation)

**File:** `dbt/models/marts/mart_weather_demand.sql`

Aggregates fct_trips by: pickup_borough, weather_category, is_adverse_weather, pickup_year, pickup_month, pickup_hour, is_rush_hour, is_night, is_weekend, payment_type.

Metrics: trip_count, total_revenue, total_fares, total_tips, total_tolls, total_congestion_surcharge, total_cbd_fee, avg_fare_total, avg_tip, avg_duration_minutes, avg_distance.

**Why:** Pre-aggregated table (42,582 rows) that Tableau/Streamlit can query instantly. Contains every dimension needed to answer the question: borough (where), weather (condition), year/month (when/YoY), and payment_type (revenue breakdown). Keeps the dashboard fast without hitting 38M rows on every chart.

**Result:** 42,582 rows.

### Step 14: Build dim_zones and dim_weather

**Files:** `dbt/models/marts/dim_zones.sql`, `dbt/models/marts/dim_weather.sql`

Clean dimension tables in GOLD schema for dashboard joins and drilldowns.

**Why:** Dashboard tools need lookup tables to display human-readable zone names and weather details. Keeping dimensions in GOLD alongside the marts means the Tableau connection only needs one schema.

### Step 15: Run dbt test on Gold models

**File:** `dbt/models/marts/_models.yml`

16 tests covering: not_null on all key columns, accepted_values on taxi_type, unique on dim_zones.location_id, relationships (fct_trips.pickup_zone_id to dim_zones.location_id).

**Result:** 16 pass, 0 warn, 0 error.

---

## What's Next

- Connect Tableau/Looker to AMO_GOLD.MART_WEATHER_DEMAND (42K rows, instant queries)
- Build Streamlit app with interactive borough/weather/year filters
- Write Data Quality Incident Report (leveraging is_valid/dq_flag_reason from Silver)
- Architecture diagram of the full pipeline as built
- Presentation preparation
