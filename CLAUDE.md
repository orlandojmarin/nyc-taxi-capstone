# Capstone Project Context

## Team

- **Team Name:** Team AMO
- **Members:** Maryam Choudhury, Ariana Lopez, Orlando Marin
- **Sprint:** Monday August 10 to Friday August 14, 2026
- **Everything due:** Friday August 14, 2026
- **Demo Day:** Wednesday August 19, 2026 (20 minutes + 5 minutes Q&A)

## Analytical Question

**"How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?"**

Supporting analysis includes trip duration, revenue impact, and payment type breakdowns.

## Architecture: Pattern A (ELT, Warehouse-Centric)

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
Snowflake AMO_GOLD (fct_trips, mart_weather_demand, dim_zones, dim_weather)
   |
   v
Tableau + Streamlit
```

**Why Pattern A:** Fewest moving parts, most reliable path for a one-week sprint. Team is strongest in SQL. All transformation is tested and version-controlled through dbt.

## Data Source

- **Bucket:** `s3://techcatalyst-de-2026/raw/`
- **Yellow taxi:** 10 files (Jan-May 2025, Jan-May 2026), 38,759,706 rows, Parquet
- **Green taxi:** 10 files (same months), 465,029 rows, Parquet
- **Taxi zone lookup:** `taxi_zone_lookup.csv` (265 zones)
- **Weather enrichment:** Open-Meteo Historical Weather API (hourly, NYC Central Park, 7,248 rows)
- **Total:** 39,224,735 trip rows + 265 zones + 7,248 weather hours

## Snowflake Configuration

- **Account:** FFOJZFH-WPA36811
- **Database:** TECHCATALYST
- **Schemas:** AMO_BRONZE, AMO_SILVER, AMO_GOLD
- **Role:** DE
- **Warehouse:** COMPUTE_WH
- **User:** ORLANDO
- **Credentials:** `pipeline/snow.cfg` (gitignored, never committed)
- **dbt profiles:** `~/.dbt/profiles.yml` (profile name: `capstone`, target: `dev`)
- **Storage integration:** `s3_int` (pre-configured by instructor)
- **Loading:** External stage + COPY INTO with MATCH_BY_COLUMN_NAME

## Pipeline Files

| File | Purpose |
| :--- | :--- |
| `pipeline/orchestrate.py` | Single-command pipeline orchestration (runs everything end-to-end, idempotent, ~6 min) |
| `pipeline/snowflake_connect.py` | Python connection helper (reads snow.cfg) |
| `pipeline/01_bronze_load.sql` | S3 external stage + COPY INTO for taxi and zone data |
| `pipeline/02_fetch_weather.py` | Fetches Open-Meteo API and loads directly into Snowflake Bronze |
| `pipeline/03_bronze_verify.sql` | Verifies all Bronze tables loaded correctly |
| `pipeline/04_silver_transform.sql` | Reference SQL for Bronze to Silver (manual version with DQ flags) |
| `pipeline/snow.cfg` | Snowflake credentials (gitignored, never committed) |
| `dbt/models/staging/stg_trips.sql` | dbt staging: union Yellow+Green, derive time columns, DQ flags |
| `dbt/models/staging/stg_zones.sql` | dbt staging: clean zone lookup |
| `dbt/models/staging/stg_weather.sql` | dbt staging: weather with categories and adverse flag |
| `dbt/models/marts/fct_trips.sql` | dbt mart: valid trips enriched with borough + weather + revenue |
| `dbt/models/marts/mart_weather_demand.sql` | dbt mart: aggregated demand/revenue by borough, weather, time, payment |
| `dbt/models/marts/dim_zones.sql` | dbt mart: zone dimension for dashboard joins |
| `dbt/models/marts/dim_weather.sql` | dbt mart: weather dimension for drilldown |
| `streamlit_app.py` | Streamlit app (queries Snowflake directly) |
| `.github/workflows/merge-to-main.yml` | GitHub Action: selective file sync orlando -> develop -> main |

