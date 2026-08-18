import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).parent / "data"

CSV_FILES = {
    "mart_weather_demand": "mart_weather_demand.csv",
    "fct_trips (sample)": "fct_trips_sample.csv",
    "dim_zones": "dim_zones.csv",
    "dim_weather": "dim_weather.csv",
}


def _load_from_csv(table_key):
    csv_path = DATA_DIR / CSV_FILES[table_key]
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return None


def _load_from_snowflake(query):
    try:
        sys.path.insert(0, str(Path(__file__).parent / "pipeline"))
        from snowflake_connect import query_to_df
        return query_to_df(query)
    except Exception:
        return None

st.set_page_config(
    page_title="NYC Taxi Capstone - Team AMO",
    page_icon="🚕",
    layout="wide",
)

st.title("NYC Taxi Capstone: Data Explorer")
st.markdown("**Created by Team AMO:** Ariana Lopez, Maryam Choudhury, and Orlando Marin")
st.markdown("""Analytical Question: *How does adverse weather (rain and snow) affect taxi demand 
            across NYC boroughs, and how did those patterns shift between 2025 and 2026?*""")

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
def load_table(table_key):
    df = _load_from_csv(table_key)
    if df is not None:
        return df
    df = _load_from_snowflake(GOLD_TABLES[table_key]["query"])
    if df is not None:
        return df
    st.error(f"Could not load {table_key} from CSV or Snowflake.")
    st.stop()


st.sidebar.header("Navigation")
page = st.sidebar.radio("View", ["Visualizations", "Data Explorer"])

if page == "Data Explorer":
    st.header("Gold Layer Data Explorer")
    selected_table = st.selectbox(
        "Select a table",
        list(GOLD_TABLES.keys()),
        format_func=lambda t: t.replace("_", " ").title(),
    )

    st.caption(GOLD_TABLES[selected_table]["description"])
    explorer_df = load_table(selected_table)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Rows", f"{len(explorer_df):,}")
    with col2:
        st.metric("Columns", len(explorer_df.columns))

    st.dataframe(explorer_df, width="stretch", height=600)

    with st.expander("Column Details"):
        col_info = pd.DataFrame({
            "Column": explorer_df.columns,
            "Type": [str(explorer_df[c].dtype) for c in explorer_df.columns],
            "Non-Null Count": [explorer_df[c].notna().sum() for c in explorer_df.columns],
            "Sample Value": [str(explorer_df[c].iloc[0]) if len(explorer_df) > 0 else None for c in explorer_df.columns],
        })
        st.dataframe(col_info, width="stretch")

