-- ============================================================
-- Weather Enrichment: Load Open-Meteo hourly data into Snowflake
-- Capstone - Orlando
--
-- Prerequisites:
--   1. Run orlando/03_fetch_weather.py to generate weather_hourly.csv
--   2. Upload weather_hourly.csv to a Snowflake stage (see options below)
--
-- This gives us hourly weather for NYC (Central Park) covering
-- Jan-May 2025 and Jan-May 2026, matching our taxi trip dates.
-- ============================================================

USE ROLE DE;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE TECHCATALYST;
USE SCHEMA BRONZE;

-- ============================================================
-- SECTION 1: Create the weather table
-- ============================================================

CREATE OR REPLACE TABLE weather_hourly (
    datetime_local          TIMESTAMP_NTZ,
    temperature_f           FLOAT,
    apparent_temperature_f  FLOAT,
    precipitation_inch      FLOAT,
    rain_inch               FLOAT,
    snowfall_inch           FLOAT,
    snow_depth_inch         FLOAT,
    weather_code            INT,
    weather_description     VARCHAR,
    wind_speed_mph          FLOAT,
    wind_gusts_mph          FLOAT,
    relative_humidity_pct   INT,
    visibility_ft           FLOAT
);

-- ============================================================
-- SECTION 2: Load from internal stage (simplest method)
--
-- Option A: Use Snowflake's web UI to upload the CSV
--   1. Go to Data > Databases > TECHCATALYST > BRONZE > Stages
--   2. Click "+ Stage" > create a temporary internal stage, or use the table stage
--   3. Upload weather_hourly.csv
--   4. Then run the COPY INTO below
--
-- Option B: Use SnowSQL or the Python connector to PUT the file
--   PUT file:///path/to/weather_hourly.csv @~;
-- ============================================================

-- File format for the weather CSV
CREATE OR REPLACE FILE FORMAT weather_csv_ff
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  NULL_IF = ('');

-- If you uploaded to your user stage (@~):
COPY INTO weather_hourly
FROM @~/weather_hourly.csv
FILE_FORMAT = weather_csv_ff;

-- If you created a named internal stage:
-- COPY INTO weather_hourly
-- FROM @my_internal_stage/weather_hourly.csv
-- FILE_FORMAT = weather_csv_ff;

-- ============================================================
-- SECTION 3: Verify
-- ============================================================

SELECT COUNT(*) AS weather_rows FROM weather_hourly;
-- Expected: 7248 rows (151 days * 2 periods * 24 hours)

SELECT
    YEAR(datetime_local) AS yr,
    MONTH(datetime_local) AS mo,
    COUNT(*) AS hours,
    ROUND(AVG(temperature_f), 1) AS avg_temp_f,
    ROUND(SUM(precipitation_inch), 2) AS total_precip_inch,
    ROUND(SUM(snowfall_inch), 2) AS total_snow_inch
FROM weather_hourly
GROUP BY yr, mo
ORDER BY yr, mo;

-- ============================================================
-- SECTION 4: Silver layer weather view
-- ============================================================

USE SCHEMA SILVER;

-- Create a silver weather table with a date+hour key for joining to trips
CREATE OR REPLACE TABLE stg_weather AS
SELECT
    datetime_local,
    DATE(datetime_local)                AS weather_date,
    HOUR(datetime_local)                AS weather_hour,
    temperature_f,
    apparent_temperature_f,
    precipitation_inch,
    rain_inch,
    snowfall_inch,
    snow_depth_inch,
    weather_code,
    weather_description,
    wind_speed_mph,
    wind_gusts_mph,
    relative_humidity_pct,
    visibility_ft,
    -- Derived: simple weather category for easy grouping
    CASE
        WHEN weather_code IN (0, 1)         THEN 'Clear'
        WHEN weather_code IN (2, 3)         THEN 'Cloudy'
        WHEN weather_code IN (45, 48)       THEN 'Fog'
        WHEN weather_code BETWEEN 51 AND 57 THEN 'Drizzle'
        WHEN weather_code BETWEEN 61 AND 67 THEN 'Rain'
        WHEN weather_code BETWEEN 71 AND 77 THEN 'Snow'
        WHEN weather_code BETWEEN 80 AND 82 THEN 'Rain Showers'
        WHEN weather_code BETWEEN 85 AND 86 THEN 'Snow Showers'
        WHEN weather_code BETWEEN 95 AND 99 THEN 'Thunderstorm'
        ELSE 'Other'
    END AS weather_category,
    -- Derived: is it "bad weather" (useful for demand analysis)
    CASE
        WHEN weather_code >= 61 OR snowfall_inch > 0 OR wind_speed_mph > 25
        THEN TRUE ELSE FALSE
    END AS is_adverse_weather
FROM TECHCATALYST.BRONZE.weather_hourly;

-- Verify
SELECT weather_category, COUNT(*) AS hours, ROUND(AVG(temperature_f),1) AS avg_temp
FROM stg_weather
GROUP BY weather_category
ORDER BY hours DESC;

-- ============================================================
-- SECTION 5: Example join to trips (for your analysis later)
-- ============================================================

-- This shows how to join weather to trips by matching on date + hour.
-- Use this pattern in your gold layer / mart models.

-- SELECT
--     t.pickup_year,
--     t.pickup_month,
--     w.weather_category,
--     w.is_adverse_weather,
--     COUNT(*) AS trip_count,
--     ROUND(AVG(t.trip_duration_minutes), 1) AS avg_duration,
--     ROUND(AVG(t.total_amount), 2) AS avg_total
-- FROM SILVER.stg_trips t
-- JOIN SILVER.stg_weather w
--     ON DATE(t.pickup_at) = w.weather_date
--     AND HOUR(t.pickup_at) = w.weather_hour
-- GROUP BY 1, 2, 3, 4
-- ORDER BY 1, 2, trip_count DESC;
