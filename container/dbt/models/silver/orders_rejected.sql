select * from {{ ref('stg_orders') }} where rejection_reason is not null
