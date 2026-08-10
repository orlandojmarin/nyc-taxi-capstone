"""
Fetch hourly historical weather data from Open-Meteo for NYC
and load it directly into Snowflake BRONZE.weather_hourly.

Open-Meteo is free, requires no API key, and provides hourly resolution.
Location: Central Park, NYC (40.7831, -73.9712)

Prerequisites:
    pip install requests pandas snowflake-connector-python

Usage:
    python orlando/03_fetch_weather.py
"""

import time
import requests
import pandas as pd
from snowflake_connect import get_connection, run_sql, load_dataframe

# NYC Central Park coordinates
LAT = 40.7831
LON = -73.9712

# Date ranges matching our taxi data
DATE_RANGES = [
    ("2025-01-01", "2025-05-31"),
    ("2026-01-01", "2026-05-31"),
]

# Hourly variables to pull
HOURLY_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "snow_depth",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "relative_humidity_2m",
    "visibility",
]

WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def fetch_weather(start_date, end_date):
    """Fetch hourly weather from Open-Meteo archive API."""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARS),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York",
    }

    r = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params)
    r.raise_for_status()
    return r.json()


def fetch_all_weather():
    """Fetch weather for all date ranges and return a DataFrame."""
    all_rows = []

    for start_date, end_date in DATE_RANGES:
        print(f"Fetching {start_date} to {end_date}...")
        data = fetch_weather(start_date, end_date)
        hourly = data["hourly"]
        n_hours = len(hourly["time"])

        for i in range(n_hours):
            weather_code = hourly["weather_code"][i]
            row = {
                "DATETIME_LOCAL": hourly["time"][i],
                "TEMPERATURE_F": hourly["temperature_2m"][i],
                "APPARENT_TEMPERATURE_F": hourly["apparent_temperature"][i],
                "PRECIPITATION_INCH": hourly["precipitation"][i],
                "RAIN_INCH": hourly["rain"][i],
                "SNOWFALL_INCH": hourly["snowfall"][i],
                "SNOW_DEPTH_INCH": hourly["snow_depth"][i],
                "WEATHER_CODE": weather_code,
                "WEATHER_DESCRIPTION": WEATHER_DESCRIPTIONS.get(weather_code, "Unknown"),
                "WIND_SPEED_MPH": hourly["wind_speed_10m"][i],
                "WIND_GUSTS_MPH": hourly["wind_gusts_10m"][i],
                "RELATIVE_HUMIDITY_PCT": hourly["relative_humidity_2m"][i],
                "VISIBILITY_FT": hourly["visibility"][i],
            }
            all_rows.append(row)

        print(f"  Got {n_hours} hourly records")
        time.sleep(0.5)

    df = pd.DataFrame(all_rows)
    df["DATETIME_LOCAL"] = pd.to_datetime(df["DATETIME_LOCAL"])
    return df


def load_to_snowflake(df):
    """Create the Bronze weather table and load the DataFrame."""
    conn = get_connection()
    try:
        # Set context
        run_sql("USE ROLE DE", conn)
        run_sql("USE WAREHOUSE COMPUTE_WH", conn)
        run_sql("USE DATABASE TECHCATALYST", conn)
        run_sql("CREATE SCHEMA IF NOT EXISTS TECHCATALYST.BRONZE", conn)
        run_sql("USE SCHEMA BRONZE", conn)

        # Drop and recreate to ensure idempotency
        run_sql("DROP TABLE IF EXISTS WEATHER_HOURLY", conn)

        # Load using write_pandas (handles table creation automatically)
        load_dataframe(df, "WEATHER_HOURLY", overwrite=True, create=True, conn=conn)

        # Verify
        result = run_sql("SELECT COUNT(*) FROM WEATHER_HOURLY", conn)
        print(f"\nVerification: {result[0][0]} rows in BRONZE.WEATHER_HOURLY")
    finally:
        conn.close()


def main():
    df = fetch_all_weather()
    print(f"\nFetched {len(df)} total rows")
    print(f"Date range: {df['DATETIME_LOCAL'].min()} to {df['DATETIME_LOCAL'].max()}")

    load_to_snowflake(df)
    print("\nDone. Weather data loaded into TECHCATALYST.BRONZE.WEATHER_HOURLY")


if __name__ == "__main__":
    main()
