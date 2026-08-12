# Tableau Connection Guide

How to connect Tableau to the Gold layer data for our analytical question:
**"How does adverse weather affect taxi demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?"**

---

## Step-by-Step: Connect Tableau Public to Snowflake

Tableau Public (the free browser version) does not support direct Snowflake connections. To work around this, we export the data from Snowflake and upload it to Tableau Public.

### How to do it

1. **Export the data from Snowflake:**
   - Log into Snowflake at https://app.snowflake.com
   - Use your normal username and password
   - Make sure your role is set to **DE** (top-left dropdown, or run `USE ROLE DE;`)
   - Open a new SQL Worksheet
   - Paste and run this query:
     ```sql
     SELECT * FROM TECHCATALYST.AMO_GOLD.MART_WEATHER_DEMAND;
     ```
   - In the results pane, click the **Download** button (down arrow icon, top-right of the results)
   - Choose **Download as CSV**
   - Save the file somewhere you can find it (e.g., Downloads folder)

2. **Upload to Tableau Public:**
   - Go to https://public.tableau.com and sign in (create a free account if you don't have one)
   - Click **Create** (top nav) then **Web Authoring**
   - On the Connect screen, under "Files", click **Upload from computer**
   - Select the CSV file you just downloaded
   - Tableau will load the data and show you a preview

3. **Verify the data loaded:**
   - You should see 30,251 rows
   - Columns like PICKUP_BOROUGH, WEATHER_CATEGORY, TRIP_COUNT, TOTAL_REVENUE, etc.
   - If columns look correct, click **Update Now** at the bottom to load all data
   - Then click the **Sheet 1** tab at the bottom to start building visualizations

### After the data is loaded in Tableau Public:

- **Dimensions** (drag to Rows/Columns/Filters): PICKUP_BOROUGH, WEATHER_CATEGORY, IS_ADVERSE_WEATHER, PICKUP_YEAR, PICKUP_MONTH, PICKUP_HOUR, PAYMENT_TYPE, IS_RUSH_HOUR, IS_NIGHT, IS_WEEKEND
- **Measures** (drag to values): TRIP_COUNT, TOTAL_REVENUE, TOTAL_FARES, TOTAL_TIPS, AVG_FARE_TOTAL, AVG_TIP, AVG_DURATION_MINUTES, AVG_DISTANCE
- Some columns like PICKUP_YEAR and PICKUP_MONTH may import as measures (numbers). Right-click them and select "Convert to Dimension" so they behave as categories, not values to sum.

---

## Snowflake Connection Details (for reference)

These are the Snowflake details if you need to log in and run queries or export data:

| Setting | Value |
| :--- | :--- |
| Snowflake URL | https://app.snowflake.com |
| Account | FFOJZFH-WPA36811 |
| Role | DE |
| Warehouse | COMPUTE_WH |
| Database | TECHCATALYST |
| Schema | AMO_GOLD |
| Authentication | Your normal Snowflake username/password |

---

## Primary Data Source: MART_WEATHER_DEMAND

This is the main table to use. It has 30,251 rows (pre-aggregated from 38M trips), so Tableau will query it instantly with no performance issues. Only trips attributable to a real NYC borough are included (Unknown/N/A zone IDs excluded).

**Connect to:** `TECHCATALYST.AMO_GOLD.MART_WEATHER_DEMAND`

### Column Descriptions

| Column | Type | Description |
| :--- | :--- | :--- |
| `PICKUP_BOROUGH` | VARCHAR | NYC borough where the trip started (Manhattan, Brooklyn, Queens, Bronx, Staten Island, EWR). Only real boroughs are included. |
| `WEATHER_CATEGORY` | VARCHAR | Weather condition at time of pickup (Clear, Cloudy, Fog, Drizzle, Rain, Snow, Rain Showers, Snow Showers, Thunderstorm) |
| `IS_ADVERSE_WEATHER` | BOOLEAN | TRUE when Rain, Snow, or high wind. Use this for simple good-weather vs. bad-weather comparisons |
| `PICKUP_YEAR` | INT | 2025 or 2026. Use this for year-over-year comparisons |
| `PICKUP_MONTH` | INT | 1-5 (January through May) |
| `PICKUP_HOUR` | INT | 0-23. Hour of day when the trip started |
| `IS_RUSH_HOUR` | BOOLEAN | TRUE during 7-8am and 5-6pm |
| `IS_NIGHT` | BOOLEAN | TRUE between 10pm and 5am |
| `IS_WEEKEND` | BOOLEAN | TRUE on Saturday/Sunday |
| `PAYMENT_TYPE` | VARCHAR | Human-readable label: Credit Card, Cash, No Charge, Dispute, Unknown, Voided |
| `TRIP_COUNT` | INT | Number of trips in this group |
| `TOTAL_REVENUE` | FLOAT | Sum of total_amount for all trips in this group |
| `TOTAL_FARES` | FLOAT | Sum of base fare only |
| `TOTAL_TIPS` | FLOAT | Sum of tips (note: cash tips show as $0, only credit card tips are recorded) |
| `TOTAL_TOLLS` | FLOAT | Sum of toll charges |
| `TOTAL_CONGESTION_SURCHARGE` | FLOAT | Sum of congestion surcharges |
| `TOTAL_CBD_FEE` | FLOAT | Sum of CBD (Central Business District) congestion fees, new in 2025 |
| `AVG_FARE_TOTAL` | FLOAT | Average total fare per trip |
| `AVG_TIP` | FLOAT | Average tip per trip |
| `AVG_DURATION_MINUTES` | FLOAT | Average trip duration in minutes |
| `AVG_DISTANCE` | FLOAT | Average trip distance in miles |

