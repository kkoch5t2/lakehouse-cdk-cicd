with normalized as (
 select try_cast(nullif(trim(order_id), '') as bigint) order_id,
        trim(customer_name) customer_name,
        try_cast(amount as decimal(12,2)) amount,
        lower(trim(status)) status,
        try_cast(order_date as date) order_date,
        try_cast(source_updated_at as timestamp) source_updated_at,
        event_id
 from {{ source('bronze', 'orders_raw') }}
), ranked as (
 select *, row_number() over (
   partition by coalesce(cast(order_id as varchar), concat('invalid:', event_id))
   order by source_updated_at desc nulls last, event_id desc) rn
 from normalized
)
select *, case
 when order_id is null then 'invalid_order_id'
 when source_updated_at is null then 'invalid_updated_at'
 when amount is null or amount < 0 then 'invalid_amount'
 when order_date is null then 'invalid_date'
 when status not in ('new','paid','cancelled') then 'invalid_status'
 when customer_name is null or customer_name = '' then 'invalid_customer'
 else null end rejection_reason
from ranked where rn = 1
