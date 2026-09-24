# Guidance and Hints — Sales Cleaning Assignment

If you need assistance resolving defects or reviewing evaluation feedback, consult these practical hints to prepare an approved submission:

---

### 1. Order Deduplication & Primary Key Integrity (`unique_orders` — Critical Check)
- **Top Priority:** Duplicate order IDs cause immediate assignment failure, even if your submission scores 75 points from other checks.
- **In Excel or Spreadsheets:** Select the full data range, navigate to the `Data` tab, select `Remove Duplicates`, and ensure only `order_id` is selected as the unique comparison key.
- **Minimum Rows Warning:** Ensure your cleaned file retains at least 40 valid data rows. Dropping additional rows causes automated rejection (`too_few_rows`).

---

### 2. Standardizing Date Formats (`standard_dates`)
- **Target Format:** Four-digit year, two-digit month, two-digit day separated by dashes: `YYYY-MM-DD` (e.g. `2026-09-20`).
- **Spreadsheet Tools:** If some dates are stored as text or `DD/MM/YYYY`, apply a standardized date format via Cell Formatting or use text/date transformation formulas (`DATE`, `TEXT`) before saving.

---

### 3. Auditing Numeric Values and Revenue Calculations (`valid_numeric_values`)
- **Quantities & Prices:** Correct any negative or zero values in `quantity` and `unit_price` resulting from typo defects to their positive valid values.
- **Revenue Integrity:** Ensure the `revenue` column strictly equals `quantity * unit_price` across all rows, within the ±0.01 tolerance.

---

### 4. Handling Missing Customer Records (`complete_customer_records`)
- **Do Not Drop Rows:** Deleting transactions with missing emails distorts total company sales reporting and violates operational policy.
- **Proper Audit Annotation:** Locate empty cells in `customer_email`, and enter the exact string `"unavailable"` in the corresponding row under `missing_email_reason`.

