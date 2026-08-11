with trips as (

    select * from {{ ref('stg_trips') }}
    where IS_VALID = true

),

zones as (

    select * from {{ ref('stg_zones') }}

),

weather as (

    select * from {{ ref('stg_weather') }}

)

select
    t.TAXI_TYPE             as taxi_type,
    t.PICKUP_AT             as pickup_at,
    t.DROPOFF_AT            as dropoff_at,
    t.PICKUP_YEAR           as pickup_year,
    t.PICKUP_MONTH          as pickup_month,
    t.PICKUP_DAYOFWEEK      as pickup_dayofweek,
    t.PICKUP_HOUR           as pickup_hour,
    t.IS_NIGHT              as is_night,
    t.IS_WEEKEND            as is_weekend,
    t.IS_RUSH_HOUR          as is_rush_hour,
    t.TRIP_DURATION_MINUTES as trip_duration_minutes,
    t."trip_distance"       as trip_distance,
    t."passenger_count"     as passenger_count,
    t."payment_type"        as payment_type,
    t."fare_amount"         as fare_amount,
    t."extra"               as extra,
    t."mta_tax"             as mta_tax,
    t."tip_amount"          as tip_amount,
    t."tolls_amount"        as tolls_amount,
    t."improvement_surcharge" as improvement_surcharge,
    t."congestion_surcharge" as congestion_surcharge,
    t."cbd_congestion_fee"  as cbd_congestion_fee,
    t.AIRPORT_FEE           as airport_fee,
    t."total_amount"        as total_amount,
    t.PICKUP_ZONE_ID        as pickup_zone_id,
    t.DROPOFF_ZONE_ID       as dropoff_zone_id,
    pz.BOROUGH              as pickup_borough,
    pz.ZONE_NAME            as pickup_zone_name,
    dz.BOROUGH              as dropoff_borough,
    dz.ZONE_NAME            as dropoff_zone_name,
    w.WEATHER_CATEGORY      as weather_category,
    w.IS_ADVERSE_WEATHER    as is_adverse_weather,
    w.TEMPERATURE_F         as temperature_f,
    w.PRECIPITATION_INCH    as precipitation_inch,
    w.WIND_SPEED_MPH        as wind_speed_mph
from trips t
left join zones pz
    on t.PICKUP_ZONE_ID = pz.LOCATION_ID
left join zones dz
    on t.DROPOFF_ZONE_ID = dz.LOCATION_ID
left join weather w
    on date(t.PICKUP_AT) = w.WEATHER_DATE
    and hour(t.PICKUP_AT) = w.WEATHER_HOUR
