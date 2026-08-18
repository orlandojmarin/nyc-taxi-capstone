select
    LOCATIONID      as location_id,
    BOROUGH         as borough,
    ZONE            as zone_name,
    SERVICE_ZONE
from {{ source('bronze', 'zone_lookup') }}
