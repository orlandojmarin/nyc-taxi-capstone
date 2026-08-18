with yellow as (

    select
        'yellow'                    as TAXI_TYPE,
        "VendorID"                  as VENDOR_ID,
        "tpep_pickup_datetime"      as PICKUP_AT,
        "tpep_dropoff_datetime"     as DROPOFF_AT,
        "passenger_count"           as PASSENGER_COUNT,
        "trip_distance"             as TRIP_DISTANCE,
        "RatecodeID"                as RATE_CODE_ID,
        "store_and_fwd_flag"        as STORE_AND_FWD_FLAG,
        "PULocationID"              as PICKUP_ZONE_ID,
        "DOLocationID"              as DROPOFF_ZONE_ID,
        "payment_type"              as PAYMENT_TYPE,
        "fare_amount"               as FARE_AMOUNT,
        "extra"                     as EXTRA,
        "mta_tax"                   as MTA_TAX,
        "tip_amount"                as TIP_AMOUNT,
        "tolls_amount"              as TOLLS_AMOUNT,
        "improvement_surcharge"     as IMPROVEMENT_SURCHARGE,
        "total_amount"              as TOTAL_AMOUNT,
        "congestion_surcharge"      as CONGESTION_SURCHARGE,
        "Airport_fee"               as AIRPORT_FEE,
        "cbd_congestion_fee"        as CBD_CONGESTION_FEE,
        null::float                 as EHAIL_FEE,
        null::int                   as TRIP_TYPE
    from {{ source('bronze', 'yellow_raw') }}

),

green as (

    select
        'green'                     as TAXI_TYPE,
        "VendorID"                  as VENDOR_ID,
        "lpep_pickup_datetime"      as PICKUP_AT,
        "lpep_dropoff_datetime"     as DROPOFF_AT,
        "passenger_count"           as PASSENGER_COUNT,
        "trip_distance"             as TRIP_DISTANCE,
        "RatecodeID"                as RATE_CODE_ID,
        "store_and_fwd_flag"        as STORE_AND_FWD_FLAG,
        "PULocationID"              as PICKUP_ZONE_ID,
        "DOLocationID"              as DROPOFF_ZONE_ID,
        "payment_type"              as PAYMENT_TYPE,
        "fare_amount"               as FARE_AMOUNT,
        "extra"                     as EXTRA,
        "mta_tax"                   as MTA_TAX,
        "tip_amount"                as TIP_AMOUNT,
        "tolls_amount"              as TOLLS_AMOUNT,
        "improvement_surcharge"     as IMPROVEMENT_SURCHARGE,
        "total_amount"              as TOTAL_AMOUNT,
        "congestion_surcharge"      as CONGESTION_SURCHARGE,
        null::float                 as AIRPORT_FEE,
        "cbd_congestion_fee"        as CBD_CONGESTION_FEE,
        "ehail_fee"                 as EHAIL_FEE,
        "trip_type"                 as TRIP_TYPE
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
        datediff('minute', PICKUP_AT, DROPOFF_AT)   as TRIP_DURATION_MINUTES,
        year(PICKUP_AT)                             as PICKUP_YEAR,
        month(PICKUP_AT)                            as PICKUP_MONTH,
        dayofweek(PICKUP_AT)                        as PICKUP_DAYOFWEEK,
        hour(PICKUP_AT)                             as PICKUP_HOUR,
        case when hour(PICKUP_AT) >= 20 or hour(PICKUP_AT) < 6 then true else false end as IS_NIGHT,
        case when dayofweek(PICKUP_AT) in (0, 6) then true else false end as IS_WEEKEND,
        case
            when dayofweek(PICKUP_AT) not in (0, 6)
             and (hour(PICKUP_AT) between 7 and 8 or hour(PICKUP_AT) between 17 and 18)
            then true else false
        end as IS_RUSH_HOUR
    from combined

)

select
    *,
    case
        when TRIP_DURATION_MINUTES < 0 then false
        when FARE_AMOUNT < 0 then false
        when TOTAL_AMOUNT < 0 then false
        when TRIP_DISTANCE < 0 then false
        when TRIP_DISTANCE > 100 then false
        when PICKUP_YEAR not in (2025, 2026) then false
        when PICKUP_MONTH not between 1 and 5 then false
        else true
    end as IS_VALID,
    array_to_string(array_construct_compact(
        case when TRIP_DURATION_MINUTES < 0 then 'dropoff_before_pickup' end,
        case when FARE_AMOUNT < 0 then 'negative_fare' end,
        case when TOTAL_AMOUNT < 0 then 'negative_total' end,
        case when TRIP_DISTANCE < 0 then 'negative_distance' end,
        case when TRIP_DISTANCE > 100 then 'extreme_distance' end,
        case when PICKUP_YEAR not in (2025, 2026) then 'out_of_range_year' end,
        case when PICKUP_MONTH not between 1 and 5 then 'out_of_range_month' end
    ), ', ') as DQ_FLAG_REASON
from with_derived
