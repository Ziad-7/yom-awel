# Practical Assignment: Cleaning Daily Sales Transactions

- **Task ID:** `clean-sales` (Version 1 — Official Release Deliverable)
- **Workplace Simulation:** Nile Distribution & Trading Co. (Cairo Operations)
- **Direct Supervisor:** Tarek — Operations & Data Lead
- **Accepted Formats:** Tabular spreadsheets in CSV or Excel (`.csv`, `.xlsx`)
- **Maximum File Size:** 5 MB (5,242,880 bytes)
- **Minimum Retained Data Rows:** 40 rows after deduplication
- **Pass Requirement:** Score >= 75 points out of 100 **AND** pass the critical check (`unique_orders`)

---

## Workplace Context & Assignment Overview

Welcome to your first workday on the operations team at Nile Distribution & Trading Co.!

We received a raw daily sales dataset aggregated hastily from our regional branch representatives. The raw file contains common data hygiene defects that are currently breaking our automated reporting pipelines and accounting spreadsheets.

Your task is to inspect the raw file (`sales_dirty.csv`), resolve all data defects, and deliver a clean, standardized deliverable ready for operational ingestion.

---

## Technical Pass Requirements & Objective Breakdown (100 Points)

The automated deterministic evaluation engine evaluates your submitted workbook against four canonical checks (25 points each):

1. **Order Deduplication & Primary Key Integrity (`unique_orders` — Mandatory Critical Check — 25 pts):**
   - Audit the `order_id` column. Several transactions were entered multiple times in error.
   - **Requirement:** Preserve exactly one valid instance of each order and remove all duplicates. Zero duplicate or blank `order_id` values may remain.
   - **Critical Warning:** This check is **critical and non-negotiable**; failing `unique_orders` prevents passing the entire assignment, even if your total score reaches 75 points!

2. **Standardize Order Dates (`standard_dates` — 25 pts):**
   - The `order_date` column contains mixed formats (e.g. `DD/MM/YYYY`, non-standard separators).
   - **Requirement:** Normalize all dates into ISO 8601 standard format: `YYYY-MM-DD` (e.g. `2026-09-20`).

3. **Validate Numeric Values & Revenue Calculations (`valid_numeric_values` — 25 pts):**
   - Audit `quantity` and `unit_price` columns for physically impossible negative numbers or zero values caused by entry typos.
   - **Requirement:** Ensure that `revenue` is accurately calculated as `quantity * unit_price` (within a standard numerical tolerance of ±0.01 EGP).

4. **Handle Missing Customer Emails (`complete_customer_records` — 25 pts):**
   - Some customer transactions lack a registered `customer_email`.
   - **Requirement:** Company policy strictly prohibits dropping valid sales records. Annotate all missing emails by entering the exact string `"unavailable"` in the `missing_email_reason` column.

---

## Submission Guidelines & Evaluator Technical Boundaries

- **Seven Required Columns in Cleaned File (exact names, lowercase):**
  `order_id`, `customer_email`, `order_date`, `quantity`, `unit_price`, `revenue`, `missing_email_reason`
- **Minimum Retained Rows:** Your cleaned file must retain at least 40 valid data rows. Files with fewer than 40 rows are rejected automatically (`too_few_rows`).
- **Excel Specifications:** The evaluation engine parses the first active worksheet only; workbooks with macros, password protection, external links, or exceeding 10,000 rows or 20 columns are rejected.
- **Privacy & Safety Warning:** Data is synthetic and intended solely for simulation. Do not insert real Egyptian national IDs, real telephone numbers, credit cards, or personal passwords.
- **Grading & Retry Flow:** If your submission does not meet the pass rule (75+ points and passing deduplication), your account transitions to `NEEDS_RETRY`. You will receive targeted supervisor feedback in Egyptian Arabic explaining the exact failure categories so you can correct your sheet and resubmit without losing attempt history.

