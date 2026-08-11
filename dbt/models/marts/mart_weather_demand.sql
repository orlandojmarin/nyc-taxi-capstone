with trips as (

    select * from {{ ref('fct_trips') }}

)

select
    pickup_borough,
    weather_category,
    is_adverse_weather,
    pickup_year,
    pickup_month,
    pickup_hour,
    is_rush_hour,
    is_night,
    is_weekend,
    payment_type,
    count(*)                            as trip_count,
    sum(total_amount)                   as total_revenue,
    sum(fare_amount)                    as total_fares,
    sum(tip_amount)                     as total_tips,
    sum(tolls_amount)                   as total_tolls,
    sum(congestion_surcharge)           as total_congestion_surcharge,
    sum(cbd_congestion_fee)             as total_cbd_fee,
    avg(total_amount)                   as avg_fare_total,
    avg(tip_amount)                     as avg_tip,
    avg(trip_duration_minutes)          as avg_duration_minutes,
    avg(trip_distance)                  as avg_distance
from trips
where pickup_borough is not null
group by
    pickup_borough,
    weather_category,
    is_adverse_weather,
    pickup_year,
    pickup_month,
    pickup_hour,
    is_rush_hour,
    is_night,
    is_weekend,
    payment_type