else:
    df = load_table("mart_weather_demand")

    MONTH_LABELS = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May",
                    6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct",
                    11: "Nov", 12: "Dec"}
    boroughs = sorted(df["PICKUP_BOROUGH"].unique())

    # --- Chart 1: Year-over-year monthly trip volume by borough ---
    st.subheader("\U0001f695 Overall Taxi Volume Holds Steady (+0.8% YoY)")

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
            theme_text = st.get_option("theme.textColor") or TEXT_COLOR
            fig.update_layout(
                title=dict(text=f"Monthly Trip Volume ({borough})", x=0.5, xanchor="center",
                           font=dict(size=20, color=theme_text)),
                height=450,
                plot_bgcolor=BG_COLOR,
                paper_bgcolor=PAPER_COLOR,
                font=dict(color=theme_text, size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Month", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text)),
                yaxis=dict(title="Total Trips", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text)),
                legend=dict(font=dict(size=14, color=theme_text))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Takeaway: In this dashboard, the gray lines and bars represent 2025, while the blue lines and bars represent 2026. 
        Overall taxi demand in NYC grew by 0.8% YoY, so relatively flat. Boroughs like The Bronx and Brooklyn each grew by 
        about 40%, while Manhattan, which accounts for the majority of taxi trips in NYC, declined by 0.7% YoY.
        """)

    st.markdown("---")

    # --- Chart 2: Weekday vs weekend demand by hour ---
    st.subheader("\U0001f552 Weekday Demand Spikes at Rush Hour While Weekends Stay Flat")

    with st.expander("How to read this chart"):
        st.markdown("""
        This line chart shows average trips per hour across the 24-hour day, comparing weekdays
        to weekends.

        - **Green line** = Weekdays (Mon-Fri)
        - **Orange line** = Weekends (Sat-Sun)
        - **Shaded regions** = Rush hours (7-9 AM and 5-7 PM), when commuters typically travel to and from work
        - Totals are divided by the number of days in each group so the lines are directly comparable
        - Each tab shows one borough
        - Hover over points for exact values
        """)

    weather_dim_for_days = load_table("dim_weather")
    weather_dim_for_days["WEATHER_DATE"] = pd.to_datetime(weather_dim_for_days["WEATHER_DATE"])
    weather_dim_for_days["_IS_WEEKEND"] = weather_dim_for_days["WEATHER_DATE"].dt.weekday >= 5
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
                line=dict(color="#2ca02c", width=3),
                marker=dict(size=6, color="#2ca02c"),
                hovertemplate="<b>Weekday</b><br>Hour: %{x}:00<br>Avg Trips: %{y:,.0f}<extra></extra>"
            ))
            fig.add_trace(go.Scatter(
                x=weekend_hourly["PICKUP_HOUR"].values,
                y=weekend_hourly["AVG_TRIPS"].values,
                mode="lines+markers", name="Weekend",
                line=dict(color="#ff7f0e", width=3),
                marker=dict(size=6, color="#ff7f0e"),
                hovertemplate="<b>Weekend</b><br>Hour: %{x}:00<br>Avg Trips: %{y:,.0f}<extra></extra>"
            ))
            fig.add_vrect(x0=7, x1=9, fillcolor="gray", opacity=0.1,
                          line_width=0, annotation_text="Rush Hour", annotation_position="top left",
                          annotation_font=dict(size=11, color="gray"))
            fig.add_vrect(x0=17, x1=19, fillcolor="gray", opacity=0.1,
                          line_width=0, annotation_text="Rush Hour", annotation_position="top left",
                          annotation_font=dict(size=11, color="gray"))
            theme_text = st.get_option("theme.textColor") or TEXT_COLOR
            fig.update_layout(
                title=dict(text=f"Average Hourly Demand: Weekday vs. Weekend ({borough})",
                           x=0.5, xanchor="center", font=dict(size=20, color=theme_text)),
                height=450,
                plot_bgcolor=BG_COLOR,
                paper_bgcolor=PAPER_COLOR,
                font=dict(color=theme_text, size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Hour of Day", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text), tickmode="linear", dtick=2),
                yaxis=dict(title="Avg Trips per Hour", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text)),
                legend=dict(font=dict(size=14, color=theme_text))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Takeaway: In this chart, the green line represents taxi demand on weekdays, while the orange line represents the taxi demand on weekends. 
        Taxi demand increases rapidly during weekday rush hours, while weekends have a more gradual increase in demand throughout the day. 
        So when there's bad weather during weekday rush hours, it's likely to have a larger impact on taxi revenue 
        than that same weather would on the weekend, which we'll explore shortly.
        """)

    st.markdown("---")

    # --- Chart 3: Average trip cost by borough, tabbed by weather category ---
    st.subheader("\U0001f4b3 Average Trip Cost Remains Stable Across Weather Conditions")

    with st.expander("How to read this chart"):
        st.markdown("""
        This grouped bar chart shows the average trip cost (excluding tips) for each borough,
        comparing 2025 vs. 2026.

        - **Gray bars** = 2025
        - **Navy bars** = 2026
        - Each tab shows a different weather category
        - Hover over bars for exact dollar amounts
        - Tips are excluded for consistency (cash tips are not recorded in the data)
        """)

    weather_cat_emojis = {"Clear": "☀️ Clear", "Cloudy": "☁️ Cloudy", "Drizzle": "\U0001f4a7 Drizzle", "Rain": "☂️ Rain", "Snow": "❄️ Snow"}
    weather_cats = sorted(df["WEATHER_CATEGORY"].unique())
    tabs3 = st.tabs([weather_cat_emojis.get(c, c) for c in weather_cats])
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
            theme_text = st.get_option("theme.textColor") or TEXT_COLOR
            fig.update_layout(
                title=dict(text=f"Average Trip Cost by Borough ({weather_cat})",
                           x=0.5, xanchor="center", font=dict(size=20, color=theme_text)),
                barmode="group",
                height=500,
                plot_bgcolor=BG_COLOR,
                paper_bgcolor=PAPER_COLOR,
                font=dict(color=theme_text, size=14),
                margin=dict(l=50, r=50, t=70, b=80),
                xaxis=dict(title="Borough", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text)),
                yaxis=dict(title="Avg Cost per Trip ($)", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text), tickprefix="$"),
                legend=dict(font=dict(size=14, color=theme_text))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Takeaway: Surprisingly, the cost of a taxi trip isn't impacted by weather. Average fares
        stay consistent across all conditions and boroughs, which confirms that weather's impact
        on revenue is driven by the number of rides taken, as opposed to the cost per trip.
        """)

    st.markdown("---")

    # --- Chart 4: Per-hour demand change during adverse weather ---
    st.subheader("☂️❄️ Weather's Effect on Taxi Demand Shifted Between 2025 and 2026")

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

    weather_dim = load_table("dim_weather")
    weather_dim["WEATHER_DATE"] = pd.to_datetime(weather_dim["WEATHER_DATE"])
    weather_dim["YEAR"] = weather_dim["WEATHER_DATE"].dt.year
    weather_dim["IS_NIGHT"] = (weather_dim["WEATHER_HOUR"] >= 20) | (weather_dim["WEATHER_HOUR"] < 6)

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
        vals_2025 = [d["pct_change"] for d in changes_2025]
        vals_2026 = [d["pct_change"] for d in changes_2026]
        fig.add_trace(go.Bar(
            x=[d["borough"] for d in changes_2025],
            y=vals_2025,
            name="2025",
            marker_color=COLOR_2025,
            marker_line=dict(width=1, color="black"),
            text=[f"{v:+.1f}%" for v in vals_2025],
            textposition="outside", textfont=dict(size=12),
            hovertemplate="<b>%{x}</b><br>2025 Change: %{y:+.2f}%<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=[d["borough"] for d in changes_2026],
            y=vals_2026,
            name="2026",
            marker_color=COLOR_2026,
            marker_line=dict(width=1, color="black"),
            text=[f"{v:+.1f}%" for v in vals_2026],
            textposition="outside", textfont=dict(size=12),
            hovertemplate="<b>%{x}</b><br>2026 Change: %{y:+.2f}%<extra></extra>"
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        theme_text = st.get_option("theme.textColor") or TEXT_COLOR
        fig.update_layout(
            title=dict(text=f"Hourly Demand Change During Adverse Weather ({subtitle})",
                       x=0.5, xanchor="center", font=dict(size=20, color=theme_text)),
            barmode="group",
            height=500,
            plot_bgcolor=BG_COLOR,
            paper_bgcolor=PAPER_COLOR,
            font=dict(color=theme_text, size=14),
            margin=dict(l=50, r=50, t=70, b=50),
            xaxis=dict(title="Borough", title_font=dict(size=16, color=theme_text),
                       tickfont=dict(size=14, color=theme_text)),
            yaxis=dict(title="% Change in Trips/Hour (Adverse vs. Clear)",
                       title_font=dict(size=16, color=theme_text),
                       tickfont=dict(size=14, color=theme_text), ticksuffix="%",
                       zeroline=True),
            legend=dict(font=dict(size=14, color=theme_text))
        )
        st.plotly_chart(fig, use_container_width=True)

    tab_day, tab_night = st.tabs(["☀️ Day (6 AM - 8 PM)", "\U0001f319 Night (8 PM - 6 AM)"])
    with tab_day:
        day_changes = compute_weather_changes(df, weather_dim, night_filter=False)
        render_weather_chart(day_changes, "Daytime Hours")
    with tab_night:
        night_changes = compute_weather_changes(df, weather_dim, night_filter=True)
        render_weather_chart(night_changes, "Nighttime Hours")

    with st.expander("Show interpretation"):
        st.markdown("""
        Takeaway: In this chart and the next, positive bars mean more trips per hour during rain or snow compared to clear weather, and negative bars mean fewer
        trips per hour when there's bad weather. In 2025, bad weather increased demand, but in 2026 it lowered demand.
        In 2026 during the day, all 5 boroughs show reduced demand during adverse weather, by as much as 24 percent in The Bronx and Queens.
        """)

    st.markdown("---")

    # --- Chart 5: Weather type breakdown (rain vs snow) ---
    st.subheader("❄️ Snow Drives the Demand Drop While Rain Still Boosts Ridership")

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
            theme_text = st.get_option("theme.textColor") or TEXT_COLOR
            fig.update_layout(
                title=dict(text=f"Demand Change by Adverse Weather Type ({borough})",
                           x=0.5, xanchor="center", font=dict(size=20, color=theme_text)),
                barmode="group", height=450,
                plot_bgcolor=BG_COLOR, paper_bgcolor=PAPER_COLOR,
                font=dict(color=theme_text, size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Adverse Weather Type", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text)),
                yaxis=dict(title="% Change vs. Clear Weather", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text), ticksuffix="%", zeroline=True),
                legend=dict(font=dict(size=14, color=theme_text))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Takeaway: This chart sheds light on why demand shifted between 2025 and 2026. Rain actually increases ridership in both years, 
        however, the snow in 2026 was far more severe than in 2025, driving the overall demand decline during bad weather.
        """)

    st.markdown("---")

    # --- Chart 6: Revenue per adverse-weather hour, rush vs off-peak ---
    st.subheader("\U0001f4b0 Adverse-Weather-Hour Revenue Losses Concentrate During Rush Hour")

    with st.expander("How to read this chart"):
        st.markdown("""
        This chart shows the **dollar difference in revenue per hour** during adverse weather
        compared to clear weather, split by rush hour vs. off-peak.

        - **Gray bars** = 2025
        - **Navy bars** = 2026
        - **Negative values** = revenue lost per adverse-weather hour compared to a clear-weather hour
        - **Positive values** = revenue gained per adverse-weather hour (riders switching to taxis)
        - **Rush Hour** = 7-9 AM and 5-7 PM weekdays
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
                wf = wf[wf["WEATHER_HOUR"].isin([7, 8, 17, 18])]
            else:
                wf = wf[~wf["WEATHER_HOUR"].isin([7, 8, 17, 18])]

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
            theme_text = st.get_option("theme.textColor") or TEXT_COLOR
            fig.update_layout(
                title=dict(text=f"Revenue Impact per Adverse-Weather Hour ({borough})",
                           x=0.5, xanchor="center", font=dict(size=20, color=theme_text)),
                barmode="group", height=450,
                plot_bgcolor=BG_COLOR, paper_bgcolor=PAPER_COLOR,
                font=dict(color=theme_text, size=14),
                margin=dict(l=50, r=50, t=70, b=50),
                xaxis=dict(title="Time Period", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text)),
                yaxis=dict(title="Revenue Difference per Hour ($)", title_font=dict(size=16, color=theme_text),
                           tickfont=dict(size=14, color=theme_text), tickprefix="$", zeroline=True),
                legend=dict(font=dict(size=14, color=theme_text))
            )
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show interpretation"):
        st.markdown("""
        Takeaway: This chart puts a dollar amount on the YoY demand shift. For example, in Manhattan during rush hour, rain and snow
        went from adding \$31K/hr in revenue in 2025 to costing over \$58K/hr in 2026. That's a swing of nearly \$90K/hr YoY,
        concentrated in high-demand periods.

        A limitation of the data is that it can't distinguish whether the revenue loss comes from fewer drivers or fewer riders,
        but it does pinpoint exactly when and where the loss is greatest, giving decision-makers in the NYC taxi industry
        a clear starting point.
        """)
