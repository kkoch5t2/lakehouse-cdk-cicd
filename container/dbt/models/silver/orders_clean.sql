select order_id, customer_name, amount, status, order_date, source_updated_at
from {{ ref('stg_orders') }} where rejection_reason is null
