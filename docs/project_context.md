# Capstone Project Context

## Team

- **Team Name:** Team AMO
- **Members:** Maryam Choudhury, Ariana Lopez, Orlando Marin
- **Sprint:** Monday August 10 to Friday August 14, 2026
- **Demo Day:** Wednesday August 19, 2026 (20 minutes + 5 minutes Q&A)

## Project Summary

We are a three-person data consultancy building a working data platform on top of 10 months of NYC taxi trip records (Yellow and Green, Jan-May 2025 and Jan-May 2026) from a raw S3 bucket. We choose the analytical question, choose the architecture, and defend both.

## Data Source

- **Bucket:** `s3://techcatalyst-de-2026/raw/`
- **Yellow taxi:** 10+ files (Jan-May 2025, Jan-May 2026), 38,759,706 rows, Parquet
- **Green taxi:** 10+ files (same months), 465,029 rows, Parquet
- **Taxi zone lookup:** `taxi_zone_lookup.csv` (265 zones)
- **Weather enrichment:** Open-Meteo Historical Weather API (hourly, NYC Central Park, 7,248 rows)
- **Total:** 39,224,735 trip rows + 265 zones + 7,248 weather hours

## Process Reference

See [docs/pattern_a_steps.md](pattern_a_steps.md) for a detailed step-by-step log of what was done at each layer, why, and how to reproduce it.

## Architecture Decision: Pattern A (ELT, Warehouse-Centric)

```
S3 RAW (parquet)
   |  external stage + COPY INTO
   v
Snowflake AMO_BRONZE (yellow_raw, green_raw, zone_lookup, weather_hourly)
   |  dbt / SQL
   v
Snowflake AMO_SILVER (stg_trips, stg_zones, stg_weather)
   |  dbt
   v
Snowflake AMO_GOLD (marts serving analytical question)
   |
   v
Tableau + Streamlit (stretch goal)
```

**Why Pattern A:** Fewest moving parts, most reliable path for a one-week sprint. Team is strongest in SQL. All transformation is tested and version-controlled through dbt.

## Pipeline Files (orlando branch)

| File | Purpose |
| :--- | :--- |
| `pipeline/orchestrate.py` | Single-command pipeline orchestration (runs everything end-to-end) |
| `pipeline/snowflake_connect.py` | Python connection helper (reads snow.cfg) |
| `pipeline/01_bronze_load.sql` | S3 external stage + COPY INTO for taxi and zone data |
| `pipeline/02_fetch_weather.py` | Fetches Open-Meteo API and loads directly into Snowflake Bronze |
| `pipeline/03_bronze_verify.sql` | Verifies all Bronze tables loaded correctly |
| `pipeline/04_silver_transform.sql` | Reference SQL for Bronze to Silver (manual version with DQ flags) |
| `pipeline/snow.cfg` | Snowflake credentials (gitignored, never committed) |
| `dbt/models/staging/stg_trips.sql` | dbt staging model: union, derive, flag DQ issues |
| `dbt/models/staging/stg_zones.sql` | dbt staging model: clean zone lookup |
| `dbt/models/staging/stg_weather.sql` | dbt staging model: weather with categories |
| `dbt/models/marts/fct_trips.sql` | dbt mart: valid trips enriched with borough + weather + full revenue |
| `dbt/models/marts/mart_weather_demand.sql` | dbt mart: aggregated demand/revenue by borough, weather, time, payment |
| `dbt/models/marts/dim_zones.sql` | dbt mart: zone dimension for dashboard joins |
| `dbt/models/marts/dim_weather.sql` | dbt mart: weather dimension for dashboard drilldown |

**Run order (orchestrated):**
```bash
python pipeline/orchestrate.py
```

This single script executes all steps in order: Bronze infrastructure, data load, weather fetch, verification, dbt run (Silver + Gold), and dbt test. It is idempotent (safe to re-run) and fails fast with clear error messages.

**Manual run order (if needed):**
1. `pipeline/01_bronze_load.sql` in Snowflake worksheet
2. `python pipeline/02_fetch_weather.py` from terminal
3. `pipeline/03_bronze_verify.sql` in Snowflake worksheet (confirm all 4 tables)
4. `cd dbt && dbt run` (builds Silver + Gold layers)
5. `dbt test` (validates all models with automated checks)

