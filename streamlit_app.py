import sys
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))
from snowflake_connect import get_connection

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
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.MART_WEATHER_DEMAND ORDER BY PICKUP_BOROUGH, PICKUP_YEAR, PICKUP_MONTH",
        "description": "Pre-aggregated demand and revenue metrics by borough, weather, time, and payment type (34,719 rows).",
    },
    "fct_trips": {
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.FCT_TRIPS LIMIT 10000",
        "description": "Fact table of valid trips enriched with borough, zone, and weather data (38M+ rows, showing first 10,000).",
    },
    "dim_zones": {
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.DIM_ZONES ORDER BY LOCATION_ID",
        "description": "Zone dimension with borough and service zone (265 rows).",
    },
    "dim_weather": {
        "query": "SELECT * FROM TECHCATALYST.AMO_GOLD.DIM_WEATHER ORDER BY WEATHER_DATE, WEATHER_HOUR",
        "description": "Weather dimension with hourly observations and categories (7,248 rows).",
    },
}


@st.cache_data(ttl=600)
def load_table(query):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()


st.sidebar.header("Select Gold Table")
selected_table = st.sidebar.radio(
    "Table",
    list(GOLD_TABLES.keys()),
    format_func=lambda t: t.replace("_", " ").title(),
)

st.header(selected_table.replace("_", " ").title())
st.caption(GOLD_TABLES[selected_table]["description"])

with st.spinner(f"Loading {selected_table} from Snowflake..."):
    df = load_table(GOLD_TABLES[selected_table]["query"])

col1, col2 = st.columns(2)
with col1:
    st.metric("Rows", f"{len(df):,}")
with col2:
    st.metric("Columns", len(df.columns))

st.dataframe(df, use_container_width=True, height=600)

with st.expander("Column Details"):
    col_info = pd.DataFrame({
        "Column": df.columns,
        "Type": [str(df[c].dtype) for c in df.columns],
        "Non-Null Count": [df[c].notna().sum() for c in df.columns],
        "Sample Value": [df[c].iloc[0] if len(df) > 0 else None for c in df.columns],
    })
    st.dataframe(col_info, use_container_width=True)
