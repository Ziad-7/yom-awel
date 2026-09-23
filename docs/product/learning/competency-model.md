# Yom Awel Competency Model

- **Domain:** Entry-Level Digital & Data Skills (Egyptian Job Market)
- **Primary Track:** Data Operations and Spreadsheet Mastery
- **Governing Version:** 1.0.0
- **Owners:** Member 1 (Product & Learning Design) in cross-review with Member 4 (Deterministic Evaluation)

---

## 1. Pedagogical Mission

The Yom Awel Competency Model defines observable, measurable workplace capabilities rather than abstract academic concepts. In simulated Egyptian workplaces, digital assistants and junior data coordinators succeed not by memorizing definitions, but by preparing clean, reliable, and auditable spreadsheets for managers and clients.

Every competency defined here maps directly to:
1. Deterministic evaluation checks that verify correctness without human or LLM bias.
2. Formative Egyptian Arabic supervisor feedback that guides reflection and improvement.
3. Verifiable evidence entries in the learner's digital profile.

---

## 2. Core Competency Dimensions

### 2.1 Spreadsheet Hygiene (`comp-spreadsheet-hygiene`)
- **Definition:** Preserving structural integrity, header clarity, sheet naming, cell encoding, and standard column boundaries without extraneous notes or corrupted formatting.
- **Observable Behaviors:**
  - Preserves exact required header names (`order_id`, `customer_email`, `order_date`, `quantity`, `unit_price`, `revenue`, `missing_email_reason`).
  - Does not introduce merged cells or multi-row headers that break automated ingestion.
  - Maintains tabular structure with a single data region.

### 2.2 Deduplication (`comp-deduplication`)
- **Definition:** Identifying and resolving repeated records based on unique business identifiers.
- **Observable Behaviors:**
  - Identifies duplicate occurrences of business primary keys (`order_id`).
  - Retains exactly one valid record per key while removing redundant duplicates.
  - Verifies that record counts decrease by the exact number of duplicates removed.
- **Evaluator Mapping:** Check `unique_orders` (25 points).

### 2.3 Type Normalization & Dates (`comp-type-normalization`)
- **Definition:** Converting heterogeneous date and numeric strings into standardized, queryable machine formats.
- **Observable Behaviors:**
  - Standardizes diverse date formats (e.g. `DD/MM/YYYY`, `MM-DD-YYYY`, text dates) into the ISO 8601 standard format (`YYYY-MM-DD`).
  - Prevents date ambiguity and avoids introducing invalid leap-year or month/day inversion errors.
- **Evaluator Mapping:** Check `standard_dates` (25 points).

### 2.4 Numeric Validation & Formula Integrity (`comp-numeric-integrity`)
- **Definition:** Auditing numeric columns for physical validity, sign errors, and arithmetic consistency.
- **Observable Behaviors:**
  - Audits negative numbers (e.g. quantity `-2`, negative prices) resulting from input errors.
  - Ensures mathematical relationship: `revenue == quantity * unit_price` within acceptable rounding tolerance.
  - Leaves zero division or formula syntax errors absent.
- **Evaluator Mapping:** Check `valid_numeric_values` (25 points).

### 2.5 Handling Missing Data & Audit Annotation (`comp-missing-data-handling`)
- **Definition:** Making deliberate, policy-compliant decisions when critical attributes are absent rather than silently deleting rows or leaving blanks.
- **Observable Behaviors:**
  - Distinguishes between rows that can be preserved and missing attributes that require annotation.
  - For missing customer emails, annotates the reason explicitly as `"unavailable"` in `missing_email_reason` rather than deleting the valuable sales transaction.
- **Evaluator Mapping:** Check `complete_customer_records` (25 points).

### 2.6 Professional Workplace Delivery (`comp-workplace-delivery`)
- **Definition:** Delivering deliverables adhering to file format limits, naming conventions, and deadline expectations.
- **Observable Behaviors:**
  - Uploads valid `.csv` or `.xlsx` files below the 5 MB threshold.
  - Demonstrates iterative learning by improving scores across subsequent retry attempts.

---

## 3. Governance and Invariants

1. **Deterministic Authority:**
   Competency accreditation is governed exclusively by deterministic evaluation checks. AI feedback agents provide pedagogical coaching, but cannot award badges or alter competency scores.
2. **Dual-Owner Policy Control:**
   Any modification to competency definitions, check point allocations, or pass criteria requires explicit sign-off from both Member 1 (Product) and Member 4 (Evaluation).
