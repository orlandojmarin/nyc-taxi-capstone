# Gold Layer Plan (Silver → Gold)

Gold is where your data becomes answers. Silver is generic (cleaned, conformed, anyone could use it). Gold is specific to YOUR analytical question.

---

## What Gold contains

- **Fact tables:** one row per trip, joined to dimensions, filtered to valid records only
- **Dimension tables:** zone names, weather categories (lookup tables for human-readable labels)
- **Mart/aggregation tables:** pre-computed summaries that answer your question directly (e.g., year-over-year comparisons)

---

## Part 1: dbt setup (one-time, ~30-45 min)

You haven't set up dbt for this project yet. Here's what that involves:

1. **Install dbt-snowflake** on your machine: `pip install dbt-snowflake`
2. **Copy the starter skeleton** from the Week 8 folder into your repo (it has `dbt_project.yml`, `_sources.yml`, sample `stg_trips.sql`)
3. **Create `profiles.yml`** with your Snowflake credentials (same info as `snow.cfg`, just in YAML format)
4. **Run `dbt debug`** to confirm the connection works
5. **Port your Silver SQL** into dbt staging models (replace raw SQL with `{{ source('bronze', 'yellow_raw') }}` references)

The starter skeleton already has most of this scaffolded. You're adapting, not starting from scratch.

---

## Part 2: Gold models to build

### fct_trips (fact table)

- Source: `stg_trips` joined to `stg_zones` (pickup and dropoff) and `stg_weather`
- Filters: only `is_valid = TRUE` records (the ones that passed cleaning)
- Adds: borough names, zone names, weather_category, is_adverse_weather
- Materialized as: **table** (queried repeatedly by dashboard)

### dim_zones (dimension)

- Source: `stg_zones`
- Just a clean copy with location_id, borough, zone_name, service_zone
- Materialized as: **table**

### dim_weather (dimension, optional)

- Source: `stg_weather`
- Hourly weather with category, useful for drilling into dashboard
- Materialized as: **table**

### mart_yoy_comparison (the money table)

- Source: `fct_trips`
- Aggregates by your analytical question dimensions (e.g., month, zone, weather, hour)
- Computes 2025 vs 2026 metrics side-by-side
- Calculates percent change year-over-year
- This is what your Tableau/Looker dashboard connects to
- Materialized as: **table**

---

## Part 3: dbt tests to add

| Test | Model | Column | Why |
| :--- | :--- | :--- | :--- |
| not_null | fct_trips | pickup_zone_id, dropoff_zone_id | Joins would silently drop rows |
| unique | dim_zones | location_id | Dimension key must be unique |
| accepted_values | fct_trips | taxi_type | Only 'yellow' and 'green' |
| accepted_values | fct_trips | payment_type | Values 1-6 only (warn, don't fail) |
| relationships | fct_trips | pickup_zone_id → dim_zones.location_id | Referential integrity |
| not_null | mart_yoy_comparison | pickup_year | Grouping key can't be null |

---

## Part 4: Analytical question (must decide before building Gold)

Your Gold layer is shaped by what you're asking. Example questions that work well:

- "How did the CBD congestion fee (Jan 2025) affect trip patterns, fares, and demand by zone?"
- "Does adverse weather increase demand, fares, or trip duration, and did that change YoY?"
- "Which zones saw the biggest YoY change in ridership, and why?"
- "Did tipping behavior change YoY, controlling for the cash tip trap?"

Pick ONE. The mart_yoy_comparison table is built to answer that specific question.

---

## Part 5: dbt commands (run order)

```bash
dbt deps          # install packages (if any)
dbt run           # builds all models (staging views + mart tables)
dbt test          # runs all tests
dbt docs generate # creates documentation + lineage graph
dbt docs serve    # opens the lineage graph in browser
```

---

## Time estimate: Silver → Gold vs Bronze → Silver

| Phase | Effort | Why |
| :--- | :--- | :--- |
| Bronze → Silver | ~1-1.5 hours | Fixed scope: union, rename, derive, clean. Same for everyone regardless of question. |
| Silver → Gold | ~2-3 hours | Variable scope: depends on your question, number of marts, dbt setup. More creative decisions involved. |

Gold takes longer because:
- You need to set up dbt (one-time cost)
- You need to decide your analytical question first
- The mart models require thinking about what aggregations serve your question
- dbt tests require thought about what would actually break your analysis
- You iterate: build a mart, look at the output, adjust

But the SQL itself is simpler. Gold queries are just GROUP BYs, JOINs, and CASE statements on top of already-clean Silver data. The complexity is in the decisions, not the code.

---

## Checklist

- [ ] Analytical question decided
- [ ] dbt installed and connected to Snowflake
- [ ] Staging models ported from manual SQL into dbt
- [ ] `dbt run` succeeds for staging layer
- [ ] `fct_trips` built (joined, filtered to valid)
- [ ] `dim_zones` built
- [ ] `mart_yoy_comparison` built (answers your question)
- [ ] `dbt test` passes (or warns with documented reasons)
- [ ] `dbt docs generate` produces lineage graph
- [ ] Dashboard (Tableau/Looker) connected to mart tables