## Gold Layer Models

| Model | Rows | Purpose |
|-------|------|---------|
| fct_trips | 38,053,445 | Enriched fact table: valid trips joined with zones and weather |
| mart_weather_demand | 30,251 | Pre-aggregated for dashboards (by borough, weather, year, month, hour, rush_hour, night, weekend, payment_type) |
| dim_zones | 265 | Zone lookup with borough and service zone |
| dim_weather | 7,248 | Hourly weather observations with category and adverse flag |

## Key Design Decisions

- **Data quality approach:** Flag with `IS_VALID` + `DQ_FLAG_REASON` columns in Silver. Never delete invalid rows. Gold filters to `IS_VALID = TRUE`.
- **Null handling:** Not all nulls are dropped. Many fields (passenger_count, airport_fee, congestion_surcharge) are legitimately null and still produce valid, analyzable trips.
- **Payment type:** Integer codes mapped to labels (Credit Card, Cash, No Charge, Dispute, Unknown, Voided) in Gold layer (`fct_trips.sql`), not in Streamlit.
- **Column casing:** Silver (`stg_trips.sql`) aliases all columns to UPPERCASE. Bronze columns are lowercase from INFER_SCHEMA.
- **Mart excludes unknown boroughs:** Zone IDs 264/265 (Unknown, N/A) filtered out of `mart_weather_demand`.
- **fct_trips in Streamlit:** Only 1,000 rows shown (LIMIT). Full 38M+ rows remain in Snowflake.
- **Cash tip trap:** `tip_amount` only populated for credit card. Cash tips show as $0.00. Acknowledged in DQ report.
- **Models materialized as tables:** 39M rows too expensive to rebuild as views on every query.

## Streamlit App

- **File:** `streamlit_app.py` (repo root)
- **Data source:** Queries Snowflake directly via `pipeline/snowflake_connect.py`
- **Cache:** 10-minute TTL on all queries (`@st.cache_data(ttl=600)`)
- **Tables displayed:** mart_weather_demand (full), fct_trips (1,000 row LIMIT), dim_zones, dim_weather
- **Visualizations** (on the mart_weather_demand tab):
  1. Trip demand by year and weather condition (tabbed by borough, grouped bar)
  2. Year-over-year monthly trip volume (tabbed by borough, line chart)
  3. Average fare by borough and year (tabbed by weather category, grouped bar)
- **Charts:** Altair with `alt.data_transformers.disable_max_rows()`
- **Run locally:** `streamlit run streamlit_app.py --server.port 8501 --server.headless true`
- **Deployment:** Streamlit Community Cloud, pointed at `main` branch

## Branching and Deployment (CI/CD)

- **Working branch:** `orlando`
- **GitHub Action:** `.github/workflows/merge-to-main.yml`
- **Flow:** Push to `orlando` triggers selective file sync to `develop`, then `develop` to `main`
- **Only these files are synced** (everything else stays on `orlando` only):
  - `streamlit_app.py`
  - `requirements.txt`
  - `pipeline/snowflake_connect.py`
  - `docs/Capstone_Architecture_PatternA.drawio`
  - `docs/Capstone_Presentation.pptx`
  - `docs/data_quality_report.md`
  - `docs/pattern_a_steps.md`
- **To add/remove files from sync:** Edit the `FILES` array in the workflow YAML
- **Other team branches:** ariana, maryam

## dbt Commands

```bash
cd /home/ec2-user/SageMaker/nyc-taxi-capstone/dbt
dbt run --select staging    # Silver layer
dbt run --select marts      # Gold layer
dbt test                    # All tests (16 Gold pass, 15 Silver pass + 1 warn)
dbt docs generate           # Lineage graph
```

## Orchestration

```bash
python pipeline/orchestrate.py
```

