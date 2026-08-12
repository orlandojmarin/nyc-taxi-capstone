import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt

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

COLOR_2025 = "#002D72"
COLOR_2026 = "#d9d9d9"

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
    st.markdown("---")
    st.header("Visualizations")

    MONTH_LABELS = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May",
                    6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct",
                    11: "Nov", 12: "Dec"}
    boroughs = sorted(df["PICKUP_BOROUGH"].unique())

    # --- Chart 1: Percentage drop in demand during adverse weather ---
    st.subheader("1. Adverse Weather Reduces Taxi Demand Across All Boroughs")

    with st.expander("How to read this chart"):
        st.markdown("""
        This bar chart shows the **percentage drop in trips** during adverse weather compared to clear weather for each borough.

        - **Navy bar** = 2025 demand drop
        - **Gray bar** = 2026 demand drop
        - A larger bar means that borough loses more demand during bad weather
        - Hover over bars for exact percentages
        """)

    borough_drops = []
    for borough in boroughs:
        borough_df = df[df["PICKUP_BOROUGH"] == borough].copy()
        grouped = borough_df.groupby(
            ["PICKUP_YEAR", "IS_ADVERSE_WEATHER"], as_index=False
        )["TRIP_COUNT"].sum()

        clear_2025 = grouped[(grouped["PICKUP_YEAR"] == 2025) & (grouped["IS_ADVERSE_WEATHER"] == False)]["TRIP_COUNT"].sum()
        adverse_2025 = grouped[(grouped["PICKUP_YEAR"] == 2025) & (grouped["IS_ADVERSE_WEATHER"] == True)]["TRIP_COUNT"].sum()
        clear_2026 = grouped[(grouped["PICKUP_YEAR"] == 2026) & (grouped["IS_ADVERSE_WEATHER"] == False)]["TRIP_COUNT"].sum()
        adverse_2026 = grouped[(grouped["PICKUP_YEAR"] == 2026) & (grouped["IS_ADVERSE_WEATHER"] == True)]["TRIP_COUNT"].sum()

        drop_2025 = ((clear_2025 - adverse_2025) / clear_2025 * 100) if clear_2025 > 0 else 0
        drop_2026 = ((clear_2026 - adverse_2026) / clear_2026 * 100) if clear_2026 > 0 else 0
        borough_drops.append({"borough": borough, "drop_2025": drop_2025, "drop_2026": drop_2026})

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d["borough"] for d in borough_drops],
        y=[d["drop_2025"] for d in borough_drops],
        name="2025",
        marker_color=COLOR_2025,
        marker_line=dict(width=1, color="black"),
        hovertemplate="<b>%{x}</b><br>2025 Demand Drop: %{y:.1f}%<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=[d["borough"] for d in borough_drops],
        y=[d["drop_2026"] for d in borough_drops],
        name="2026",
        marker_color=COLOR_2026,
        marker_line=dict(width=1, color="black"),
        hovertemplate="<b>%{x}</b><br>2026 Demand Drop: %{y:.1f}%<extra></extra>"
    ))
    fig.update_layout(
        title=dict(text="Demand Drop During Adverse Weather by Borough", x=0.5, xanchor="center",
                   font=dict(size=20, color="black")),
        barmode="group",
        height=500,
        plot_bgcolor="white",
        paper_bgcolor="#f5f5f5",
        font=dict(color="black", size=14),
        margin=dict(l=50, r=50, t=70, b=50),
        xaxis=dict(title="Borough", title_font=dict(size=16), tickfont=dict(size=14)),
        yaxis=dict(title="% Fewer Trips (Adverse vs. Clear)", title_font=dict(size=16),
                   tickfont=dict(size=14), ticksuffix="%"),
        legend=dict(font=dict(size=14))
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Adverse weather reduces taxi demand across all boroughs, with drops ranging from roughly 15% to over 50%
        depending on the borough. The percentage drop is consistent between 2025 and 2026, suggesting that
        weather sensitivity has remained stable year over year. Boroughs with lower baseline demand
        (Staten Island, Bronx) tend to show larger proportional drops, while Manhattan's dense commuter
        base provides more resilience during bad weather.
        """)

    st.markdown("---")

    # --- Chart 2: Year-over-year monthly trip volume by borough ---
    st.subheader("2. Monthly Trip Volume Shows Consistent Year-over-Year Growth")

    with st.expander("How to read this chart"):
        st.markdown("""
        This line chart shows total monthly trips for each borough, with one line per year.

        - **Navy line** = 2025
        - **Gray line** = 2026
        - Hover over points for exact trip counts
        - Each tab shows one borough
        """)

    tabs2 = st.tabs(boroughs)
    for tab, borough in zip(tabs2, boroughs):
        with tab:
            borough_df = df[df["PICKUP_BOROUGH"] == borough].copy()
            monthly = borough_df.groupby(
                ["PICKUP_YEAR", "PICKUP_MONTH"], as_index=False
            )["TRIP_COUNT"].sum()

            m_2025 = monthly[monthly["PICKUP_YEAR"] == 2025].sort_values("PICKUP_MONTH")
            m_2026 = monthly[monthly["PICKUP_YEAR"] == 2026].sort_values("PICKUP_MONTH")

            months_2025 = [MONTH_LABELS[m] for m in m_2025["PICKUP_MONTH"]]
            months_2026 = [MONTH_LABELS[m] for m in m_2026["PICKUP_MONTH"]]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=months_2025, y=m_2025["TRIP_COUNT"].values,
                mode="lines+markers", name="2025",
                line=dict(color=COLOR_2025, width=3),
                marker=dict(size=8),
                hovertemplate="<b>2025</b><br>Month: %{x}<br>Trips: %{y:,.0f}<extra></extra>"
            ))
            fig.add_trace(go.Scatter(
                x=months_2026, y=m_2026["TRIP_COUNT"].values,
                mode="lines+markers", name="2026",
                line=dict(color="#808080", width=3),
                marker=dict(size=8, color="#808080"),
                hovertemplate="<b>2026</b><br>Month: %{x}<br>Trips: %{y:,.0f}<extra></extra>"
            ))
            fig.update_layout(
                title=dict(text=f"Monthly Trip Volume ({borough})", x=0.5, xanchor="center",
                           font=dict(size=20, color="black")),
                height=450,
                plot_bgcolor="white",
                paper_bgcolor="#f5f5f5",
                font=dict(color="black", size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Month", title_font=dict(size=16), tickfont=dict(size=14)),
                yaxis=dict(title="Total Trips", title_font=dict(size=16), tickfont=dict(size=14)),
                legend=dict(font=dict(size=14))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Most boroughs show a consistent upward trend from January through May in both years,
        reflecting seasonal demand patterns. 2026 generally tracks above 2025, suggesting
        year-over-year growth in taxi usage across the city.
        """)

    st.markdown("---")

    # --- Chart 3: Average fare by borough, tabbed by weather category ---
    st.subheader("3. Average Fares Remain Stable Across Weather Conditions")

    with st.expander("How to read this chart"):
        st.markdown("""
        This grouped bar chart shows the average fare per trip for each borough, comparing 2025 vs. 2026.

        - **Navy bars** = 2025
        - **Gray bars** = 2026
        - Each tab shows a different weather category
        - Value labels show exact dollar amounts above each bar
        """)

    weather_cats = sorted(df["WEATHER_CATEGORY"].unique())
    tabs3 = st.tabs(weather_cats)
    for tab, weather_cat in zip(tabs3, weather_cats):
        with tab:
            weather_df = df[df["WEATHER_CATEGORY"] == weather_cat].copy()
            fare_agg = weather_df.groupby(
                ["PICKUP_BOROUGH", "PICKUP_YEAR"], as_index=False
            ).agg(total_rev=("TOTAL_REVENUE", "sum"), total_trips=("TRIP_COUNT", "sum"))
            fare_agg["AVG_FARE"] = fare_agg["total_rev"] / fare_agg["total_trips"]

            b_2025 = fare_agg[fare_agg["PICKUP_YEAR"] == 2025].sort_values("PICKUP_BOROUGH")
            b_2026 = fare_agg[fare_agg["PICKUP_YEAR"] == 2026].sort_values("PICKUP_BOROUGH")

            borough_list = sorted(fare_agg["PICKUP_BOROUGH"].unique())
            vals_2025 = [b_2025[b_2025["PICKUP_BOROUGH"] == b]["AVG_FARE"].values[0]
                         if len(b_2025[b_2025["PICKUP_BOROUGH"] == b]) > 0 else 0
                         for b in borough_list]
            vals_2026 = [b_2026[b_2026["PICKUP_BOROUGH"] == b]["AVG_FARE"].values[0]
                         if len(b_2026[b_2026["PICKUP_BOROUGH"] == b]) > 0 else 0
                         for b in borough_list]

            fig, ax = plt.subplots(figsize=(10, 6))
            x = range(len(borough_list))
            width = 0.35
            x_2025 = [pos - width/2 for pos in x]
            x_2026 = [pos + width/2 for pos in x]

            bars1 = ax.bar(x_2025, vals_2025, width, label="2025", color=COLOR_2025, edgecolor="black")
            bars2 = ax.bar(x_2026, vals_2026, width, label="2026", color=COLOR_2026, edgecolor="black")

            for bar in list(bars1) + list(bars2):
                height = bar.get_height()
                ax.annotate(f'${height:.2f}',
                            xy=(bar.get_x() + bar.get_width()/2, height),
                            xytext=(0, 5), textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

            ax.set_ylabel("Avg Fare per Trip ($)")
            ax.set_title(f"Average Fare by Borough ({weather_cat})")
            ax.set_xticks(x)
            ax.set_xticklabels(borough_list)
            ax.legend()
            st.pyplot(fig)
            plt.close(fig)

    with st.expander("Show interpretation"):
        st.markdown("""
        Average fares are relatively consistent across weather categories within each borough,
        suggesting that weather does not significantly drive up per-trip fares. Year-over-year
        changes are modest, with slight increases in 2026 likely reflecting inflation or fare
        adjustments rather than weather-driven surge pricing.
        """)
