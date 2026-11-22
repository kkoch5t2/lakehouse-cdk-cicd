select * from {{ ref('orders_clean') }} where amount < 0
