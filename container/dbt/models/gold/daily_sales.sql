select order_date, count(*) order_count, sum(amount) sales_amount
from {{ ref('orders_clean') }} where status = 'paid'
group by order_date