### Important Data Notes

- **Cash tip trap:** Payment type "Cash" always shows $0 tips because cash tips are not recorded by the meter. Do not include cash trips in any tip analysis, or explicitly call this out.
- **Year-over-year:** Both years cover January through May only. Comparisons are fair month-to-month.
- **Borough coverage:** Manhattan dominates trip volume. Staten Island and EWR have very few trips.

---

## Supporting Tables (optional, for drilldowns)

| Table | Rows | Use |
| :--- | :--- | :--- |
| `DIM_ZONES` | 265 | Zone names and service zones, if you want to drill below borough level |
| `DIM_WEATHER` | 7,248 | Full hourly weather detail (temperature, precipitation, wind, etc.) |
| `FCT_TRIPS` | 38,053,445 | Individual trip records. Only use this if you need trip-level detail. It's large, so queries will be slower. |

---

## Normalizing the Data (Important)

Manhattan dominates raw trip counts (it has far more taxi activity than other boroughs). If you chart raw SUM(TRIP_COUNT) by borough, Manhattan will dwarf everything else and you won't see meaningful patterns in Brooklyn, Queens, etc.

**How to normalize: use percentage change instead of raw counts.**

The idea: for each borough, compare its own adverse-weather demand to its own clear-weather demand. That way you're comparing each borough against itself, not against Manhattan.

### Option 1: Calculated field in Tableau

Create a calculated field called something like "Pct Demand Drop":

```
(SUM(IF [Is Adverse Weather] = FALSE THEN [Trip Count] END)
 - SUM(IF [Is Adverse Weather] = TRUE THEN [Trip Count] END))
/ SUM(IF [Is Adverse Weather] = FALSE THEN [Trip Count] END)
```

This gives you the percentage of trips lost during adverse weather, per borough. A value of 0.12 means that borough loses 12% of its demand when weather is bad. This is flexible and lets you slice by month, hour, year, etc.

### Option 2: Use "Percent of Total" in Tableau

For quick normalization without calculated fields:
1. Drag TRIP_COUNT to the value shelf
2. Right-click the pill on the Marks card, select "Quick Table Calculation" then "Percent of Total"
3. Right-click again, select "Compute Using" then "Table (across)" or the specific dimension you want to normalize within

This shows each borough's share of trips rather than raw counts. Quickest option if you just want to level the playing field between boroughs.

---

## Suggested Visualizations

These directly answer the analytical question and make a strong dashboard:

### 1. Demand Impact: Adverse vs. Clear Weather by Borough (bar chart or grouped bar)
- X axis: PICKUP_BOROUGH
- Color: IS_ADVERSE_WEATHER (TRUE/FALSE)
- Value: Pct Demand Drop (normalized, see above) OR SUM(TRIP_COUNT) if you want raw scale
- Shows which boroughs lose the most demand during bad weather

### 2. Year-over-Year Shift (side-by-side or line chart)
- Filter or color by PICKUP_YEAR (2025 vs 2026)
- Group by PICKUP_BOROUGH + IS_ADVERSE_WEATHER
- Value: SUM(TRIP_COUNT) or SUM(TOTAL_REVENUE)
- Shows whether weather sensitivity changed between years

### 3. Revenue per Trip During Adverse Weather (highlight table or bar)
- Rows: PICKUP_BOROUGH
- Columns: WEATHER_CATEGORY
- Value: AVG_FARE_TOTAL
- Shows whether fares increase during bad weather (surge/longer trips)

### 4. Hourly Demand Pattern by Weather (line chart)
- X axis: PICKUP_HOUR
- Lines: WEATHER_CATEGORY or IS_ADVERSE_WEATHER
- Value: SUM(TRIP_COUNT)
- Shows how weather disrupts the normal daily demand curve

### 5. Monthly Trend with Weather Overlay (combo chart)
- X axis: PICKUP_MONTH
- Bars: SUM(TRIP_COUNT)
- Line or color: proportion of adverse weather hours that month
- Shows seasonal patterns

---

## Quick Test Query

Run this in Tableau or Snowflake to confirm your connection works:

```sql
SELECT
    PICKUP_BOROUGH,
    PICKUP_YEAR,
    IS_ADVERSE_WEATHER,
    SUM(TRIP_COUNT) AS trips,
    SUM(TOTAL_REVENUE) AS revenue
FROM TECHCATALYST.AMO_GOLD.MART_WEATHER_DEMAND
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
```

You should get 24 rows (6 boroughs x 2 years x 2 weather conditions).
