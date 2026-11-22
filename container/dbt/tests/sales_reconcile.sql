with expected as (
select order_date, count(*) order_count, sum(amount) sales_amount
from {{ ref('orders_clean') }} where status = 'paid' group by order_date
)
select * from (
(select * from expected except select * from {{ ref('daily_sales') }})
union all
(select * from {{ ref('daily_sales') }} except select * from expected)
) discrepancies
