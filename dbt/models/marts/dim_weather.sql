select
    WEATHER_DATE        as weather_date,
    WEATHER_HOUR        as weather_hour,
    TEMPERATURE_F       as temperature_f,
    APPARENT_TEMPERATURE_F as apparent_temperature_f,
    PRECIPITATION_INCH  as precipitation_inch,
    RAIN_INCH           as rain_inch,
    SNOWFALL_INCH       as snowfall_inch,
    SNOW_DEPTH_INCH     as snow_depth_inch,
    WEATHER_CODE        as weather_code,
    WEATHER_DESCRIPTION as weather_description,
    WIND_SPEED_MPH      as wind_speed_mph,
    WIND_GUSTS_MPH      as wind_gusts_mph,
    RELATIVE_HUMIDITY_PCT as relative_humidity_pct,
    VISIBILITY_FT       as visibility_ft,
    WEATHER_CATEGORY    as weather_category,
    IS_ADVERSE_WEATHER  as is_adverse_weather
from {{ ref('stg_weather') }}
