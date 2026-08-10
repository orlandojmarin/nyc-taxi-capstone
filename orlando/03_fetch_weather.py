"""
Fetch hourly historical weather data from Open-Meteo for NYC.
Covers January-May 2025 and January-May 2026 to match taxi trip data.

Open-Meteo is free, requires no API key, and provides hourly resolution.
Location: Central Park, NYC (40.7831, -73.9712)

Output: orlando/weather_hourly.csv (ready to load into Snowflake)

Usage:
    python orlando/03_fetch_weather.py
"""

import csv
import time
import requests

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

# WMO weather codes for reference (used in weather_code column)
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


def main():
    all_rows = []

    for start_date, end_date in DATE_RANGES:
        print(f"Fetching {start_date} to {end_date}...")
        data = fetch_weather(start_date, end_date)
        hourly = data["hourly"]
        n_hours = len(hourly["time"])

        for i in range(n_hours):
            weather_code = hourly["weather_code"][i]
            row = {
                "datetime_local": hourly["time"][i],
                "temperature_f": hourly["temperature_2m"][i],
                "apparent_temperature_f": hourly["apparent_temperature"][i],
                "precipitation_inch": hourly["precipitation"][i],
                "rain_inch": hourly["rain"][i],
                "snowfall_inch": hourly["snowfall"][i],
                "snow_depth_inch": hourly["snow_depth"][i],
                "weather_code": weather_code,
                "weather_description": WEATHER_DESCRIPTIONS.get(weather_code, "Unknown"),
                "wind_speed_mph": hourly["wind_speed_10m"][i],
                "wind_gusts_mph": hourly["wind_gusts_10m"][i],
                "relative_humidity_pct": hourly["relative_humidity_2m"][i],
                "visibility_ft": hourly["visibility"][i],
            }
            all_rows.append(row)

        print(f"  Got {n_hours} hourly records")
        time.sleep(0.5)  # polite rate limiting

    # Write CSV
    output_path = "orlando/weather_hourly.csv"
    fieldnames = list(all_rows[0].keys())

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nDone. Wrote {len(all_rows)} rows to {output_path}")
    print(f"Date range: {all_rows[0]['datetime_local']} to {all_rows[-1]['datetime_local']}")


if __name__ == "__main__":
    main()
