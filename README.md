# NYC Taxi Trip Data Platform

**Team AMO:** Ariana Lopez, Maryam Choudhury, Orlando Marin

**Program:** TechCatalyst Data Engineering 2026 Capstone

**Sprint:** August 10-14, 2026 | **Demo Day:** August 19, 2026

## Overview

This project builds a complete data platform on top of 39+ million NYC taxi trip records (Yellow and Green, January-May 2025 and January-May 2026) to answer the question: **How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?**

Raw Parquet files land from S3 into Snowflake through an idempotent ELT pipeline, are transformed through dbt Core with full data quality flagging, enriched with hourly weather data, and served to both a Tableau dashboard and a Streamlit application.

**Live Streamlit App:** [nyc-taxi-capstone.streamlit.app](https://nyc-taxi-capstone.streamlit.app/)

## Analytical Question

> How does adverse weather (rain and snow) affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?

Supporting analysis includes time-of-day patterns, revenue per active minute, borough-level demand shifts, and year-over-year comparisons across weather types.

## Key Findings

- **Weather changes ride volume, not ride cost.** Average fares stay flat across all weather conditions and boroughs. The business risk is fewer rides, not less expensive ones.
- **In 2025, adverse weather increased demand. In 2026, it lowered demand.** The difference is driven by snow severity: rain increases ridership in both years, but the heavier snow in 2026 drove an overall demand decline.
- **The geographic response to weather shifted year over year.** Brooklyn's adverse-weather share grew from +0.2pp in 2025 to +0.9pp in 2026. Manhattan moved from +0.7pp to -0.5pp.
- **Brooklyn is the only borough where both demand and per-minute earnings rise during rain** (+27% demand, +11% earnings per active minute).
- **Drivers who stay on the road during snow earn more per active minute in every borough** (+8% in Manhattan to +29% in the Bronx).
- **Manhattan rush hour saw a $90K/hr revenue swing YoY:** adverse weather added $31K/hr in 2025 but cost $58K/hr in 2026.

## Architecture

**Pattern A: ELT, Warehouse-Centric**

```
S3 RAW (Parquet)
   |  External stage + COPY INTO
   v
Snowflake BRONZE (yellow_raw, green_raw, zone_lookup, weather_hourly)
   |  dbt Core
   v
Snowflake SILVER (stg_trips, stg_zones, stg_weather)
   |  dbt Core
   v
Snowflake GOLD (fct_trips, mart_weather_demand, dim_zones, dim_weather)
   |
   v
Tableau + Streamlit
```

**Why Pattern A:** Fewest moving parts for a one-week sprint. All transformation is SQL-based, tested, and version-controlled through dbt. Snowflake handles 39M rows natively with no memory management or chunking logic.

## Tech Stack

- **Cloud Warehouse:** Snowflake (COMPUTE_WH, auto-suspend)
- **Data Source:** AWS S3 (`s3://techcatalyst-de-2026/raw/`)
- **Transformation:** dbt Core 1.12 (dbt-snowflake)
- **Weather Enrichment:** Open-Meteo Historical Weather API
- **Pipeline Orchestration:** Python (`orchestrate.py`)
- **Visualization:** Tableau, Streamlit, Plotly
- **ML (Bonus):** BigQuery ML (K-Means clustering)
- **Version Control:** GitHub with branch-per-member workflow

## Data

| Source | Records | Format |
| :--- | ---: | :--- |
| Yellow taxi (Jan-May 2025, Jan-May 2026) | 38,759,706 | Parquet |
| Green taxi (Jan-May 2025, Jan-May 2026) | 465,029 | Parquet |
| Taxi zone lookup | 265 | CSV |
| Weather (NYC Central Park, hourly) | 7,248 | API (Open-Meteo) |
| **Total** | **39,232,248** | |

## Project Structure

```
nyc-taxi-capstone/
├── README.md
├── requirements.txt
├── streamlit_app.py                 # Streamlit data explorer
├── pipeline/
│   ├── orchestrate.py               # Single-command pipeline runner
│   ├── snowflake_connect.py         # Snowflake connection helper
│   ├── 01_bronze_load.sql           # S3 external stage + COPY INTO
│   ├── 02_fetch_weather.py          # Open-Meteo API fetch + load
│   ├── 03_bronze_verify.sql         # Row count verification
│   └── 04_silver_transform.sql      # Reference SQL (before dbt)
├── dbt/
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/                 # Silver layer (stg_trips, stg_zones, stg_weather)
│   │   └── marts/                   # Gold layer (fct_trips, mart_weather_demand, dim_*)
│   └── macros/
├── docs/
│   ├── Capstone_Presentation.pptx   # Demo Day presentation
│   ├── data_quality_report.md       # Data Quality Incident Report
│   ├── pattern_a_steps.md           # Step-by-step pipeline reproduction log
│   └── Capstone_Architecture_PatternA.drawio  # Architecture diagram
├── ml_clustering/
│   ├── bqml_clustering_code.sql     # BigQuery ML K-Means models
│   ├── kmeans_clustering_results.xlsx
│   └── README.md                    # Cluster analysis writeup
└── data/                            # CSV exports for Streamlit fallback
    ├── mart_weather_demand.csv
    ├── fct_trips_sample.csv
    ├── dim_zones.csv
    └── dim_weather.csv
```

## How to Re-Run This Pipeline

### Prerequisites

- Snowflake account with the `DE` role and access to `TECHCATALYST` database
- Python 3.9+ with packages from `requirements.txt`
- `pipeline/snow.cfg` configured with Snowflake credentials (see `pipeline/snow.cfg.template` format)
- `~/.dbt/profiles.yml` configured with a `capstone` profile targeting Snowflake
- Internet access for the Open-Meteo weather API

### Run the Full Pipeline

```bash
pip install -r requirements.txt
python pipeline/orchestrate.py
```

This executes all steps in order: Bronze infrastructure setup, data load from S3, weather API fetch, row count verification, dbt run (Silver + Gold layers), and dbt test. The pipeline is idempotent (safe to re-run) and completes in approximately 6 minutes.

### Run dbt Independently

```bash
cd dbt
dbt run --select staging     # Silver layer
dbt run --select marts       # Gold layer
dbt test                     # All tests (31 pass, 1 expected warn)
dbt docs generate            # Lineage graph
```

### Run the Streamlit App Locally

```bash
streamlit run streamlit_app.py --server.port 8501 --server.headless true
```

The app first attempts to read from local CSV files in `data/`, falling back to a live Snowflake connection if `pipeline/snow.cfg` is configured.

## Data Quality

We identified 8 data quality issues affecting 1,171,290 rows (3.0% of total). Each defect is quantified, its impact analyzed, and a keep/flag/exclude decision justified in the [Data Quality Incident Report](docs/data_quality_report.md).

Key decisions:
- **Negative fares and impossible timestamps:** Flagged invalid, excluded from Gold
- **Payment type 0 (undocumented, 23% of trips):** Kept, mapped to "Unknown" since fare patterns match credit card trips
- **Cash tip trap:** Acknowledged in all tip analysis, filtered to credit card only when presenting tips
- **Zero-distance trips (2.7%):** Kept, since fares and durations are normal (likely short hops)

## Cost and Performance Rationale

- **Table types:** Transient tables in Bronze (re-loadable from S3, no time travel needed). Permanent tables in Silver and Gold (point-in-time recovery valuable for debugging).
- **Warehouse:** COMPUTE_WH with auto-suspend at 5 minutes. X-Small sufficient for 39M row loads and dbt runs.
- **File sizing:** Parquet files from S3 are already well-sized (50-200MB each). No splitting or compaction needed.
- **dbt materialization:** All models materialized as tables (not views) because 39M rows are too expensive to rebuild on every query. Incremental would be the next step at 10x scale.
- **At 10x scale:** Switch Gold fact table to incremental materialization, add clustering keys on pickup_year and pickup_borough, consider multi-cluster warehouse for concurrent dashboard queries.

## Future State

With additional time and budget, we would:

1. **Real-time ingestion (highest impact):** Stream trip and weather data continuously via Snowpipe for minute-level demand signals during active storms.
2. **ML demand forecasting:** Predict demand changes before weather events occur to improve driver positioning and reduce idle time.
3. **Expanded analysis:** Extend to full-year data for seasonal patterns and incorporate Uber/Lyft data to compare surge pricing behavior during adverse weather.

## AI Use Disclosure

AI assistants were used during this project for:
- Pipeline development and SQL transformations
- Streamlit visualizations and chart logic
- Data analysis and revenue calculations
- Presentation content and speaker notes

**How we verified:**
- Ran full pipeline end-to-end and reconciled row counts against source files
- Cross-checked all calculations against raw data and Tableau results
- Reviewed and revised all generated content before committing
- Every number on every slide traces back to a verifiable query

**What we corrected:**
- Fare calculations initially included tips, inflating averages. Caught and corrected.
- Hourly earnings used an unverifiable utilization assumption. Replaced with revenue per active minute.
- Initial summary slide was descriptive. Reworked to be prescriptive with data-backed actions.

## Contributors

| Team Member | Primary Contributions |
| :--- | :--- |
| Ariana Lopez | BigQuery ML clustering analysis, architecture diagram, Pattern B exploration (AWS Glue + PySpark), permit data investigation |
| Maryam Choudhury | Tableau dashboard (YoY analysis + clustering visualizations), Pattern B exploration, permit data investigation |
| Orlando Marin | Pipeline orchestration, dbt models, Streamlit app, documentation (DQ report, pattern_a_steps), repo management |

## License

This project was developed for educational purposes as part of the TechCatalyst Data Engineering 2026 program.
