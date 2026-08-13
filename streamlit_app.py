import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
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
    "**Team AMO** (Ariana Lopez, Maryam Choudhury, Orlando Marin) | "
    "Analytical Question: *How does adverse weather affect taxi "
    "demand across NYC boroughs, and how did those patterns shift between 2025 and 2026?*"
)

BG_COLOR = "white"
PAPER_COLOR = "#f5f5f5"
TEXT_COLOR = "black"
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
                           font=dict(size=20, color=TEXT_COLOR)),
                height=450,
                plot_bgcolor=BG_COLOR,
                paper_bgcolor=PAPER_COLOR,
                font=dict(color=TEXT_COLOR, size=14),
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

    # --- Chart 2: Weekday vs weekend demand by hour ---
    st.subheader("2. Weekday Demand Spikes at Rush Hour While Weekends Stay Flat")

    with st.expander("How to read this chart"):
        st.markdown("""
        This line chart shows average trips per hour across the 24-hour day, comparing weekdays
        to weekends.

        - **Gray line** = Weekdays (Mon-Fri)
        - **Navy line** = Weekends (Sat-Sun)
        - Values are normalized: total trips at each hour divided by the number of weekday or
          weekend days, so the lines are directly comparable despite more weekdays existing
        - Each tab shows one borough
        - Hover over points for exact values
        """)

    weather_dim_for_days = load_table("SELECT * FROM TECHCATALYST.AMO_GOLD.DIM_WEATHER")
    weather_dim_for_days["_IS_WEEKEND"] = weather_dim_for_days["WEATHER_DATE"].apply(
        lambda d: d.weekday() >= 5 if hasattr(d, "weekday") else False
    )
    weekday_days = weather_dim_for_days[weather_dim_for_days["_IS_WEEKEND"] == False]["WEATHER_DATE"].nunique()
    weekend_days = weather_dim_for_days[weather_dim_for_days["_IS_WEEKEND"] == True]["WEATHER_DATE"].nunique()

    tabs_wd = st.tabs(boroughs)
    for tab, borough in zip(tabs_wd, boroughs):
        with tab:
            bdf = df[df["PICKUP_BOROUGH"] == borough]
            weekday_hourly = bdf[bdf["IS_WEEKEND"] == False].groupby(
                "PICKUP_HOUR", as_index=False
            )["TRIP_COUNT"].sum()
            weekend_hourly = bdf[bdf["IS_WEEKEND"] == True].groupby(
                "PICKUP_HOUR", as_index=False
            )["TRIP_COUNT"].sum()

            weekday_hourly = weekday_hourly.sort_values("PICKUP_HOUR")
            weekend_hourly = weekend_hourly.sort_values("PICKUP_HOUR")
            weekday_hourly["AVG_TRIPS"] = weekday_hourly["TRIP_COUNT"] / weekday_days
            weekend_hourly["AVG_TRIPS"] = weekend_hourly["TRIP_COUNT"] / weekend_days

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weekday_hourly["PICKUP_HOUR"].values,
                y=weekday_hourly["AVG_TRIPS"].values,
                mode="lines+markers", name="Weekday",
                line=dict(color=COLOR_2025, width=3),
                marker=dict(size=6),
                hovertemplate="<b>Weekday</b><br>Hour: %{x}:00<br>Avg Trips: %{y:,.0f}<extra></extra>"
            ))
            fig.add_trace(go.Scatter(
                x=weekend_hourly["PICKUP_HOUR"].values,
                y=weekend_hourly["AVG_TRIPS"].values,
                mode="lines+markers", name="Weekend",
                line=dict(color=COLOR_2026, width=3),
                marker=dict(size=6, color=COLOR_2026),
                hovertemplate="<b>Weekend</b><br>Hour: %{x}:00<br>Avg Trips: %{y:,.0f}<extra></extra>"
            ))
            fig.update_layout(
                title=dict(text=f"Average Hourly Demand: Weekday vs. Weekend ({borough})",
                           x=0.5, xanchor="center", font=dict(size=20, color=TEXT_COLOR)),
                height=450,
                plot_bgcolor=BG_COLOR,
                paper_bgcolor=PAPER_COLOR,
                font=dict(color=TEXT_COLOR, size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Hour of Day", title_font=dict(size=16), tickfont=dict(size=14),
                           tickmode="linear", dtick=2),
                yaxis=dict(title="Avg Trips per Hour", title_font=dict(size=16),
                           tickfont=dict(size=14)),
                legend=dict(font=dict(size=14))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Weekday demand shows sharp peaks during morning and evening rush hours (8 AM and 5-7 PM),
        while weekend demand is more evenly distributed throughout the day, rising gradually from
        late morning through the evening. This pattern matters for the weather analysis: if adverse
        weather hits during rush hour on a weekday, it disrupts a high-demand period. The same
        weather on a weekend would affect a flatter demand curve, potentially showing a smaller
        absolute impact.
        """)

    st.markdown("---")

    # --- Chart 3: Average trip cost by borough, tabbed by weather category ---
    st.subheader("3. Average Trip Cost Remains Stable Across Weather Conditions")

    with st.expander("How to read this chart"):
        st.markdown("""
        This grouped bar chart shows the average trip cost (excluding tips) for each borough,
        comparing 2025 vs. 2026.

        - **Gray bars** = 2025
        - **Navy bars** = 2026
        - Each tab shows a different weather category
        - Hover over bars for exact dollar amounts
        - Tips are excluded for consistency (cash tips are not recorded in TLC data)
        """)

    weather_cats = sorted(df["WEATHER_CATEGORY"].unique())
    tabs3 = st.tabs(weather_cats)
    for tab, weather_cat in zip(tabs3, weather_cats):
        with tab:
            wcat_df = df[df["WEATHER_CATEGORY"] == weather_cat].copy()
            fare_agg = wcat_df.groupby(
                ["PICKUP_BOROUGH", "PICKUP_YEAR"], as_index=False
            ).agg(
                total_rev=("TOTAL_REVENUE", "sum"),
                total_tips=("TOTAL_TIPS", "sum"),
                total_trips=("TRIP_COUNT", "sum")
            )
            fare_agg["AVG_FARE"] = (fare_agg["total_rev"] - fare_agg["total_tips"]) / fare_agg["total_trips"]

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
                hovertemplate="<b>%{x}</b><br>2025 Avg Cost: $%{y:.2f}<extra></extra>"
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
                hovertemplate="<b>%{x}</b><br>2026 Avg Cost: $%{y:.2f}<extra></extra>"
            ))
            fig.update_layout(
                title=dict(text=f"Average Trip Cost by Borough ({weather_cat})",
                           x=0.5, xanchor="center", font=dict(size=20, color=TEXT_COLOR)),
                barmode="group",
                height=500,
                plot_bgcolor=BG_COLOR,
                paper_bgcolor=PAPER_COLOR,
                font=dict(color=TEXT_COLOR, size=14),
                margin=dict(l=50, r=50, t=70, b=80),
                xaxis=dict(title="Borough", title_font=dict(size=16), tickfont=dict(size=14)),
                yaxis=dict(title="Avg Cost per Trip ($)", title_font=dict(size=16),
                           tickfont=dict(size=14), tickprefix="$"),
                legend=dict(font=dict(size=14))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Average trip costs (excluding tips) are relatively consistent across weather categories
        within each borough, suggesting that weather does not significantly drive up per-trip costs.
        Year-over-year changes are modest, with slight increases in 2026 likely reflecting inflation
        or fare adjustments rather than weather-driven surge pricing. Tips are excluded because cash
        tips are not recorded in TLC data, which would skew comparisons across payment types.

        Notably, trips during adverse weather are shorter in both distance and duration (e.g.,
        Queens snow trips average 26.8 min vs. 34.3 min during clear weather in 2026), yet revenue
        per trip remains stable because base fares, surcharges, and congestion fees keep the per-trip
        total consistent regardless of distance. This confirms that weather's primary impact on
        revenue is through *volume* (fewer trips), not through changes in what each trip earns.
        """)

    st.markdown("---")

    # --- Chart 4: Per-hour demand change during adverse weather ---
    st.subheader("4. Weather's Effect on Taxi Demand Shifted Between 2025 and 2026")

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
                       x=0.5, xanchor="center", font=dict(size=20, color=TEXT_COLOR)),
            barmode="group",
            height=500,
            plot_bgcolor=BG_COLOR,
            paper_bgcolor=PAPER_COLOR,
            font=dict(color=TEXT_COLOR, size=14),
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

    # --- Chart 5: Weather type breakdown (rain vs snow) ---
    st.subheader("5. Snow Drives the Demand Drop While Rain Still Boosts Ridership")

    with st.expander("How to read this chart"):
        st.markdown("""
        This chart breaks "adverse weather" into its components (Rain vs. Snow) and shows
        the percentage change in demand compared to clear weather for each type.

        - **Gray bars** = 2025
        - **Navy bars** = 2026
        - **Positive values** = more trips per hour than during clear weather
        - **Negative values** = fewer trips per hour than during clear weather
        - Each tab shows one borough
        - This reveals *which type* of bad weather is responsible for the shift seen in Chart 4
        """)

    def compute_weather_type_changes(mart_df, weather_ref):
        results = []
        for borough in boroughs:
            bdf = mart_df[mart_df["PICKUP_BOROUGH"] == borough]
            for year in [2025, 2026]:
                clear_hrs = len(weather_ref[
                    (weather_ref["YEAR"] == year) & (weather_ref["WEATHER_CATEGORY"] == "Clear")
                ])
                clear_trips = bdf[
                    (bdf["PICKUP_YEAR"] == year) & (bdf["WEATHER_CATEGORY"] == "Clear")
                ]["TRIP_COUNT"].sum()
                avg_clear = clear_trips / clear_hrs if clear_hrs > 0 else 0

                for wtype in ["Rain", "Snow"]:
                    type_hrs = len(weather_ref[
                        (weather_ref["YEAR"] == year) & (weather_ref["WEATHER_CATEGORY"] == wtype)
                    ])
                    type_trips = bdf[
                        (bdf["PICKUP_YEAR"] == year) & (bdf["WEATHER_CATEGORY"] == wtype)
                    ]["TRIP_COUNT"].sum()
                    avg_type = type_trips / type_hrs if type_hrs > 0 else 0
                    pct_change = ((avg_type - avg_clear) / avg_clear * 100) if avg_clear > 0 else 0
                    results.append({
                        "borough": borough, "year": year,
                        "weather_type": wtype, "pct_change": round(pct_change, 2)
                    })
        return results

    weather_type_changes = compute_weather_type_changes(df, weather_dim)

    tabs5 = st.tabs(boroughs)
    for tab, borough in zip(tabs5, boroughs):
        with tab:
            borough_data = [d for d in weather_type_changes if d["borough"] == borough]

            rain_2025 = next((d["pct_change"] for d in borough_data
                              if d["weather_type"] == "Rain" and d["year"] == 2025), 0)
            rain_2026 = next((d["pct_change"] for d in borough_data
                              if d["weather_type"] == "Rain" and d["year"] == 2026), 0)
            snow_2025 = next((d["pct_change"] for d in borough_data
                              if d["weather_type"] == "Snow" and d["year"] == 2025), 0)
            snow_2026 = next((d["pct_change"] for d in borough_data
                              if d["weather_type"] == "Snow" and d["year"] == 2026), 0)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Rain", "Snow"], y=[rain_2025, snow_2025],
                name="2025", marker_color=COLOR_2025,
                marker_line=dict(width=1, color="black"),
                text=[f"{rain_2025:+.1f}%", f"{snow_2025:+.1f}%"],
                textposition="outside", textfont=dict(size=12),
                hovertemplate="<b>%{x}</b><br>2025: %{y:+.2f}%<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                x=["Rain", "Snow"], y=[rain_2026, snow_2026],
                name="2026", marker_color=COLOR_2026,
                marker_line=dict(width=1, color="black"),
                text=[f"{rain_2026:+.1f}%", f"{snow_2026:+.1f}%"],
                textposition="outside", textfont=dict(size=12),
                hovertemplate="<b>%{x}</b><br>2026: %{y:+.2f}%<extra></extra>"
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.update_layout(
                title=dict(text=f"Demand Change by Weather Type ({borough})",
                           x=0.5, xanchor="center", font=dict(size=20, color=TEXT_COLOR)),
                barmode="group", height=450,
                plot_bgcolor=BG_COLOR, paper_bgcolor=PAPER_COLOR,
                font=dict(color=TEXT_COLOR, size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Weather Type", title_font=dict(size=16), tickfont=dict(size=14)),
                yaxis=dict(title="% Change vs. Clear Weather", title_font=dict(size=16),
                           tickfont=dict(size=14), ticksuffix="%", zeroline=True),
                legend=dict(font=dict(size=14))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Breaking adverse weather into Rain and Snow reveals a critical distinction: **rain consistently
        boosts taxi demand** (people avoid walking in the rain and switch to cabs), while **snow
        suppresses it** (people stay home, roads become impassable, drivers pull off the road).

        The 2025-to-2026 shift seen in Chart 4 is largely driven by snow's growing negative impact.
        This is not a behavioral mystery: **2026 had a dramatically worse snow season.** Total snowfall
        more than doubled (11.6 in vs. 25.2 in), the longest continuous storm grew from 11 to 27 hours,
        and average snow accumulation tripled (0.14 in vs. 0.41 in on the ground). Meanwhile, rain was
        actually *lighter* in 2026 (fewer hours, lower intensity), which explains why rain's demand
        boost weakened but did not flip negative in most boroughs.

        This matters for recommendations: rain remains a revenue *opportunity* (more riders switching
        to cabs), while snow, especially prolonged heavy snow, is a *risk* that scales with storm
        severity and requires proactive operational response.
        """)

    st.markdown("---")

    # --- Chart 6: Revenue per adverse-weather hour, rush vs off-peak ---
    st.subheader("6. Storm-Hour Revenue Losses Concentrate During Rush Hour")

    with st.expander("How to read this chart"):
        st.markdown("""
        This chart shows the **dollar difference in revenue per hour** during adverse weather
        compared to clear weather, split by rush hour vs. off-peak.

        - **Gray bars** = 2025
        - **Navy bars** = 2026
        - **Negative values** = revenue lost per storm-hour compared to a clear-weather hour
        - **Positive values** = revenue gained per storm-hour (riders switching to taxis)
        - **Rush Hour** = 7-10 AM and 4-7 PM weekdays
        - **Off-Peak** = all other hours
        - Each tab shows one borough
        - This quantifies the finding from Charts 4 and 5 in dollars, and shows when the
          impact is most severe
        """)

    def compute_revenue_per_hour(mart_df, weather_ref, rush_filter):
        results = []
        for borough in boroughs:
            bdf = mart_df[(mart_df["PICKUP_BOROUGH"] == borough) &
                          (mart_df["IS_RUSH_HOUR"] == rush_filter)]
            wf = weather_ref.copy()
            if rush_filter:
                wf = wf[wf["WEATHER_HOUR"].isin([7, 8, 9, 16, 17, 18])]
            else:
                wf = wf[~wf["WEATHER_HOUR"].isin([7, 8, 9, 16, 17, 18])]

            for year in [2025, 2026]:
                clear_hrs = len(wf[(wf["YEAR"] == year) & (wf["IS_ADVERSE_WEATHER"] == False)])
                adverse_hrs = len(wf[(wf["YEAR"] == year) & (wf["IS_ADVERSE_WEATHER"] == True)])
                clear_rev = bdf[(bdf["PICKUP_YEAR"] == year) &
                                (bdf["IS_ADVERSE_WEATHER"] == False)]["TOTAL_REVENUE"].sum()
                adverse_rev = bdf[(bdf["PICKUP_YEAR"] == year) &
                                  (bdf["IS_ADVERSE_WEATHER"] == True)]["TOTAL_REVENUE"].sum()
                rev_per_clear_hr = clear_rev / clear_hrs if clear_hrs > 0 else 0
                rev_per_adverse_hr = adverse_rev / adverse_hrs if adverse_hrs > 0 else 0
                delta = rev_per_adverse_hr - rev_per_clear_hr
                results.append({"borough": borough, "year": year, "delta": round(delta, 2)})
        return results

    tabs6 = st.tabs(boroughs)
    for tab, borough in zip(tabs6, boroughs):
        with tab:
            rush_data = compute_revenue_per_hour(df, weather_dim, rush_filter=True)
            offpeak_data = compute_revenue_per_hour(df, weather_dim, rush_filter=False)

            rush_borough = [d for d in rush_data if d["borough"] == borough]
            offpeak_borough = [d for d in offpeak_data if d["borough"] == borough]

            categories = ["Rush Hour", "Off-Peak"]
            vals_2025 = [
                next((d["delta"] for d in rush_borough if d["year"] == 2025), 0),
                next((d["delta"] for d in offpeak_borough if d["year"] == 2025), 0)
            ]
            vals_2026 = [
                next((d["delta"] for d in rush_borough if d["year"] == 2026), 0),
                next((d["delta"] for d in offpeak_borough if d["year"] == 2026), 0)
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=categories, y=vals_2025, name="2025",
                marker_color=COLOR_2025,
                marker_line=dict(width=1, color="black"),
                text=[f"${v:+,.0f}" for v in vals_2025],
                textposition="outside", textfont=dict(size=12),
                hovertemplate="<b>%{x}</b><br>2025: $%{y:+,.0f}/hr<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                x=categories, y=vals_2026, name="2026",
                marker_color=COLOR_2026,
                marker_line=dict(width=1, color="black"),
                text=[f"${v:+,.0f}" for v in vals_2026],
                textposition="outside", textfont=dict(size=12),
                hovertemplate="<b>%{x}</b><br>2026: $%{y:+,.0f}/hr<extra></extra>"
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray")
            fig.update_layout(
                title=dict(text=f"Revenue Impact per Storm-Hour ({borough})",
                           x=0.5, xanchor="center", font=dict(size=20, color=TEXT_COLOR)),
                barmode="group", height=450,
                plot_bgcolor=BG_COLOR, paper_bgcolor=PAPER_COLOR,
                font=dict(color=TEXT_COLOR, size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Time Period", title_font=dict(size=16), tickfont=dict(size=14)),
                yaxis=dict(title="Revenue Difference per Hour ($)", title_font=dict(size=16),
                           tickfont=dict(size=14), tickprefix="$", zeroline=True),
                legend=dict(font=dict(size=14))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        This chart translates the demand shift into dollars and reveals **when** the loss is most
        acute. In 2025, adverse weather during rush hour often *increased* revenue (more riders
        hailing cabs). In 2026, that pattern reversed, and the losses concentrate heavily during
        rush hour, where per-hour revenue is highest.

        **Business implication:** A single storm-hour during rush hour now costs more in lost revenue
        than several off-peak storm-hours combined. This supports a targeted response: pre-position
        vehicles before forecasted storms, prioritize rush-hour coverage, and consider dynamic
        incentives for drivers to stay on the road during adverse conditions.
        """)