## Stretch Goals

| Goal | Priority | Status |
| :--- | :--- | :--- |
| Orchestration (single idempotent Python script) | High | Done |
| Streamlit dashboard | Medium | Planned |
| BigQuery ML (forecast or clustering) | Low | Planned if time permits |

## Required Deliverables

1. Working pipeline from S3 RAW to Snowflake gold models
2. dbt Core project with staging models, mart models, and tests
3. Data Quality Incident Report
4. At least one defended 2025 vs 2026 year-over-year finding
5. Dashboard in Tableau or Looker
6. Architecture diagram of what was actually built
7. Cost and performance rationale
8. GitHub repository with README that lets someone re-run the work
9. AI use disclosure
10. Future state proposal with effort estimate
11. Demo Day presentation (every member speaking)
12. (Optional) Streamlit app, Databricks lane, BigQuery destination, AI enrichment

## Grading Rubric (100 points)

| Area | Weight |
| :--- | :--- |
| Pipeline: completeness, reliability, reproducibility | 25 |
| Data quality investigation and remediation | 15 |
| Modeling and analytics engineering | 15 |
| Analytical insight and year-over-year finding | 15 |
| Business intelligence delivery | 10 |
| Presentation, storytelling, and defense | 20 |

## Key Data Traps to Address

- **Cash tip trap:** `tip_amount` only populated for credit card; cash tips show as $0.00
- **Timestamps outside file's month:** Some records have pickup dates in wrong months/years
- **Impossible values:** Negative fares, zero-distance trips, passenger_count of 0, dropoff before pickup
- **Duplicates:** No natural primary key; must define what constitutes a duplicate
- **Schema differences:** Yellow uses `tpep_*` timestamps, Green uses `lpep_*`; Green has `ehail_fee` and `trip_type`, no `airport_fee`
- **2025 schema change:** `cbd_congestion_fee` column added starting Jan 2025

## Presentation Structure (20 min)

| Section | Time | Purpose |
| :--- | :--- | :--- |
| Problem and question | 2-3 min | What we set out to answer and why |
| Data and approach | 3-4 min | What we were given, data shape, architecture |
| Data quality | 2-3 min | What was wrong and what we did |
| Findings | 5-6 min | Year-over-year result with dashboard |
| Technical deep dive | 3-4 min | Design decisions, trade-offs, cost |
| Future state | 1-2 min | What we would build next |
| Recommendation | 1 min | What the client should do |

## Sprint Milestones

| Day | Focus | Checkpoint |
| :--- | :--- | :--- |
| Monday (Aug 10) | Charter, question, architecture, first data landing | One raw file in Snowflake + question in README |
| Tuesday (Aug 11) | Ingest all 20 files, union Yellow/Green, begin DQ report | All files loaded, unioned, row count reconciled |
| Wednesday (Aug 12) | dbt project, staging/mart models, tests, Architecture Defense | Architecture Defense (10 min + questions) |
| Thursday (Aug 13) | Gold models, dashboard, DQ report, cost rationale, diagrams | Dashboard connected showing real data |
| Friday (Aug 14) | Deliver everything, freeze pipeline, first rehearsal | All deliverables committed, pipeline runs clean |

## Snowflake Configuration

- **Account:** FFOJZFH-WPA36811
- **Database:** TECHCATALYST
- **Schemas:** AMO_BRONZE, AMO_SILVER (staging), AMO_GOLD (marts)
- **Role:** DE
- **Warehouse:** COMPUTE_WH
- **Credentials:** `snow.cfg` file (never commit)
- **Storage integration:** `s3_int` (pre-configured by instructor)
- **Loading:** External stage + COPY INTO with MATCH_BY_COLUMN_NAME

## GitHub Repository

- **URL:** https://github.com/orlandojmarin/nyc-taxi-capstone
- **Branch strategy:** main, develop, orlando, ariana, maryam
- Every team member commits code
- Decision log kept current in Team Charter

## Decisions to Record (for Architecture Defense and Demo Day)

