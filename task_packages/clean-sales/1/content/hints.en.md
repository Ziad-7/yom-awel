# Guidance and Hints — Sales Cleaning Assignment

If you need assistance resolving defects or reviewing evaluation feedback, consult these practical hints:

---

### 1. Removing Duplicates (Deduplication)
- **In Excel or Spreadsheets:** Select the full data range, go to the `Data` tab, select `Remove Duplicates`, and ensure only `order_id` is checked as the unique key.
- **Good Practice:** Avoid manual deletion to prevent unintended data loss. Verify that each `order_id` appears exactly once in the cleaned output.

---

### 2. Standardizing Date Formats
- **Target Format:** Four-digit year, two-digit month, two-digit day separated by dashes: `YYYY-MM-DD` (e.g. `2026-09-20`).
- **Tips:** If some dates were parsed as text strings or formatted as `DD/MM/YYYY`, apply a standardized date format via Cell Formatting or use text/date transformation formulas before saving.

---

### 3. Auditing Numeric Values and Formulas
- **Quantities & Prices:** Any negative quantities or negative unit prices are typos from the raw entry. Ensure these are corrected to their positive valid amounts.
- **Revenue Integrity:** Ensure the `revenue` column strictly equals `quantity * unit_price`. Applying a uniform formula across the entire column prevents manual arithmetic errors.

---

### 4. Handling Missing Customer Emails
- **Do Not Drop Rows:** Deleting transactions with missing emails distorts total company sales reporting.
- **Proper Audit Annotation:** Locate empty cells in `customer_email`, and enter the exact string `"unavailable"` in the corresponding row under `missing_email_reason`.