Runs all steps in order: Bronze infrastructure, data load, weather fetch, verification, dbt run (Silver + Gold), and dbt test. Idempotent (safe to re-run). Takes ~6 minutes end-to-end.

## dbt Tests Summary

- **Silver:** 15 pass, 1 warn (undocumented payment_type values like 0)
- **Gold:** 16/16 pass (not_null on keys, accepted_values on taxi_type, relationships on zone join)

## Known Data Traps (addressed)

- **Cash tip trap:** `tip_amount` only for credit card; cash tips = $0.00
- **Timestamps outside file's month:** Some records have pickup dates in wrong months/years
- **Impossible values:** Negative fares, zero-distance trips, passenger_count of 0, dropoff before pickup
- **Duplicates:** No natural primary key; must define what constitutes a duplicate
- **Schema differences:** Yellow uses `tpep_*`, Green uses `lpep_*`; Green has `ehail_fee`/`trip_type`, no `airport_fee`
- **2025 schema change:** `cbd_congestion_fee` column added starting Jan 2025
- **Zone IDs 264/265:** Catch-all "unknown" and "outside of NYC" entries, excluded from mart

## Required Deliverables

| # | Deliverable | Status |
| :--- | :--- | :--- |
| 1 | Working pipeline from S3 RAW to Snowflake gold models | Done |
| 2 | dbt Core project with staging models, mart models, and tests | Done |
| 3 | Data Quality Incident Report | Done |
| 4 | At least one defended 2025 vs 2026 year-over-year finding | In progress |
| 5 | Dashboard in Tableau or Looker | Maryam working on this |
| 6 | Architecture diagram of what was actually built | Done (Capstone_Architecture_PatternA.drawio) |
| 7 | Cost and performance rationale | Not started |
| 8 | GitHub repository with README | Not started |
| 9 | AI use disclosure | Not started |
| 10 | Future state proposal with effort estimate | Not started |
| 11 | Demo Day presentation, every member speaking | In progress (Capstone_Presentation.pptx) |
| 12 | Streamlit app (optional/bonus) | Done |

## Grading Rubric (100 points)

| Area | Weight |
| :--- | :--- |
| Pipeline: completeness, reliability, reproducibility | 25 |
| Data quality investigation and remediation decisions | 15 |
| Modeling and analytics engineering | 15 |
| Analytical insight and the year-over-year finding | 15 |
| Business intelligence delivery | 10 |
| Presentation, storytelling, and defense | 20 |

Bonus (up to 5 points) for optional work that is genuinely integrated: Databricks lane, BigQuery comparison, Streamlit app, AI enrichment.

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

## Current Work Assignments

- **Orlando:** Streamlit app, pipeline orchestration, dbt models, presentation slides
- **Maryam:** Tableau dashboard connected to AMO_GOLD.MART_WEATHER_DEMAND
- **Ariana:** BigQuery ML

## Team Exploration Path

Before selecting Pattern A, the team explored multiple approaches:
1. Ariana and Maryam initially investigated construction data as potential enrichment
2. Ariana and Maryam then collaborated on Pattern B (ETL with AWS Glue/Spark)
3. Orlando built and tested Pattern A (ELT, warehouse-centric with dbt)
4. Team decided Pattern A was the strongest path given timeline and reliability
All exploratory work informed the final architecture decision and is acknowledged in the presentation.

## Sprint Progress

### Monday (Aug 10) - DONE
- Created GitHub repo with branches (main, develop, orlando, ariana, maryam)
- Bronze layer complete: 38,759,706 yellow + 465,029 green + 265 zones + 7,248 weather
- Weather enrichment via Open-Meteo API, loaded directly via Python connector
- Architecture diagrams updated (Pattern A includes weather)
- Silver plan and Gold plan docs created
- Collaborators added (Maryam accepted, Ariana invitation pending)
- Note: Column names from INFER_SCHEMA are case-sensitive (must use double quotes)

