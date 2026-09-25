# Hints

- Filter `status` to paid **before** grouping.
- `COUNT(*)` counts orders in each group.
- `SUM(quantity * unit_price)` calculates the group's revenue; `ROUND(..., 2)` gives cents.
- Alias your three columns exactly as `region`, `paid_orders`, and `total_revenue`.
