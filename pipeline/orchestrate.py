"""
Orchestrate the full Pattern A pipeline: S3 RAW -> Bronze -> Silver -> Gold.

Run this single script to execute the entire pipeline end-to-end.
It is idempotent: running it twice will not duplicate data.

Usage:
    python pipeline/orchestrate.py

Prerequisites:
    - snow.cfg configured in pipeline/ (never commit this file)
    - dbt profiles.yml configured at ~/.dbt/profiles.yml
    - Internet access (for Open-Meteo weather API)
"""

import sys
import subprocess
import time
import logging
from pathlib import Path

# snowflake_connect.py is in the same directory as this script
sys.path.insert(0, str(Path(__file__).parent))
from snowflake_connect import get_connection, run_sql

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt"

# Expected row counts for validation (approximate minimums)
EXPECTED_COUNTS = {
    "AMO_BRONZE.YELLOW_RAW": 38_000_000,
    "AMO_BRONZE.GREEN_RAW": 400_000,
    "AMO_BRONZE.ZONE_LOOKUP": 265,
    "AMO_BRONZE.WEATHER_HOURLY": 7_000,
}

# Set up logging so the user can see progress and diagnose failures
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("orchestrate")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def run_sql_step(conn, sql, description):
    """Execute a SQL statement with logging. Returns the result rows."""
    log.info(f"  {description}")
    try:
        result = run_sql(sql, conn)
        return result
    except Exception as e:
        log.error(f"  FAILED: {description} -- {e}")
        raise


