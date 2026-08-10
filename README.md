# NYC Taxi Trip Data Platform

**Team:** Orlando Marin, Ariana Lopez, Maryam Choudhury
**Program:** TechCatalyst Data Engineering 2026 Capstone
**Sprint:** August 10-14, 2026 | **Demo Day:** August 19, 2026

## Analytical Question

> (To be finalized Monday, August 10)

## Architecture

> (Pattern A or B, to be decided and documented Monday)

## Project Structure

```
nyc-taxi-capstone/
├── README.md
├── orlando/          # Orlando's working directory
├── ariana/           # Ariana's working directory
├── maryam/           # Maryam's working directory
├── dbt/              # dbt Core project (shared)
├── pipeline/         # Ingestion and orchestration scripts (shared)
├── docs/             # Team charter, data quality report, diagrams
└── .gitignore
```

## How to Re-Run This Pipeline

(To be completed by Friday, August 14)

## Data

- **Source:** `s3://techcatalyst-de-2026/raw/`
- **Yellow taxi:** 10 Parquet files (Jan-May 2025, Jan-May 2026), ~33M rows
- **Green taxi:** 10 Parquet files (same months), ~600K rows
- **Zone lookup:** `taxi_zone_lookup.csv` (265 zones)

## Deliverables

- [ ] Working pipeline (S3 RAW to Snowflake Gold)
- [ ] dbt Core project with staging/mart models and tests
- [ ] Data Quality Incident Report
- [ ] Year-over-year finding (defended)
- [ ] Tableau/Looker dashboard
- [ ] Architecture diagram
- [ ] Cost and performance rationale
- [ ] Future state proposal
- [ ] AI use disclosure
- [ ] Demo Day presentation
