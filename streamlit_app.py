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

COLOR_2025 = "#d9d9d9"
COLOR_2026 = "#002D72"

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

    # --- Chart 1: Year-over-year monthly trip volume by borough ---
    st.subheader("1. Monthly Trip Volume Shows Consistent Year-over-Year Growth")

    with st.expander("How to read this chart"):
        st.markdown("""
        This line chart shows total monthly trips for each borough, with one line per year.

        - **Gray line** = 2025
        - **Navy line** = 2026
        - Hover over points for exact trip counts
        - Each tab shows one borough
        """)

    tabs1 = st.tabs(boroughs)
    for tab, borough in zip(tabs1, boroughs):
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
                line=dict(color=COLOR_2026, width=3),
                marker=dict(size=8, color=COLOR_2026),
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

    # --- Chart 2: Per-hour demand change during adverse weather ---
    st.subheader("2. Weather's Effect on Taxi Demand Shifted Between 2025 and 2026")

    with st.expander("How to read this chart"):
        st.markdown("""
        This bar chart shows the **percentage change in average hourly trips** during adverse weather
        compared to clear weather, normalized by the number of hours in each condition.

        - **Gray bars** = 2025
        - **Navy bars** = 2026
        - **Positive values** = demand *increases* during adverse weather (people switch to taxis)
        - **Negative values** = demand *decreases* during adverse weather
        - Use the **Day/Night tabs** to control for time-of-day bias (adverse weather at night would
          naturally show lower demand regardless of weather)
        - Hover over bars for exact percentages
        """)

    weather_dim = load_table("SELECT * FROM TECHCATALYST.AMO_GOLD.DIM_WEATHER")
    weather_dim["YEAR"] = weather_dim["WEATHER_DATE"].apply(
        lambda x: x.year if hasattr(x, "year") else int(str(x)[:4])
    )
    weather_dim["IS_NIGHT"] = weather_dim["WEATHER_HOUR"].apply(
        lambda h: h >= 20 or h < 6
    )

    def compute_weather_changes(mart_df, weather_ref, night_filter):
        if night_filter is not None:
            wf = weather_ref[weather_ref["IS_NIGHT"] == night_filter]
            mf = mart_df[mart_df["IS_NIGHT"] == night_filter]
        else:
            wf = weather_ref
            mf = mart_df
        results = []
        for borough in boroughs:
            bdf = mf[mf["PICKUP_BOROUGH"] == borough]
            for year in [2025, 2026]:
                clear_hrs = len(wf[(wf["YEAR"] == year) & (wf["IS_ADVERSE_WEATHER"] == False)])
                adverse_hrs = len(wf[(wf["YEAR"] == year) & (wf["IS_ADVERSE_WEATHER"] == True)])
                clear_trips = bdf[(bdf["PICKUP_YEAR"] == year) & (bdf["IS_ADVERSE_WEATHER"] == False)]["TRIP_COUNT"].sum()
                adverse_trips = bdf[(bdf["PICKUP_YEAR"] == year) & (bdf["IS_ADVERSE_WEATHER"] == True)]["TRIP_COUNT"].sum()
                avg_clear = clear_trips / clear_hrs if clear_hrs > 0 else 0
                avg_adverse = adverse_trips / adverse_hrs if adverse_hrs > 0 else 0
                pct_change = ((avg_adverse - avg_clear) / avg_clear * 100) if avg_clear > 0 else 0
                results.append({"borough": borough, "year": year, "pct_change": round(pct_change, 2)})
        return results

    def render_weather_chart(borough_changes, subtitle):
        changes_2025 = [d for d in borough_changes if d["year"] == 2025]
        changes_2026 = [d for d in borough_changes if d["year"] == 2026]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[d["borough"] for d in changes_2025],
            y=[d["pct_change"] for d in changes_2025],
            name="2025",
            marker_color=COLOR_2025,
            marker_line=dict(width=1, color="black"),
            hovertemplate="<b>%{x}</b><br>2025 Change: %{y:+.2f}%<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=[d["borough"] for d in changes_2026],
            y=[d["pct_change"] for d in changes_2026],
            name="2026",
            marker_color=COLOR_2026,
            marker_line=dict(width=1, color="black"),
            hovertemplate="<b>%{x}</b><br>2026 Change: %{y:+.2f}%<extra></extra>"
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(
            title=dict(text=f"Hourly Demand Change During Adverse Weather ({subtitle})",
                       x=0.5, xanchor="center", font=dict(size=20, color="black")),
            barmode="group",
            height=500,
            plot_bgcolor="white",
            paper_bgcolor="#f5f5f5",
            font=dict(color="black", size=14),
            margin=dict(l=50, r=50, t=70, b=50),
            xaxis=dict(title="Borough", title_font=dict(size=16), tickfont=dict(size=14)),
            yaxis=dict(title="% Change in Trips/Hour (Adverse vs. Clear)",
                       title_font=dict(size=16), tickfont=dict(size=14), ticksuffix="%",
                       zeroline=True),
            legend=dict(font=dict(size=14))
        )
        st.plotly_chart(fig, use_container_width=True)

    tab_day, tab_night = st.tabs(["Day (6 AM - 8 PM)", "Night (8 PM - 6 AM)"])
    with tab_day:
        day_changes = compute_weather_changes(df, weather_dim, night_filter=False)
        render_weather_chart(day_changes, "Daytime Hours")
    with tab_night:
        night_changes = compute_weather_changes(df, weather_dim, night_filter=True)
        render_weather_chart(night_changes, "Nighttime Hours")

    with st.expander("Show interpretation"):
        st.markdown("""
        Splitting by time of day controls for the possibility that adverse weather clusters at night
        (when demand is naturally lower). During **daytime hours**, the 2025 pattern holds: adverse
        weather *increased* taxi demand in Manhattan and Brooklyn as riders switched from walking or
        transit. In 2026, daytime adverse weather drove demand *down*, suggesting a behavioral shift.
        The **nighttime tab** shows whether this pattern persists when baseline demand is already low,
        helping confirm the finding is not simply a time-of-day artifact.
        """)

    st.markdown("---")

    # --- Chart 3: Average fare by borough, tabbed by weather category ---
    st.subheader("3. Average Fares Remain Stable Across Weather Conditions")

    with st.expander("How to read this chart"):
        st.markdown("""
        This grouped bar chart shows the average fare per trip for each borough, comparing 2025 vs. 2026.

        - **Gray bars** = 2025
        - **Navy bars** = 2026
        - Each tab shows a different weather category
        - Hover over bars for exact dollar amounts
        """)

    weather_cats = sorted(df["WEATHER_CATEGORY"].unique())
    tabs3 = st.tabs(weather_cats)
    for tab, weather_cat in zip(tabs3, weather_cats):
        with tab:
            wcat_df = df[df["WEATHER_CATEGORY"] == weather_cat].copy()
            fare_agg = wcat_df.groupby(
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

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=borough_list,
                y=vals_2025,
                name="2025",
                marker_color=COLOR_2025,
                marker_line=dict(width=1, color="black"),
                text=[f"${v:.2f}" for v in vals_2025],
                textposition="outside",
                textfont=dict(size=11),
                hovertemplate="<b>%{x}</b><br>2025 Avg Fare: $%{y:.2f}<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                x=borough_list,
                y=vals_2026,
                name="2026",
                marker_color=COLOR_2026,
                marker_line=dict(width=1, color="black"),
                text=[f"${v:.2f}" for v in vals_2026],
                textposition="outside",
                textfont=dict(size=11),
                hovertemplate="<b>%{x}</b><br>2026 Avg Fare: $%{y:.2f}<extra></extra>"
            ))
            fig.update_layout(
                title=dict(text=f"Average Fare by Borough ({weather_cat})",
                           x=0.5, xanchor="center", font=dict(size=20, color="black")),
                barmode="group",
                height=500,
                plot_bgcolor="white",
                paper_bgcolor="#f5f5f5",
                font=dict(color="black", size=14),
                margin=dict(l=50, r=50, t=70, b=80),
                xaxis=dict(title="Borough", title_font=dict(size=16), tickfont=dict(size=14)),
                yaxis=dict(title="Avg Fare per Trip ($)", title_font=dict(size=16),
                           tickfont=dict(size=14), tickprefix="$"),
                legend=dict(font=dict(size=14))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Average fares are relatively consistent across weather categories within each borough,
        suggesting that weather does not significantly drive up per-trip fares. Year-over-year
        changes are modest, with slight increases in 2026 likely reflecting inflation or fare
        adjustments rather than weather-driven surge pricing.
        """)
