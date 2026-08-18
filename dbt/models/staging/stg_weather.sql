select
    "DATETIME_LOCAL",
    date("DATETIME_LOCAL")                as weather_date,
    hour("DATETIME_LOCAL")                as weather_hour,
    "TEMPERATURE_F",
    "APPARENT_TEMPERATURE_F",
    "PRECIPITATION_INCH",
    "RAIN_INCH",
    "SNOWFALL_INCH",
    "SNOW_DEPTH_INCH",
    "WEATHER_CODE",
    "WEATHER_DESCRIPTION",
    "WIND_SPEED_MPH",
    "WIND_GUSTS_MPH",
    "RELATIVE_HUMIDITY_PCT",
    "VISIBILITY_FT",
    case
        when "WEATHER_CODE" in (0, 1)         then 'Clear'
        when "WEATHER_CODE" in (2, 3)         then 'Cloudy'
        when "WEATHER_CODE" in (45, 48)       then 'Fog'
        when "WEATHER_CODE" between 51 and 57 then 'Drizzle'
        when "WEATHER_CODE" between 61 and 67 then 'Rain'
        when "WEATHER_CODE" between 71 and 77 then 'Snow'
        when "WEATHER_CODE" between 80 and 82 then 'Rain Showers'
        when "WEATHER_CODE" between 85 and 86 then 'Snow Showers'
        when "WEATHER_CODE" between 95 and 99 then 'Thunderstorm'
        else 'Other'
    end as weather_category,
    case
        when "WEATHER_CODE" >= 61 or "SNOWFALL_INCH" > 0 or "WIND_SPEED_MPH" > 25
        then true else false
    end as is_adverse_weather
from {{ source('bronze', 'weather_hourly') }}
