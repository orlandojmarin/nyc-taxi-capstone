# Data Quality Incident Report

**Team:** AMO (Maryam Choudhury, Ariana Lopez, Orlando Marin)
**Date:** August 11, 2026

---

## Summary

| Metric | Count |
| :--- | :--- |
| Rows in source files (yellow + green) | 39,224,735 |
| Rows loaded to Bronze | 39,224,735 |
| Rows surviving to Silver | 39,224,735 (all kept, issues flagged not deleted) |
| Rows flagged invalid | 1,171,290 |
| Percentage flagged | 2.99% |
| Rows in Gold fact table | 38,053,445 |

Bronze to Silver lost zero rows. Every source record is accounted for. Invalid rows are flagged with `is_valid = FALSE` and a `dq_flag_reason` column that lists which checks failed. Gold filters to valid rows only.

---

## Defects found

### Defect 1: Negative fare amounts

**What it is**

Trips where `fare_amount` is less than zero. These represent meter adjustments, refunds, or correction entries rather than actual rides.

**How we found it**

Automated DQ check in `stg_trips.sql`: `fare_amount < 0`.

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records affected | 1,164,334 | 2.97% |

**Which metrics it would distort, and in which direction**

Would pull average fare and total revenue downward. A single correction entry of -$200 offsets hundreds of real $20 fares.

**Our decision:** Flag and exclude from Gold

**Why, and what we gave up**

These are accounting entries, not trips. Including them would produce negative revenue in some aggregation groups, which makes no sense for demand analysis. We lose visibility into the refund volume, but our question is about demand patterns, not accounting reconciliation.

---

### Defect 2: Negative total amounts

**What it is**

Trips where `total_amount` is less than zero. Often overlaps with negative fares but can also occur independently when surcharges are reversed.

**How we found it**

Automated DQ check in `stg_trips.sql`: `total_amount < 0`.

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records affected | 491,796 | 1.25% |

Note: Most of these overlap with negative fare records. The combined unique invalid count across all checks is 1,171,290.

**Which metrics it would distort, and in which direction**

Same as negative fares: pulls revenue metrics down and makes weather/demand comparisons unreliable if one weather condition happens to have more corrections.

**Our decision:** Flag and exclude from Gold

**Why, and what we gave up**

Same reasoning as negative fares. These are not real trips.

---

### Defect 3: Extreme trip distances (over 100 miles)

**What it is**

Trips reporting distances over 100 miles. NYC is roughly 35 miles end-to-end. A 100+ mile taxi trip within the five boroughs is not plausible.

**How we found it**

Automated DQ check in `stg_trips.sql`: `trip_distance > 100`.

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records affected | 2,141 | 0.005% |

**Which metrics it would distort, and in which direction**

Would inflate average trip distance significantly. A single 1,000-mile record offsets 50 normal 20-mile trips in an average calculation.

**Our decision:** Flag and exclude from Gold

**Why, and what we gave up**

These are clearly meter or GPS errors. Losing 2,141 records out of 39M is negligible.

---

### Defect 4: Dropoff before pickup

**What it is**

Trips where `dropoff_datetime` is earlier than `pickup_datetime`, making the trip duration negative.

**How we found it**

Automated DQ check in `stg_trips.sql`: `dropoff_at < pickup_at`.

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records affected | 49 | 0.0001% |

**Which metrics it would distort, and in which direction**

Would produce negative trip durations, pulling average duration down.

**Our decision:** Flag and exclude from Gold

**Why, and what we gave up**

Physically impossible. Negligible loss.

---

### Defect 5: Timestamps outside expected range

**What it is**

Trips with pickup timestamps outside January-May 2025 or January-May 2026. Some records have dates in other years entirely (meter or transmission errors).

**How we found it**

Automated DQ check in `stg_trips.sql`: year not in (2025, 2026) or month not in (1-5).

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records with out-of-range year | 41 | 0.0001% |
| Records with out-of-range month | 47 | 0.0001% |

**Which metrics it would distort, and in which direction**

Would create phantom data points in months/years we have no weather data for, breaking the weather join and producing NULL weather categories.

**Our decision:** Flag and exclude from Gold

**Why, and what we gave up**

88 records total. No meaningful loss.

---

### Defect 6: Undocumented payment_type = 0 (NOT in Data Catalog)

**What it is**

The TLC data dictionary defines payment types 1-6. However, 9,017,935 trips (23% of all records) carry `payment_type = 0`, which is not documented anywhere in the official data dictionary.

**How we found it**

dbt test `accepted_values` on `payment_type` flagged values outside 1-6. Investigation revealed type 0 is by far the largest undocumented value and carries normal fare amounts (avg $29.59, consistent with credit card trips at $29.58).

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records affected | 9,017,935 | 22.99% |

Year breakdown: 3,489,811 in 2025, 4,811,658 in 2026 (growing).

**Which metrics it would distort, and in which direction**

If excluded, we would lose nearly a quarter of all trips, severely understating demand. If misinterpreted as "unknown," any payment-type analysis would be wrong.

**Our decision:** Keep with caveat

**Why, and what we gave up**

Too large to be an error. Average fares match credit card trips exactly. Likely represents a valid payment method that the documentation has not been updated to reflect (possibly a mobile/app payment). We keep these in all demand and revenue analysis. In the Gold layer, both type 0 and type 5 are mapped to "Unknown" since neither has a confirmed meaning. This causes the mart to have fewer rows than it would with separate numeric codes (30,251 vs the previous 34,719) because groups that differed only by payment_type 0 vs 5 now merge.

---

### Defect 7: Null or zero passenger_count (NOT in Data Catalog)

**What it is**

Trips where `passenger_count` is NULL or 0. The field is driver-entered and not validated by the meter.

**How we found it**

