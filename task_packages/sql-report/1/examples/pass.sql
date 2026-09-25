SELECT region, COUNT(*) AS paid_orders,
       ROUND(SUM(quantity * unit_price), 2) AS total_revenue
FROM sales
WHERE status = 'paid'
GROUP BY region
ORDER BY region;