### Tuesday (Aug 11) - DONE
- dbt Core installed and configured (dbt-snowflake 1.12.0, profiles.yml connected)
- Silver layer complete via dbt: stg_trips (39,224,735 rows), stg_zones (265), stg_weather (7,248)
- Data quality flags added: IS_VALID + DQ_FLAG_REASON columns on stg_trips
- dbt tests passing (15 pass, 1 expected warn on undocumented payment_type values)
- Analytical question chosen
- Gold layer complete: fct_trips (38,053,445 rows), mart_weather_demand (30,251), dim_zones (265), dim_weather (7,248)
- Gold tests all passing (16/16)
- dbt docs regenerated with full Bronze-Silver-Gold lineage
- Orchestration script built and tested (orchestrate.py, 6.1 min end-to-end)
- Data Quality Incident Report written (8 defects documented, including 2 not in catalog)
- Tableau connection guide created for team
- Presentation redesigned on Hartford template with colored content cards (24 slides)

### Wednesday (Aug 12) - IN PROGRESS
- Streamlit app built with Snowflake connection and 3 visualizations
- GitHub Action set up for selective sync (orlando -> develop -> main)
- Streamlit Community Cloud deployment configured (from main branch)
- Architecture Defense completed

## GitHub Repository

- **URL:** https://github.com/orlandojmarin/nyc-taxi-capstone
- **Branch strategy:** main, develop, orlando, ariana, maryam
- Every team member commits code

## Visualization Reference: MLB Home Field Advantage Project

**Repo:** https://github.com/orlandojmarin/mlb-home-field-advantage
**Local clone:** `/home/ec2-user/SageMaker/mlb-home-field-advantage/mlb.py`

This is a prior Streamlit project by Orlando that sets the visual standard for the capstone. Key patterns to follow:

- **Consistent color scheme throughout:** Navy blue (`#002D72`) for one category, light gray (`#d9d9d9`) for the other, applied uniformly across every chart
- **Each visualization has a clear, insight-driven subheader** (states the finding, not just the chart type). Example: "Pitching Fuels MLB Home Field Advantage More Than Hitting" (not "Box Plot of Pitching Stats")
- **Expandable captions** with `st.expander("Show caption and interpretation")` beneath each chart explaining what the visualization shows and the key takeaway with specific numbers/percentages
- **Expandable "How to read this" sections** above complex charts (scatter plots) explaining what axes, colors, and positions mean
- **Clean layout:** `st.markdown("---")` dividers between sections, white plot backgrounds, light gray paper backgrounds (`#f5f5f5`), centered titles
- **Interactive elements:** Plotly for hover tooltips with detailed data, dropdowns (`st.selectbox`) to toggle between related metrics, tabs for related map views
- **Value labels on bar charts** showing exact numbers above each bar
- **Polished styling:** Black text, explicit font sizes (14-22), proper margins, no default Altair/Plotly chrome
- **Storytelling flow:** Visualizations build on each other to answer the core question progressively

**For the capstone app:** Aim for this same level of polish. Each visualization should state a finding in the subheader, include interpretation in an expander, use the consistent navy/gray color scheme (2025 = `#1a2456`, 2026 = `#a0a0a0`), and include interactivity where useful.

## Process Reference

See `docs/pattern_a_steps.md` for a detailed step-by-step log of what was done at each layer, why, and how to reproduce it.

## Files Not to Commit

- `pipeline/snow.cfg` (Snowflake credentials)
- `~/.dbt/profiles.yml` (Snowflake credentials)
- Any `.env` or token files

## Cut Order (if behind)

1. AI enrichment / BigQuery ML
2. Databricks lane
3. BigQuery second destination
4. ~~Streamlit app~~ (done)
5. Additional enrichment datasets
6. Extra dbt models beyond what question needs
7. Narrow the analytical question itself

Never cut: pipeline, dbt models, data quality report, dashboard, or rehearsal.