Exploratory analysis during Silver layer development.

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records affected | 9,248,993 | 23.58% |

**Which metrics it would distort, and in which direction**

Any analysis of "trips by passenger count" or "average passengers" would be understated. Nearly a quarter of trips would appear to have zero riders.

**Our decision:** Keep with caveat

**Why, and what we gave up**

Our analytical question is about weather and demand, not passenger counts. These trips have valid timestamps, fares, distances, and locations. Excluding 23% of trips because a non-critical field is missing would gut our dataset. We do not use passenger_count in any Gold model or dashboard metric.

---

### Defect 8: total_amount does not equal sum of components

**What it is**

For 12,781,745 trips (33.6% of valid records), `total_amount` does not equal the sum of `fare_amount + extra + mta_tax + tip_amount + tolls_amount + improvement_surcharge + congestion_surcharge + cbd_congestion_fee + airport_fee`.

**How we found it**

Exploratory query comparing total_amount against the sum of its component columns.

The most common gaps are exactly $2.50 (5.7M trips) and $3.25 (4.0M trips), which correspond to the congestion surcharge and CBD congestion fee amounts. This happens because TLC changed when these fees were included in `total_amount` vs. tracked separately. The `total_amount` field was computed at the time of the trip, but the separate surcharge columns were added retroactively to the schema.

**Scale**

| | Count | Percent of total |
| :--- | :--- | :--- |
| Records affected | 12,781,745 | 33.59% |

**Which metrics it would distort, and in which direction**

If you sum individual components instead of using `total_amount`, you'll double-count the congestion surcharge for some trips. If you use `total_amount`, you'll undercount congestion revenue for trips where it was baked into the total before the column was split out.

**Our decision:** Keep, use total_amount as the revenue metric

**Why, and what we gave up**

`total_amount` is what the rider actually paid. It is the most consistently populated field across all time periods. We use it as our primary revenue metric in `mart_weather_demand`. We give up perfectly precise breakdowns of individual surcharge components, but our question is about total demand and total revenue, not surcharge-level accounting.

---

## Defects we found but did not address

| Defect | Scale | Why we left it | How it limits our conclusions |
| :--- | :--- | :--- | :--- |
| Zero-distance trips with real fares | 1,009,593 (2.7%) | Likely short hops where GPS didn't register movement. Fares and durations are normal. | Average distance metrics are slightly understated. |
| Zero total_amount trips | 6,228 (0.016%) | Mostly disputes (type 4) and no-charge (type 3). Real events, not errors. | Negligible effect on any metric. |
| Unknown/N/A pickup borough | 75,639 (0.2%) | Zone IDs 264/265 are TLC catch-all codes. Excluded from mart but kept in fct_trips. | Borough-level analysis misses 0.2% of trips. Not material. |
| EWR (Newark Airport) pickup borough | 4,386 (0.01%) | Newark Airport is in New Jersey, not an NYC borough. Our weather data is from Central Park and does not represent EWR conditions. JFK and LGA are categorized under Queens in the zone lookup, so including EWR alone would be inconsistent. Excluded from mart but kept in fct_trips. | Negligible. 4,386 trips out of 38M. |

---

## The cash tip question

`tip_amount` is recorded for credit card transactions but not for cash, so cash tips appear as zero.

**Does any of our analysis involve tips?** Yes, `avg_tip` and `total_tips` are columns in `mart_weather_demand`.

**How did we handle it?**

The mart includes `payment_type` as a grouping dimension (mapped to human-readable labels in Gold: Credit Card, Cash, No Charge, Dispute, Unknown, Voided). Any tip analysis should be filtered to `payment_type = 'Credit Card'` only. The Tableau connection guide explicitly warns about this.

Numbers:
- Credit card trips: avg tip = $4.22
- Cash trips: avg tip = $0.00 (not real, just unrecorded)
- Cash trips with zero tip: 3,631,578 out of 3,631,809 (99.99%)

**If we present a tipping chart, what does the slide say about this?**

"Tip data reflects credit card transactions only. Cash tips are not recorded by the meter and show as $0. Cash trips are excluded from this chart."

---

## What we would do with more time

1. **Investigate payment_type 0.** Cross-reference with VendorID to determine if it's vendor-specific. Check if it correlates with a specific app or platform.
2. **Deduplicate.** There is no natural primary key, so defining "duplicate" is non-trivial. We would define it as same pickup time + same pickup zone + same dropoff zone + same fare, then quantify how many exist.
3. **Validate zero-distance trips.** Cross-reference with duration and fare to determine if they're short hops, canceled trips, or GPS failures.
4. **Surcharge reconciliation.** Build a lookup of which months include congestion fees in total_amount vs. separately, to enable precise component-level revenue analysis.

---

## Effect on our conclusions

| Our finding | Could a data quality issue explain it? | Why we are confident, or how confident we are |
| :--- | :--- | :--- |
| Demand drops X% during adverse weather | No. Invalid rows (negative fares, impossible timestamps) are evenly distributed across weather conditions. Excluding them does not change the ratio. | High confidence. The 3% exclusion is not weather-correlated. |
| Manhattan has the highest volume | No. Payment_type 0 and zero-distance trips are proportional across boroughs. | High confidence. Borough ranking is robust. |
| Revenue per trip changes during bad weather | Possible minor effect. The total_amount accounting mismatch (congestion fee timing) could vary by time period. | Moderate confidence. The YoY comparison uses the same metric (total_amount) consistently, so relative comparisons hold even if absolute values are slightly off. |
| Year-over-year demand shifted | Unlikely. The growing payment_type 0 count (3.5M in 2025 vs 4.8M in 2026) is included in both years. If excluded, both years would shrink proportionally. | High confidence. We include type 0 in both years, so the comparison is fair. |
