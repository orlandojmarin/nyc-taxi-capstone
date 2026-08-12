# NYC Taxi Capstone Project Context

## Team and Question

- **Team AMO**: Maryam, Ariana, Orlando
- **Analytical Question**: "How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?"
- **Program**: Tech Catalyst Capstone

## Architecture

- **Pattern A**: ELT, warehouse-centric
- **Medallion layers**: Bronze (raw) -> Silver (cleaned/flagged) -> Gold (analytical)
- **Warehouse**: Snowflake (account: FFOJZFH-WPA36811, database: TECHCATALYST)
- **Schemas**: AMO_BRONZE, AMO_SILVER, AMO_GOLD
- **Transformations**: dbt Core 1.12.1 with dbt-snowflake 1.12.0
- **Visualization**: Streamlit (deployed via Streamlit Community Cloud from main branch)

## Branching and Deployment

- **Working branch**: `orlando`
- **Deployment flow**: Push to `orlando` triggers GitHub Action that selectively syncs specific files to `develop`, then to `main`
- **Streamlit Community Cloud** deploys from `main`
- **Synced files** (configured in `.github/workflows/merge-to-main.yml`):
  - `streamlit_app.py`
  - `requirements.txt`
  - `pipeline/snowflake_connect.py`
  - `docs/Capstone_Architecture_PatternA.drawio`
  - `docs/Capstone_Presentation.pptx`
  - `docs/data_quality_report.md`
  - `docs/pattern_a_steps.md`
- Other files (dbt models, other docs, data/) remain only on `orlando`

## Snowflake Connection

- **Credentials**: stored in `pipeline/snow.cfg` (gitignored, never committed)
- **dbt profiles**: `~/.dbt/profiles.yml` (profile name: `capstone`, target: `dev`)
- **Streamlit app**: queries Snowflake directly via `pipeline/snowflake_connect.py`
- **Role**: DE, **Warehouse**: COMPUTE_WH, **User**: ORLANDO

## Key Design Decisions

- **Data quality**: Flag rows with `IS_VALID` + `DQ_FLAG_REASON` columns in Silver. Do not delete invalid rows. Gold layer filters to `IS_VALID = TRUE`.
- **Null handling**: Not all nulls are dropped. Many nullable fields (passenger_count, airport_fee, congestion_surcharge) are legitimately null and still produce valid, analyzable trips.
- **Payment type**: Integer codes mapped to human-readable labels (Credit Card, Cash, etc.) in the Gold layer (`fct_trips.sql`), not in Streamlit.
- **Column casing**: Silver layer (`stg_trips.sql`) aliases all columns to UPPERCASE. Bronze columns are lowercase (from INFER_SCHEMA).
- **Mart pre-aggregation**: `mart_weather_demand` (30,251 rows) groups by borough, weather, year, month, hour, rush_hour, night, weekend, payment_type. Excludes Unknown/N/A boroughs (zone IDs 264/265).
- **fct_trips display**: Show only 1,000 rows via `LIMIT` in Streamlit (full 38M+ rows remain queryable in Snowflake for visualizations).

## Gold Layer Models

| Model | Rows | Purpose |
|-------|------|---------|
| fct_trips | 38M+ | Enriched fact table (trips + zones + weather) |
| mart_weather_demand | ~30K | Pre-aggregated for dashboards |
| dim_zones | 265 | Zone lookup with borough |
| dim_weather | ~7K | Hourly weather observations |

## Streamlit App

- Located at repo root: `streamlit_app.py`
- Queries Snowflake directly (10-minute cache via `@st.cache_data(ttl=600)`)
- Sidebar navigation for 4 gold tables
- Visualizations appear on the mart_weather_demand tab:
  1. Trip demand by year and weather (tabbed by borough)
  2. Year-over-year monthly trip volume (tabbed by borough)
  3. Average fare by borough and year (tabbed by weather category)
- Uses Altair for charts
- To run locally: `streamlit run streamlit_app.py --server.port 8501 --server.headless true`

## dbt Commands

```bash
cd /home/ec2-user/SageMaker/nyc-taxi-capstone/dbt
dbt run --select staging    # Silver layer
dbt run --select marts      # Gold layer
dbt test                    # All tests
dbt docs generate           # Lineage graph
```

## Files Not to Commit

- `pipeline/snow.cfg` (credentials)
- `~/.dbt/profiles.yml` (credentials)
- Any `.env` or token files
