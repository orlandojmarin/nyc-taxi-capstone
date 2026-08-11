WITH trips as (

    SELECT *
    FROM {{ ref('fct_trips') }}

)

SELECT
    pickup_year,
    pickup_zone_name,

    count(*) as trip_count,

    avg(total_amount) as avg_total_amount,
    avg(fare_amount) as avg_fare_amount,
    avg(tip_amount) as avg_tip_amount,

    avg(trip_duration_minutes) as avg_duration_minutes,
    avg(trip_distance) as avg_distance,

    avg(case when is_rush_hour then 1 else 0 end) as pct_rush_hour,
    avg(case when is_night then 1 else 0 end) as pct_night,
    avg(case when is_weekend then 1 else 0 end) as pct_weekend,

    avg(case when is_adverse_weather then 1 else 0 end) as pct_adverse_weather

FROM trips

WHERE pickup_zone_name is not null

GROUP BY 
    pickup_zone_name,
    pickup_year