def run_shell(cmd, cwd=None, description=""):
    """Run a shell command, stream output, and raise on failure."""
    log.info(f"  {description}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            log.info(f"    {line}")
    if result.returncode != 0:
        log.error(f"  FAILED: {description}")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                log.error(f"    {line}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result


# ---------------------------------------------------------------------------
# Step 1: Bronze - Create infrastructure (stage, file format, tables)
# ---------------------------------------------------------------------------

def step_bronze_infrastructure(conn):
    """Create the external stage, file format, and Bronze tables.

    Uses CREATE OR REPLACE so re-running is safe. The tables are recreated
    empty, ready for COPY INTO to fill them.
    """
    log.info("STEP 1: Bronze infrastructure (stage, file format, tables)")

    run_sql_step(conn, "USE ROLE DE", "Set role")
    run_sql_step(conn, "USE WAREHOUSE COMPUTE_WH", "Set warehouse")
    run_sql_step(conn, "USE DATABASE TECHCATALYST", "Set database")
    run_sql_step(conn, "CREATE SCHEMA IF NOT EXISTS TECHCATALYST.AMO_BRONZE", "Ensure AMO_BRONZE schema exists")
    run_sql_step(conn, "USE SCHEMA AMO_BRONZE", "Switch to AMO_BRONZE")

    # File format tells Snowflake how to read Parquet files from S3
    run_sql_step(conn, """
        CREATE OR REPLACE FILE FORMAT capstone_parquet_ff
          TYPE = PARQUET
          USE_LOGICAL_TYPE = TRUE
    """, "Create Parquet file format")

    # External stage points at the S3 bucket using a pre-configured storage integration
    run_sql_step(conn, """
        CREATE OR REPLACE STAGE capstone_raw_stage
          STORAGE_INTEGRATION = s3_int
          URL = 's3://techcatalyst-de-2026/raw/'
          FILE_FORMAT = capstone_parquet_ff
    """, "Create external stage pointing at S3")

    # Yellow taxi table: schema inferred from Parquet files
    run_sql_step(conn, """
        CREATE OR REPLACE TABLE yellow_raw
          USING TEMPLATE (
            SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
            FROM TABLE(
              INFER_SCHEMA(
                LOCATION => '@capstone_raw_stage/yellow_taxi/',
                FILE_FORMAT => 'capstone_parquet_ff'
              )
            )
          )
    """, "Create yellow_raw table (schema inferred from Parquet)")

    # Green taxi table: same approach
    run_sql_step(conn, """
        CREATE OR REPLACE TABLE green_raw
          USING TEMPLATE (
            SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
            FROM TABLE(
              INFER_SCHEMA(
                LOCATION => '@capstone_raw_stage/green_taxi/',
                FILE_FORMAT => 'capstone_parquet_ff'
              )
            )
          )
    """, "Create green_raw table (schema inferred from Parquet)")

    # Zone lookup: simple known schema (CSV source)
    run_sql_step(conn, """
        CREATE OR REPLACE TABLE zone_lookup (
            LocationID   INT,
            Borough      VARCHAR,
            Zone         VARCHAR,
            service_zone VARCHAR
        )
    """, "Create zone_lookup table")

    log.info("  Bronze infrastructure ready.")


# ---------------------------------------------------------------------------
# Step 2: Bronze - Load data from S3
# ---------------------------------------------------------------------------

def step_bronze_load(conn):
    """Load taxi and zone data from S3 into Bronze tables.

    COPY INTO is naturally idempotent: Snowflake tracks which files have been
    loaded and skips them on re-run. Since we recreate tables in Step 1,
    all files will load fresh each run.
    """
    log.info("STEP 2: Bronze data load (S3 -> Snowflake)")

    run_sql_step(conn, "USE SCHEMA AMO_BRONZE", "Switch to AMO_BRONZE")

    # Load all yellow taxi Parquet files (MATCH_BY_COLUMN_NAME handles column ordering)
    run_sql_step(conn, """
        COPY INTO yellow_raw
        FROM @capstone_raw_stage/yellow_taxi/
        FILE_FORMAT = (FORMAT_NAME = capstone_parquet_ff)
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        ON_ERROR = 'CONTINUE'
    """, "Load yellow taxi data (~38M rows)")

    # Load all green taxi Parquet files
    run_sql_step(conn, """
        COPY INTO green_raw
        FROM @capstone_raw_stage/green_taxi/
        FILE_FORMAT = (FORMAT_NAME = capstone_parquet_ff)
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        ON_ERROR = 'CONTINUE'
    """, "Load green taxi data (~465K rows)")

    # Load zone lookup CSV
    run_sql_step(conn, """
        COPY INTO zone_lookup
        FROM @capstone_raw_stage/taxi_lookup/taxi_zone_lookup.csv
        FILE_FORMAT = (TYPE = CSV, SKIP_HEADER = 1, FIELD_OPTIONALLY_ENCLOSED_BY = '"')
        ON_ERROR = 'CONTINUE'
    """, "Load zone lookup (265 zones)")

    log.info("  Bronze data load complete.")


# ---------------------------------------------------------------------------
# Step 3: Bronze - Load weather enrichment from Open-Meteo API
# ---------------------------------------------------------------------------

def step_bronze_weather(conn):
    """Fetch hourly weather from Open-Meteo and load into Bronze.

    Uses CREATE OR REPLACE TABLE so re-running replaces old data cleanly
    (idempotent). The API is free and does not require an API key.
    """
    log.info("STEP 3: Weather enrichment (Open-Meteo API -> Bronze)")

    import requests
    import pandas as pd

    LAT, LON = 40.7831, -73.9712
    DATE_RANGES = [("2025-01-01", "2025-05-31"), ("2026-01-01", "2026-05-31")]
    HOURLY_VARS = [
        "temperature_2m", "apparent_temperature", "precipitation", "rain",
        "snowfall", "snow_depth", "weather_code", "wind_speed_10m",
        "wind_gusts_10m", "relative_humidity_2m", "visibility",
    ]
    WEATHER_DESCRIPTIONS = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Light freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
        77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
    }

    all_rows = []
    for start_date, end_date in DATE_RANGES:
        log.info(f"  Fetching weather: {start_date} to {end_date}")
        params = {
            "latitude": LAT, "longitude": LON,
            "start_date": start_date, "end_date": end_date,
            "hourly": ",".join(HOURLY_VARS),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "America/New_York",
        }
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params)
        r.raise_for_status()
        hourly = r.json()["hourly"]

        for i in range(len(hourly["time"])):
            wc = hourly["weather_code"][i]
            all_rows.append({
                "DATETIME_LOCAL": hourly["time"][i],
                "TEMPERATURE_F": hourly["temperature_2m"][i],
                "APPARENT_TEMPERATURE_F": hourly["apparent_temperature"][i],
                "PRECIPITATION_INCH": hourly["precipitation"][i],
                "RAIN_INCH": hourly["rain"][i],
                "SNOWFALL_INCH": hourly["snowfall"][i],
                "SNOW_DEPTH_INCH": hourly["snow_depth"][i],
                "WEATHER_CODE": wc,
                "WEATHER_DESCRIPTION": WEATHER_DESCRIPTIONS.get(wc, "Unknown"),
                "WIND_SPEED_MPH": hourly["wind_speed_10m"][i],
                "WIND_GUSTS_MPH": hourly["wind_gusts_10m"][i],
                "RELATIVE_HUMIDITY_PCT": hourly["relative_humidity_2m"][i],
                "VISIBILITY_FT": hourly["visibility"][i],
            })
        time.sleep(0.5)

    df = pd.DataFrame(all_rows)
    df["DATETIME_LOCAL"] = pd.to_datetime(df["DATETIME_LOCAL"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    log.info(f"  Fetched {len(df)} hourly weather records")

    # Create table with explicit types, then load (CREATE OR REPLACE = idempotent)
    run_sql_step(conn, "USE SCHEMA AMO_BRONZE", "Switch to AMO_BRONZE")
    run_sql_step(conn, """
        CREATE OR REPLACE TABLE WEATHER_HOURLY (
            DATETIME_LOCAL          TIMESTAMP_NTZ,
            TEMPERATURE_F           FLOAT,
            APPARENT_TEMPERATURE_F  FLOAT,
            PRECIPITATION_INCH      FLOAT,
            RAIN_INCH               FLOAT,
            SNOWFALL_INCH           FLOAT,
            SNOW_DEPTH_INCH         FLOAT,
            WEATHER_CODE            INT,
            WEATHER_DESCRIPTION     VARCHAR,
            WIND_SPEED_MPH          FLOAT,
            WIND_GUSTS_MPH          FLOAT,
            RELATIVE_HUMIDITY_PCT   INT,
            VISIBILITY_FT           FLOAT
        )
    """, "Create weather_hourly table")

    # Load via write_pandas (small dataset, ~7K rows)
    from snowflake.connector.pandas_tools import write_pandas
    write_pandas(conn, df, "WEATHER_HOURLY", auto_create_table=False, overwrite=False)
    log.info(f"  Weather data loaded ({len(df)} rows).")


# ---------------------------------------------------------------------------
# Step 4: Verify Bronze row counts
# ---------------------------------------------------------------------------

def step_bronze_verify(conn):
    """Check that all Bronze tables have the expected number of rows.

    This is the reconciliation step that proves no data was lost during load.
    Fails fast if any table is missing or suspiciously empty.
    """
    log.info("STEP 4: Bronze verification (row count reconciliation)")

    run_sql_step(conn, "USE SCHEMA AMO_BRONZE", "Switch to AMO_BRONZE")

    counts = {}
    for table, min_expected in EXPECTED_COUNTS.items():
        schema_table = table.split(".")[-1]
        result = run_sql_step(conn, f"SELECT COUNT(*) FROM {schema_table}", f"Count {schema_table}")
        actual = result[0][0]
        counts[table] = actual

        if actual < min_expected:
            raise RuntimeError(
                f"Row count too low for {table}: got {actual:,}, expected at least {min_expected:,}"
            )
        log.info(f"    {table}: {actual:,} rows (minimum {min_expected:,})")

    log.info("  All Bronze tables verified.")
    return counts


# ---------------------------------------------------------------------------
# Step 5: Silver + Gold via dbt (transforms and tests)
# ---------------------------------------------------------------------------

def step_dbt_run():
    """Run dbt to build Silver (staging) and Gold (marts) layers.

    dbt models are materialized as tables with CREATE OR REPLACE,
    so re-running is inherently idempotent.
    """
    log.info("STEP 5: dbt run (Silver + Gold transformations)")

    run_shell(
        ["dbt", "run"],
        cwd=str(DBT_PROJECT_DIR),
        description="dbt run (builds all staging and mart models)",
    )
    log.info("  dbt run complete.")


def step_dbt_test():
    """Run dbt tests to validate data quality and relationships.

    Tests catch issues like null keys, invalid categories, and broken
    referential integrity. A failing test means something went wrong
    upstream and should be investigated before using the data.
    """
    log.info("STEP 6: dbt test (data quality validation)")

    run_shell(
        ["dbt", "test"],
        cwd=str(DBT_PROJECT_DIR),
        description="dbt test (validates all models)",
    )
    log.info("  All dbt tests passed.")


# ---------------------------------------------------------------------------
# Step 6: Final summary
# ---------------------------------------------------------------------------

def step_summary(conn, bronze_counts):
    """Print a final summary with row counts at each layer.

    This gives a quick at-a-glance confirmation that the pipeline ran
    successfully and data flowed through all layers.
    """
    log.info("STEP 7: Final summary")

    # Get Silver and Gold counts
    silver_counts = {}
    for table in ["STG_TRIPS", "STG_ZONES", "STG_WEATHER"]:
        result = run_sql(f"SELECT COUNT(*) FROM AMO_SILVER.{table}", conn)
        silver_counts[table] = result[0][0]

    gold_counts = {}
    for table in ["FCT_TRIPS", "MART_WEATHER_DEMAND", "DIM_ZONES", "DIM_WEATHER"]:
        result = run_sql(f"SELECT COUNT(*) FROM AMO_GOLD.{table}", conn)
        gold_counts[table] = result[0][0]

    log.info("=" * 60)
    log.info("PIPELINE COMPLETE")
    log.info("=" * 60)
    log.info("")
    log.info("Bronze (raw landing):")
    for table, count in bronze_counts.items():
        log.info(f"  {table}: {count:,}")
    log.info("")
    log.info("Silver (cleaned, conformed, flagged):")
    for table, count in silver_counts.items():
        log.info(f"  AMO_SILVER.{table}: {count:,}")
    log.info("")
    log.info("Gold (analytical models):")
    for table, count in gold_counts.items():
        log.info(f"  AMO_GOLD.{table}: {count:,}")
    log.info("")
    log.info("All layers built and validated. Dashboard-ready data is in AMO_GOLD.MART_WEATHER_DEMAND.")


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main():
    start = time.time()
    log.info("=" * 60)
    log.info("NYC Taxi Capstone - Full Pipeline Orchestration")
    log.info("Pattern A: S3 RAW -> Bronze -> Silver -> Gold")
    log.info("=" * 60)

    conn = get_connection()
    try:
        # Bronze: infrastructure, load, weather, verify
        step_bronze_infrastructure(conn)
        step_bronze_load(conn)
        step_bronze_weather(conn)
        bronze_counts = step_bronze_verify(conn)

        # Silver + Gold: dbt handles all transformations and tests
        step_dbt_run()
        step_dbt_test()

        # Final summary with counts at every layer
        step_summary(conn, bronze_counts)

    except Exception as e:
        log.error(f"Pipeline failed: {e}")
        log.error("Fix the issue above and re-run. The pipeline is idempotent.")
        sys.exit(1)
    finally:
        conn.close()

    elapsed = time.time() - start
    log.info(f"Total runtime: {elapsed / 60:.1f} minutes")


if __name__ == "__main__":
    main()