- [x] Architecture pattern chosen: Pattern A (ELT, warehouse-centric)
- [x] Weather enrichment approach: Open-Meteo API loaded via Python connector
- [x] Bronze layer complete (Aug 10): 38.8M yellow, 465K green, 265 zones, 7,248 weather hours
- [x] Silver layer complete (Aug 11): dbt project with stg_trips (39.2M rows), stg_zones (265), stg_weather (7,248). DQ flags added. 16 tests (15 pass, 1 warn on payment_type).
- [x] Why models are tables vs views: staging models are tables (39M rows, too expensive to rebuild on every query as views; dashboard and Gold models read Silver repeatedly)
- [x] Analytical question chosen: "How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?"
- [x] Gold layer complete (Aug 11): fct_trips (38M rows), mart_weather_demand (34,719 rows), dim_zones (265), dim_weather (7,248). 16 Gold tests passing.
- [x] How we handled each data defect (Data Quality Incident Report complete, Aug 11)
- [ ] Warehouse size and auto-suspend settings
- [ ] What we cut if behind schedule

## Daily Progress

### Monday (Aug 10) - DONE
- [x] Created GitHub repo with branches (main, develop, orlando, ariana, maryam)
- [x] Bronze layer complete: 38,759,706 yellow + 465,029 green + 265 zones + 7,248 weather
- [x] Weather enrichment via Open-Meteo API, loaded directly via Python connector
- [x] Architecture diagrams updated (Pattern A includes weather)
- [x] Silver plan and Gold plan docs created
- [x] Collaborators added (Maryam accepted, Ariana invitation pending)
- Note: Column names from INFER_SCHEMA are case-sensitive (must use double quotes)

### Tuesday (Aug 11) - IN PROGRESS
- [x] dbt Core installed and configured (dbt-snowflake 1.12.0, profiles.yml connected)
- [x] Silver layer complete via dbt: stg_trips (39,224,735 rows), stg_zones (265), stg_weather (7,248)
- [x] Data quality flags added: is_valid + dq_flag_reason columns on stg_trips
- [x] dbt tests passing (15 pass, 1 expected warn on undocumented payment_type values)
- [x] Analytical question chosen: "How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?"
- [x] Gold layer complete: fct_trips (38,053,445 rows), mart_weather_demand (34,719), dim_zones (265), dim_weather (7,248)
- [x] Gold tests all passing (16/16)
- [x] dbt docs regenerated with full Bronze-Silver-Gold lineage
- [x] Orchestration script built and tested (orchestrate.py, 6.1 min end-to-end)
- [x] Data Quality Incident Report written (8 defects documented, including 2 not in catalog)
- [x] Tableau connection guide created for team
- [x] Team decision: Pattern A selected (Aug 11)
- [x] Presentation redesigned on Hartford template with colored content cards (24 slides)
- [ ] Document all decisions in team charter/decision log
- [ ] Connect Tableau to AMO_GOLD.MART_WEATHER_DEMAND (Maryam working on this)
- [ ] BigQuery ML (Ariana working on this)
- [ ] Streamlit app (stretch goal)

### Current Work Assignments (Aug 11)
- **Maryam:** Tableau dashboard connected to AMO_GOLD.MART_WEATHER_DEMAND
- **Orlando:** Presentation (slides, content, formatting)
- **Ariana:** BigQuery ML

### Team Exploration Path
Before selecting Pattern A, the team explored multiple approaches:
1. Ariana and Maryam initially investigated construction data as a potential enrichment source
2. Ariana and Maryam then collaborated on Pattern B (ETL with AWS Glue/Spark for Silver layer cleaning)
3. Orlando built and tested Pattern A (ELT, warehouse-centric with dbt)
4. Team decided Pattern A was the strongest path given timeline and reliability
All exploratory work informed the final architecture decision and is acknowledged in the presentation.

## Cut Order (if behind)

1. AI enrichment / BigQuery ML
2. Databricks lane
3. BigQuery second destination
4. Streamlit app
5. Additional enrichment datasets
6. Extra dbt models beyond what question needs
7. Narrow the analytical question itself

Never cut: pipeline, dbt models, data quality report, dashboard, or rehearsal.
