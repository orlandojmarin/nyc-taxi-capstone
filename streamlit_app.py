from pathlib import Path

import streamlit as st
import pandas as pd

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

DATA_DIR = Path(__file__).parent / "data"

GOLD_TABLES = {
    "mart_weather_demand": {
        "file": "mart_weather_demand.csv",
        "description": "Pre-aggregated demand and revenue metrics by borough, weather, time, and payment type (30,251 rows).",
    },
    "dim_zones": {
        "file": "dim_zones.csv",
        "description": "Zone dimension with borough and service zone (265 rows).",
    },
    "dim_weather": {
        "file": "dim_weather.csv",
        "description": "Weather dimension with hourly observations and categories (7,248 rows).",
    },
}


@st.cache_data
def load_table(filename):
    return pd.read_csv(DATA_DIR / filename)


st.sidebar.header("Select Gold Table")
selected_table = st.sidebar.radio(
    "Table",
    list(GOLD_TABLES.keys()),
    format_func=lambda t: t.replace("_", " ").title(),
)

st.header(selected_table.replace("_", " ").title())
st.caption(GOLD_TABLES[selected_table]["description"])

df = load_table(GOLD_TABLES[selected_table]["file"])

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
