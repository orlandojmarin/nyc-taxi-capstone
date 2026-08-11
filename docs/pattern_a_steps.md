# Pattern A: Step-by-Step Process Log

What was done at each stage, why, and how to reproduce it.

---

## Bronze Layer (S3 RAW to Snowflake BRONZE)

### Step 1: Create external stage and file format

**File:** `orlando/01_bronze_load.sql` (Sections 1-2)

Created a Parquet file format (`capstone_parquet_ff`) with `USE_LOGICAL_TYPE = TRUE` so timestamps come through correctly. Created an external stage (`capstone_raw_stage`) pointing at `s3://techcatalyst-de-2026/raw/` using the pre-configured `s3_int` storage integration.

**Why:** Snowflake needs a stage object to read from S3. The storage integration handles AWS credentials so we never store keys in code.

### Step 2: Inspect schemas before loading

**File:** `orlando/01_bronze_load.sql` (Section 4)

Used `INFER_SCHEMA` to read the Parquet column names and types from both Yellow and Green taxi files before creating any tables.

**Why:** Yellow and Green have different column names (`tpep_*` vs `lpep_*`, `airport_fee` vs `ehail_fee`). We needed to confirm what was actually in the files rather than assuming the documentation was correct. This also revealed that `INFER_SCHEMA` preserves case-sensitive column names (lowercase), which affects all downstream queries.

### Step 3: Create Bronze tables and load data

**File:** `orlando/01_bronze_load.sql` (Sections 5-6)

- `yellow_raw`: created using `USING TEMPLATE` from inferred schema, loaded with `COPY INTO ... MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE`
- `green_raw`: same approach
- `zone_lookup`: created with explicit schema (simple CSV, 4 columns), loaded with `COPY INTO` from CSV

**Why:** `USING TEMPLATE` + `MATCH_BY_COLUMN_NAME` means we don't have to manually type out 19+ column definitions or worry about column order in the Parquet files. `ON_ERROR = 'CONTINUE'` ensures one bad record doesn't block the entire load.

**Result:** 38,759,706 yellow rows, 465,029 green rows, 265 zones.

### Step 4: Load weather enrichment

**File:** `orlando/02_fetch_weather.py`

Python script that calls the Open-Meteo Historical Weather API for NYC Central Park (Jan 2025 through May 2026), transforms the response into a DataFrame with imperial units and human-readable descriptions, then loads directly into `BRONZE.WEATHER_HOURLY` via the Snowflake Python connector.

**Why:** Weather is a natural enrichment for taxi demand analysis. Open-Meteo is free, requires no API key, and provides hourly granularity which matches well with trip pickup timestamps.

**Result:** 7,248 hourly weather records.

### Step 5: Verify Bronze

**File:** `orlando/03_bronze_verify.sql`

Row counts for all four tables, date range checks, and sample queries to confirm data looks reasonable.

**Why:** Reconciling row counts against source files is the single clearest signal of a trustworthy pipeline (per the rubric). We confirmed no rows were silently dropped during load.

---

## Silver Layer (Snowflake BRONZE to Snowflake SILVER via dbt)

### Step 6: Set up dbt project

**Files:** `dbt/dbt_project.yml`, `dbt/macros/generate_schema_name.sql`, `~/.dbt/profiles.yml`

Initialized a dbt Core 1.12.0 project with the Snowflake adapter. Configured it to write staging models as tables in `TECHCATALYST.SILVER`. Added a `generate_schema_name` macro so dbt writes directly to `SILVER` (not a prefixed schema like `SILVER_SILVER`).

**Why:** dbt gives us repeatable builds (`dbt run` recreates everything), automated testing (`dbt test`), documentation with lineage graphs (`dbt docs generate`), and version-controlled SQL. The rubric requires a dbt Core project with staging models and tests.

### Step 7: Build stg_trips (union, derive, flag)

**File:** `dbt/models/staging/stg_trips.sql`

1. **Conform:** Union Yellow and Green into one table, renaming `tpep_*`/`lpep_*` to `pickup_at`/`dropoff_at`, adding `taxi_type` column. Columns that exist in only one source (airport_fee, ehail_fee, trip_type) carried through as NULLs for the other.

2. **Derive:** Computed `trip_duration_minutes`, `pickup_year`, `pickup_month`, `pickup_dayofweek`, `pickup_hour`, `is_night`, `is_weekend`, `is_rush_hour`. These power most analytical groupings without repeating CASE/DATEDIFF logic in every downstream query.

3. **Flag data quality:** Added `is_valid` (boolean) and `dq_flag_reason` (comma-separated list of which checks failed). A row is flagged invalid if it has: dropoff before pickup, negative fare, negative total, negative distance, distance over 100 miles, or pickup timestamp outside Jan-May 2025/2026.

**Why flag instead of delete:** The rubric says "finding a problem and silently deleting the rows is not an acceptable answer." By flagging, we can report exact counts per defect type in the DQ report, and Gold layer models can filter with `WHERE is_valid = TRUE` while preserving full traceability.

**Result:** 39,224,735 rows (38,759,706 yellow + 465,029 green, zero row loss from Bronze to Silver).

### Step 8: Build stg_zones

**File:** `dbt/models/staging/stg_zones.sql`

Clean copy of `zone_lookup` with renamed columns (`LocationID` to `location_id`, etc.) for consistent snake_case naming across Silver.

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

**Result:** 15 pass, 1 warn (payment_type value outside 1-6 exists in the data, documented for DQ report).

---

## What's next: Gold Layer

The Gold layer depends on choosing an analytical question. Gold mart models will:
- Filter to `is_valid = TRUE`
- Join trips to zones and weather
- Aggregate into the specific metrics needed to answer the question
- Serve as the data source for the Tableau/Looker dashboard
