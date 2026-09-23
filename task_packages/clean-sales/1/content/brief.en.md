# Practical Assignment: Cleaning Daily Sales Transactions

- **Task ID:** `clean-sales` (Version 1)
- **Workplace Simulation:** Nile Distribution & Trading Co. (Cairo Operations)
- **Direct Supervisor:** Tarek — Operations & Data Lead
- **Accepted Formats:** CSV or Excel (`.csv`, `.xlsx`)
- **Maximum File Size:** 5 MB (5,242,880 bytes)

---

## Workplace Context & Assignment Overview

Welcome to your first workday on the operations team at Nile Distribution Co.!

We received a raw daily sales dataset aggregated hastily from our regional branch representatives. The raw file contains common data hygiene defects that are currently breaking our automated reporting pipelines and accounting spreadsheets.

Your task is to inspect the raw file (`sales_dirty.csv`), resolve all data defects, and deliver a clean, standardized deliverable ready for operational ingestion.

---

## Deliverable Objectives (Pass Requirements)

To satisfy operational review and obtain passing approval, your cleaned deliverable must fulfill four core business requirements:

1. **Order Deduplication:**
   - Audit the `order_id` column. Several transactions were entered multiple times in error.
   - Requirement: Preserve exactly one valid instance of each order and remove all duplicate rows.

2. **Standardize Order Dates:**
   - The `order_date` column contains mixed formats (e.g. `DD/MM/YYYY`, non-standard separators).
   - Requirement: Normalize all dates into ISO 8601 standard format: `YYYY-MM-DD` (e.g. `2026-09-20`).

3. **Validate Numeric Values & Revenue Calculations:**
   - Audit `quantity` and `unit_price` columns for physically impossible negative numbers caused by entry typos.
   - Requirement: Ensure that `revenue` is accurately calculated as `quantity * unit_price` (within acceptable standard rounding).

4. **Handle Missing Customer Emails:**
   - Some customer transactions lack a registered `customer_email`.
   - Requirement: Company policy prohibits dropping valid sales records. Annotate all missing emails by entering `"unavailable"` in the `missing_email_reason` column.

---

## Submission Guidelines & Technical Constraints

- **Required Output Columns:**
  `order_id`, `customer_email`, `order_date`, `quantity`, `unit_price`, `revenue`, `missing_email_reason`
- **File Format & Limits:** Output must be a valid `.csv` or `.xlsx` workbook under 5 MB.
- **Privacy & Safety:** Data is synthetic and intended for simulation only. Do not insert personal identifiers.
- **Grading & Retry Policy:** The pass threshold is 75 points (out of 100). If any check fails, you will receive targeted coaching explaining what to review, allowing you to submit an updated attempt without penalty.
