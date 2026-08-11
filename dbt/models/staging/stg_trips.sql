with yellow as (

    select
        'yellow'                    as taxi_type,
        "VendorID"                  as vendor_id,
        "tpep_pickup_datetime"      as pickup_at,
        "tpep_dropoff_datetime"     as dropoff_at,
        "passenger_count",
        "trip_distance",
        "RatecodeID"                as rate_code_id,
        "store_and_fwd_flag",
        "PULocationID"              as pickup_zone_id,
        "DOLocationID"              as dropoff_zone_id,
        "payment_type",
        "fare_amount",
        "extra",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "congestion_surcharge",
        "Airport_fee"               as airport_fee,
        "cbd_congestion_fee",
        null::float                 as ehail_fee,
        null::int                   as trip_type
    from {{ source('bronze', 'yellow_raw') }}

),

green as (

    select
        'green'                     as taxi_type,
        "VendorID"                  as vendor_id,
        "lpep_pickup_datetime"      as pickup_at,
        "lpep_dropoff_datetime"     as dropoff_at,
        "passenger_count",
        "trip_distance",
        "RatecodeID"                as rate_code_id,
        "store_and_fwd_flag",
        "PULocationID"              as pickup_zone_id,
        "DOLocationID"              as dropoff_zone_id,
        "payment_type",
        "fare_amount",
        "extra",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "congestion_surcharge",
        null::float                 as airport_fee,
        "cbd_congestion_fee",
        "ehail_fee",
        "trip_type"
    from {{ source('bronze', 'green_raw') }}

),

combined as (

    select * from yellow
    union all
    select * from green

),

with_derived as (

    select
        *,
        datediff('minute', pickup_at, dropoff_at)   as trip_duration_minutes,
        year(pickup_at)                             as pickup_year,
        month(pickup_at)                            as pickup_month,
        dayofweek(pickup_at)                        as pickup_dayofweek,
        hour(pickup_at)                             as pickup_hour,
        case when hour(pickup_at) >= 20 or hour(pickup_at) < 6 then true else false end as is_night,
        case when dayofweek(pickup_at) in (0, 6) then true else false end as is_weekend,
        case
            when dayofweek(pickup_at) not in (0, 6)
             and (hour(pickup_at) between 7 and 8 or hour(pickup_at) between 17 and 18)
            then true else false
        end as is_rush_hour
    from combined

)

select
    *,
    case
        when trip_duration_minutes < 0 then false
        when "fare_amount" < 0 then false
        when "total_amount" < 0 then false
        when "trip_distance" < 0 then false
        when "trip_distance" > 100 then false
        when pickup_year not in (2025, 2026) then false
        when pickup_month not between 1 and 5 then false
        else true
    end as is_valid,
    array_to_string(array_construct_compact(
        case when trip_duration_minutes < 0 then 'dropoff_before_pickup' end,
        case when "fare_amount" < 0 then 'negative_fare' end,
        case when "total_amount" < 0 then 'negative_total' end,
        case when "trip_distance" < 0 then 'negative_distance' end,
        case when "trip_distance" > 100 then 'extreme_distance' end,
        case when pickup_year not in (2025, 2026) then 'out_of_range_year' end,
        case when pickup_month not between 1 and 5 then 'out_of_range_month' end
    ), ', ') as dq_flag_reason
from with_derived
