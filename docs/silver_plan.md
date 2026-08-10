# Silver Layer Plan (Bronze → Silver)

This covers everything that happens between Bronze (raw) and Silver (clean, conformed, ready for analysis). Silver has four parts: conforming, deriving, cleaning, and enrichment.

## General Approach

- **Flag, don't delete.** Add an `is_valid` column so we can report what was removed and why.
- **Document counts.** Record how many rows fail each check for the Data Quality Report.
- **Cash tip trap:** Never average `tip_amount` across all payment types. Cash tips show as $0.00, which understates tipping for cash trips.

---

## Part 1: Conforming (make the data consistent)

- **Union yellow + green** into one `stg_trips` table
- **Rename columns** to common names: `tpep_pickup_datetime` / `lpep_pickup_datetime` → `pickup_at`
- **Add `taxi_type` column** ('yellow' or 'green') so we know which fleet each row came from
- **Handle schema differences:** Green has `ehail_fee` and `trip_type` (Yellow gets NULLs); Yellow has `airport_fee` (Green gets NULL)
- **Standardize case:** all column names lowercase/snake_case in Silver

## Part 2: Derived Columns (compute useful fields)

- `trip_duration_minutes` = DATEDIFF(minute, pickup_at, dropoff_at)
- `pickup_year` = YEAR(pickup_at)
- `pickup_month` = MONTH(pickup_at)
- `pickup_dayofweek` = DAYOFWEEK(pickup_at)
- `pickup_hour` = HOUR(pickup_at)
- `is_night` = TRUE if pickup between 8pm and 6am
- `is_weekend` = TRUE if Saturday or Sunday
- `is_rush_hour` = TRUE if weekday AND (7-9am or 4-7pm)

## Part 3: Supporting Tables

- **stg_zones:** clean copy of zone_lookup with renamed columns (location_id, borough, zone_name, service_zone)
- **stg_weather:** adds `weather_date`, `weather_hour`, `weather_category`, `is_adverse_weather` from Bronze weather_hourly

## Part 4: dbt (where it comes in)

- The manual SQL in `04_silver_transform.sql` is a prototype. Once validated, port it into dbt staging models.
- dbt adds: automated testing (not_null, unique, accepted_values, relationships), documentation, lineage graphs, and repeatable runs.
- dbt staging models = Silver layer. dbt mart models = Gold layer.

---

## Part 5: Data Cleaning (flag bad records)

### stg_trips (yellow_raw + green_raw)

### Timestamps

- **Dropoff before pickup:** `dropoff_at < pickup_at`
  - These are meter errors. Flag as invalid.
- **Trips outside expected date range:** pickup not in Jan-May 2025 or Jan-May 2026
  - Known issue: some files contain timestamps in wrong months/years.
- **Extremely short trips:** duration < 1 minute with distance > 0
  - Likely meter resets or test trips.
- **Extremely long trips:** duration > 4 hours
  - Could be forgotten meters. Flag and investigate, don't auto-remove.

### Distance

- **Negative distance:** `trip_distance < 0`
  - Should not exist. Flag as invalid.
- **Zero distance with fare > $5:** `trip_distance = 0 AND fare_amount > 5`
  - Meter malfunction or flat-rate trip not recorded properly.
- **Extreme distance:** `trip_distance > 100` miles
  - NYC taxi trips don't go 100+ miles. Flag as invalid.

### Fares and Amounts

- **Negative fare:** `fare_amount < 0`
  - These are adjustments/refunds, not real trips. Flag as invalid.
- **Negative total:** `total_amount < 0`
  - Same as above.
- **Total doesn't match components:** `total_amount != fare_amount + extra + mta_tax + tip_amount + tolls_amount + improvement_surcharge + congestion_surcharge + airport_fee + cbd_congestion_fee`
  - Quantify how many. May be rounding or legitimate (cash tips not in total). Document, don't necessarily remove.

### Passengers

- **Null or zero passengers:** `passenger_count IS NULL OR passenger_count = 0`
  - Driver-entered field, often unreliable. Document the count but don't remove rows.
- **Excessive passengers:** `passenger_count > 6`
  - Max legal capacity for a standard taxi is 5-6. Flag but don't remove (some vans hold more).

### Categorical Columns

- **Invalid payment_type:** values outside 1-6
  - Document any unexpected values for the DQ report.
- **Invalid RatecodeID:** values outside 1-6 and 99
  - Same as above.
- **Invalid vendor_id:** values outside expected set
  - Document.

### Location

- **Unknown zones:** `pickup_zone_id` or `dropoff_zone_id` = 264 or 265
  - 264 = "Unknown", 265 = "Outside NYC". Don't remove, but be aware these skew zone-level analysis.
- **Null zones:** `pickup_zone_id IS NULL OR dropoff_zone_id IS NULL`
  - Document count.

### Duplicates

- **No natural primary key exists.** Two identical rows could be two real trips.
- Check for exact duplicates (all columns match). If found, keep one.
- Don't deduplicate on partial matches (same time + location) since those could be different passengers.

---

## zone_lookup

- **No cleaning needed.** This is a reference table with 265 fixed rows.
- Confirm IDs 264 and 265 exist (Unknown, Outside NYC).

---

## weather_hourly

- **Null weather values:** check for nulls in temperature, precipitation, wind
  - Open-Meteo occasionally returns nulls for missing sensor readings. Leave as-is (nulls are honest).
- **No filtering needed.** This is already clean API output.
- Silver transform adds derived columns (`weather_category`, `is_adverse_weather`) but doesn't remove rows.

---

## Summary of Actions

| Check | Action | Why |
| :--- | :--- | :--- |
| Dropoff before pickup | Flag invalid | Physically impossible |
| Negative fare/total | Flag invalid | Refunds, not trips |
| Negative/extreme distance | Flag invalid | Meter errors |
| Timestamps outside range | Flag invalid | File transmission errors |
| Zero passengers | Document only | Unreliable field, not worth removing |
| Cash tip = $0 | Document only | Not an error, just how cash works |
| Unknown zones (264/265) | Document only | Real trips, just unknown location |
| Exact duplicates | Remove duplicates | Keep one copy |
| Total != sum of parts | Document only | May be rounding or cash tips |
