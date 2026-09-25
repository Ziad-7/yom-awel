# SQL sales report

Download the sales CSV and write one SQLite `SELECT` query against a table called `sales`.
The table has `order_id`, `region`, `status`, `quantity`, and `unit_price` columns.

Return exactly one row per region **with paid orders**. Your query must return these columns in this order:

1. `region` — the region name.
2. `paid_orders` — the number of orders where `status = 'paid'`.
3. `total_revenue` — the sum of `quantity * unit_price` for those paid orders, rounded to two decimal places.

Do not include pending or cancelled orders. Save your query as a UTF-8 `.sql` file and upload it. You can also use the query editor on the website. Only one read-only SELECT is accepted; the task data cannot be changed.

Start from this outline and complete it yourself:

```sql
SELECT region, ...
FROM sales
WHERE ...
GROUP BY region;
```
