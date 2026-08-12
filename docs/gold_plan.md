# Gold Layer Plan (Silver to Gold)

Gold is where your data becomes answers. Silver is generic (cleaned, conformed, anyone could use it). Gold is specific to the analytical question.

---

## Analytical Question

**"How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?"**

Supporting analysis includes trip duration, revenue impact, and payment type breakdowns.

---

## Gold Models (built and passing)

### fct_trips (fact table)

- **Source:** `stg_trips` joined to `stg_zones` (pickup and dropoff) and `stg_weather` (on date + hour)
- **Filter:** only `IS_VALID = TRUE` records
- **Adds:** pickup/dropoff borough and zone names, weather_category, is_adverse_weather, temperature, precipitation, wind speed
- **Revenue columns:** fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge, congestion_surcharge, cbd_congestion_fee, airport_fee, total_amount
- **Payment type:** mapped from integer codes to labels (Credit Card, Cash, No Charge, Dispute, Unknown, Voided)
- **Materialized as:** table (38,053,445 rows)

### mart_weather_demand (the main analytical table)

- **Source:** `fct_trips`
- **Grouped by:** pickup_borough, weather_category, is_adverse_weather, pickup_year, pickup_month, pickup_hour, is_rush_hour, is_night, is_weekend, payment_type
- **Filter:** Excludes trips with pickup_borough of 'Unknown' or 'N/A' (zone IDs 264/265 that cannot be attributed to a real borough)
- **Metrics:** trip_count, total_revenue, total_fares, total_tips, total_tolls, total_congestion_surcharge, total_cbd_fee, avg_fare_total, avg_tip, avg_duration_minutes, avg_distance
- **Materialized as:** table (30,251 rows)
- **Use:** This is what Tableau/Streamlit connects to. Pre-aggregated so dashboards are fast.

### dim_zones (dimension)

- **Source:** `stg_zones`
- **Columns:** location_id, borough, zone_name, service_zone
- **Materialized as:** table (265 rows)

### dim_weather (dimension)

- **Source:** `stg_weather`
- **Columns:** All weather attributes plus category and adverse flag
- **Materialized as:** table (7,248 rows)
- **Use:** Drilldown in dashboard, join for ad-hoc queries

---

## dbt Tests (Gold layer)

16 tests, all passing:

| Test | Model | Column | Purpose |
| :--- | :--- | :--- | :--- |
| not_null | fct_trips | pickup_at | Core timestamp |
| not_null | fct_trips | taxi_type | Required for any split |
| accepted_values | fct_trips | taxi_type (yellow/green) | Only two valid types |
| not_null | fct_trips | pickup_borough | Borough join worked (warn) |
| not_null | fct_trips | total_amount | Revenue column present |
| relationships | fct_trips | pickup_zone_id to dim_zones (warn) | Referential integrity |
| unique | dim_zones | location_id | Dimension key |
| not_null | dim_zones | location_id | Dimension key |
| not_null | dim_zones | borough | Required grouping |
| not_null | dim_weather | weather_date | Join key |
| not_null | dim_weather | weather_hour | Join key |
| not_null | dim_weather | weather_category | Grouping column |
| not_null | mart_weather_demand | pickup_borough | Grouping key |
| not_null | mart_weather_demand | pickup_year | YoY key |
| not_null | mart_weather_demand | trip_count | Core metric |
| not_null | mart_weather_demand | total_revenue | Core metric |

---

## How mart_weather_demand answers the question

To compare demand during adverse vs clear weather by borough, YoY:

```sql
SELECT
    pickup_borough,
    pickup_year,
    is_adverse_weather,
    SUM(trip_count) as trips,
    SUM(total_revenue) as revenue,
    AVG(avg_duration_minutes) as avg_duration
FROM AMO_GOLD.MART_WEATHER_DEMAND
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
```

For Tableau/Streamlit, connect directly to `AMO_GOLD.MART_WEATHER_DEMAND`. It's small (~30K rows) and pre-aggregated, so dashboards are instant. Only trips attributable to a real NYC borough are included (Unknown/N/A excluded).

---

## dbt Commands

```bash
dbt run --select marts    # builds Gold models
dbt test --select marts   # validates Gold models
dbt docs generate         # updates lineage graph
```

---

## What's Next

- [ ] Connect Tableau to `AMO_GOLD.MART_WEATHER_DEMAND`
- [ ] Build Streamlit app with interactive borough/weather filters
- [ ] Write Data Quality Incident Report (using DQ flags from Silver)
- [ ] Architecture diagram of what was actually built
- [ ] Prepare presentation with YoY weather-demand findings

---

## Checklist

- [x] Analytical question decided
- [x] dbt installed and connected to Snowflake
- [x] Staging models built and tested (Silver layer)
- [x] `fct_trips` built (joined, filtered to valid, enriched with borough + weather)
- [x] `dim_zones` built
- [x] `dim_weather` built
- [x] `mart_weather_demand` built (answers the question with revenue breakdown)
- [x] `dbt test` passes (16/16 on Gold, 15 pass + 1 warn on Silver)
- [x] `dbt docs generate` produces lineage graph
- [ ] Dashboard (Tableau) connected to mart tables
- [ ] Streamlit app (stretch goal)
