import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import altair as alt

alt.data_transformers.disable_max_rows()

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))
from snowflake_connect import query_to_df

st.set_page_config(
    page_title="NYC Taxi Capstone - Gold Layer Explorer",
    page_icon="🚕",
    layout="wide",
)

st.title("NYC Taxi Capstone: Gold Layer Data Explorer")
st.markdown(
    "**Team AMO** | Analytical Question: *How does adverse weather affect taxi "
    "demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?*"
)

GOLD_TABLES = {
    "mart_weather_demand": {
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.MART_WEATHER_DEMAND",
        "description": "Pre-aggregated demand and revenue metrics by borough, weather, time, and payment type (~30K rows).",
    },
    "fct_trips (sample)": {
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.FCT_TRIPS LIMIT 1000",
        "description": "Sample of 1,000 rows from the enriched fact table (38M+ total). Shows individual trips with borough, weather, and revenue details.",
    },
    "dim_zones": {
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.DIM_ZONES",
        "description": "Zone dimension with borough and service zone (265 rows).",
    },
    "dim_weather": {
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.DIM_WEATHER",
        "description": "Weather dimension with hourly observations and categories (~7K rows).",
    },
}


@st.cache_data(ttl=600)
def load_table(query):
    return query_to_df(query)


st.sidebar.header("Select Gold Table")
selected_table = st.sidebar.radio(
    "Table",
    list(GOLD_TABLES.keys()),
    format_func=lambda t: t.replace("_", " ").title(),
)

st.header(selected_table.replace("_", " ").title())
st.caption(GOLD_TABLES[selected_table]["description"])

df = load_table(GOLD_TABLES[selected_table]["query"])

col1, col2 = st.columns(2)
with col1:
    st.metric("Rows", f"{len(df):,}")
with col2:
    st.metric("Columns", len(df.columns))

st.dataframe(df, width="stretch", height=600)

with st.expander("Column Details"):
    col_info = pd.DataFrame({
        "Column": df.columns,
        "Type": [str(df[c].dtype) for c in df.columns],
        "Non-Null Count": [df[c].notna().sum() for c in df.columns],
        "Sample Value": [str(df[c].iloc[0]) if len(df) > 0 else None for c in df.columns],
    })
    st.dataframe(col_info, width="stretch")

if selected_table == "mart_weather_demand":
    st.divider()
    st.header("Visualizations")

    MONTH_LABELS = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May",
                    6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct",
                    11: "Nov", 12: "Dec"}
    MONTH_ORDER = [MONTH_LABELS[m] for m in sorted(MONTH_LABELS.keys())]
    boroughs = sorted(df["PICKUP_BOROUGH"].unique())

    YEAR_COLOR = alt.Scale(domain=["2025", "2026"], range=["#1a2456", "#a0a0a0"])

    # --- Chart 1: Trip demand per borough tab, grouped by year and weather ---
    st.subheader("1. Trip Demand by Year and Weather Condition")
    tabs1 = st.tabs(boroughs)
    for tab, borough in zip(tabs1, boroughs):
        with tab:
            borough_df = df[df["PICKUP_BOROUGH"] == borough].copy()
            grouped = borough_df.groupby(
                ["PICKUP_YEAR", "IS_ADVERSE_WEATHER"], as_index=False
            )["TRIP_COUNT"].sum()
            grouped["Year"] = grouped["PICKUP_YEAR"].astype(str)
            grouped["Weather"] = grouped["IS_ADVERSE_WEATHER"].map(
                {True: "Adverse", False: "Clear"}
            )
            chart1 = (
                alt.Chart(grouped)
                .mark_bar()
                .encode(
                    x=alt.X("Weather:N", title="Weather"),
                    y=alt.Y("TRIP_COUNT:Q", title="Total Trips"),
                    color=alt.Color("Year:N", scale=YEAR_COLOR),
                    xOffset="Year:N",
                )
                .properties(height=400, title=borough)
            )
            st.altair_chart(chart1, width="stretch")

    # --- Chart 2: Year-over-year monthly trip volume by borough ---
    st.subheader("2. Year-over-Year Monthly Trip Volume (2025 vs. 2026)")
    tabs2 = st.tabs(boroughs)
    for tab, borough in zip(tabs2, boroughs):
        with tab:
            borough_df = df[df["PICKUP_BOROUGH"] == borough].copy()
            monthly = borough_df.groupby(
                ["PICKUP_YEAR", "PICKUP_MONTH"], as_index=False
            )["TRIP_COUNT"].sum()
            monthly["Year"] = monthly["PICKUP_YEAR"].astype(str)
            monthly["Month"] = monthly["PICKUP_MONTH"].map(MONTH_LABELS)
            chart2 = (
                alt.Chart(monthly)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X("Month:N", title="Month",
                            sort=[m for m in MONTH_ORDER if m in monthly["Month"].values]),
                    y=alt.Y("TRIP_COUNT:Q", title="Total Trips",
                            scale=alt.Scale(zero=False)),
                    color=alt.Color("Year:N", title="Year", scale=YEAR_COLOR),
                )
                .properties(height=400, title=borough)
            )
            st.altair_chart(chart2, width="stretch")

    # --- Chart 3: Average fare by borough, tabbed by weather category ---
    st.subheader("3. Average Fare by Borough and Year")
    weather_cats = sorted(df["WEATHER_CATEGORY"].unique())
    tabs3 = st.tabs(weather_cats)
    for tab, weather_cat in zip(tabs3, weather_cats):
        with tab:
            weather_df = df[df["WEATHER_CATEGORY"] == weather_cat].copy()
            fare_agg = weather_df.groupby(
                ["PICKUP_BOROUGH", "PICKUP_YEAR"], as_index=False
            ).agg(total_rev=("TOTAL_REVENUE", "sum"), total_trips=("TRIP_COUNT", "sum"))
            fare_agg["AVG_FARE"] = fare_agg["total_rev"] / fare_agg["total_trips"]
            fare_agg["Year"] = fare_agg["PICKUP_YEAR"].astype(str)
            chart3 = (
                alt.Chart(fare_agg)
                .mark_bar()
                .encode(
                    x=alt.X("PICKUP_BOROUGH:N", title="Borough"),
                    y=alt.Y("AVG_FARE:Q", title="Avg Fare per Trip ($)"),
                    color=alt.Color("Year:N", scale=YEAR_COLOR),
                    xOffset="Year:N",
                )
                .properties(height=400, title=weather_cat)
            )
            st.altair_chart(chart3, width="stretch")
