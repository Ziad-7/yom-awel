# Yom Awel Scoring & Pass Policy

- **Policy Version:** 1.0.0
- **Governing Task:** `clean-sales` (v1)
- **Owners:** Member 1 (Learning Design) & Member 4 (Deterministic Evaluation)
- **Status:** Frozen for Task Package v1 publication

---

## 1. Principles of Deterministic Evaluation

1. **Zero Hallucination Grading:**
   All scoring decisions are computed purely using deterministic Python logic (`pandas`, `openpyxl`) in the evaluation service. Large Language Models (Gemini) are strictly prohibited from calculating or modifying scores.
2. **Unified Pass Rule:**
   $$\text{passed} = (\text{score} \ge 75) \land (\forall c \in \text{critical\_checks}: c.\text{passed} = \text{true})$$
   A submission **passes if and only if** its total score meets or exceeds 75 out of 100 points **AND** every critical check passes.
3. **Critical Checks & Hard Stops:**
   The check `unique_orders` is designated as **critical** (`critical: true`). 
   - **Learner & Product Rationale:** Order deduplication is the foundational primary key integrity requirement in retail and distribution analytics. Duplicate order identifiers inflate sales transaction volume, produce double-counted revenue summaries, and cause duplicated warehouse dispatch in downstream business workflows. Even if a learner achieves 75 points by correctly standardizing dates, auditing numeric calculations, and documenting missing emails, retaining duplicate order entries constitutes a fatal data corruption defect. Therefore, a failure in `unique_orders` automatically results in `passed = false` regardless of total points.
4. **Format Parity (CSV & XLSX):**
   Task `clean-sales` v1 supports both **CSV** and **XLSX** formats with identical evaluation semantics:
   - Evaluator accepts either format, inspects tabular content from the first active worksheet, and applies identical grading logic.
   - Bounded XLSX constraints: file size <= 5 MiB (`5,242,880` bytes), single sheet evaluated, max 10,000 rows, max 20 columns, no macros, no password encryption.
   - Evaluator returns identical scores, check breakdowns, and diagnostics for valid CSV and XLSX submissions representing the same data.

---

## 2. Clean-Sales (v1) Check Allocation & Weights

The standard evaluation budget is 100 points, distributed equally across four canonical checks (25 points each):

| Check ID | Point Weight | Critical? | Competency | Deterministic Pass Requirement |
|---|:---:|:---:|---|---|
| `unique_orders` | 25 pts | **YES** | Deduplication & Business Key Integrity | Exactly one record per unique `order_id`. Zero duplicate or empty order keys. |
| `standard_dates` | 25 pts | No | Type Normalization | All values in `order_date` conform strictly to ISO 8601 `YYYY-MM-DD`. |
| `valid_numeric_values` | 25 pts | No | Numeric Validation & Integrity | Zero negative `quantity` or `unit_price`; `revenue` matches `quantity * unit_price` (tolerance: ±0.01). |
| `complete_customer_records` | 25 pts | No | Missing Data Handling | Every transaction lacking customer email retains its sales row with `"unavailable"` in `missing_email_reason`. |
| **Total** | **100 pts** | | | **Pass Rule: Score >= 75 AND all critical checks passed** |

---

## 3. Finite Versioned Diagnostic Vocabulary (v1)

To protect the boundary between deterministic evaluation (Member 4) and pedagogical coaching (Member 3), the evaluator emits only finite, versioned diagnostic codes. Evaluators **never leak ground-truth answers, hidden benchmark rows, or internal grader fixtures**.

### 3.1 Pre-Evaluation Rejections (Execution / Ingestion Errors)

Emitted when the submitted file fails baseline ingestion or boundary validation before grading:

| Rejection Code | Category | Learner-Visible Meaning | Retryable? |
|---|---|---|:---:|
| `unsupported_type` | Validation | File extension or MIME signature is not a supported CSV or XLSX spreadsheet. | Yes |
| `file_too_large` | Validation | File size exceeds the 5 MiB limit. | Yes |
| `corrupt_or_unreadable` | Validation | File cannot be parsed as a tabular spreadsheet (e.g. invalid encoding, macro workbook, encrypted). | Yes |
| `missing_columns` | Validation | One or more required column headers are missing from the header row. | Yes |
| `duplicate_columns` | Validation | Header row contains duplicate column names. | Yes |
| `too_few_rows` | Validation | Cleaned dataset has fewer than the required 40 rows. Rows were improperly dropped. | Yes |

### 3.2 Evaluation Checks and Diagnostic Codes

For each of the 4 graded checks, the evaluator produces an `EvaluationCheck` record containing a structured diagnostic code and learner-safe guidance:

| Check ID | Diagnostic Code | Learner-Visible Diagnostic Meaning (Safe Guidance) |
|---|---|---|
| `unique_orders` | `unique_orders_passed` | All order IDs are unique and valid. Primary key integrity satisfied. |
| `unique_orders` | `unique_orders_failed` | Duplicate or empty order IDs detected. Re-examine repeated orders and preserve exactly one record per order ID. |
| `standard_dates` | `standard_dates_passed` | All transaction dates conform to ISO 8601 (`YYYY-MM-DD`). |
| `standard_dates` | `standard_dates_failed` | Non-standard date formats detected. Standardize all dates to `YYYY-MM-DD`. |
| `valid_numeric_values` | `valid_numeric_values_passed` | All numeric quantities and prices are positive, and revenue calculations match. |
| `valid_numeric_values` | `valid_numeric_values_failed` | Negative quantities/prices or revenue calculation mismatches detected. Check formulas (`quantity * unit_price`). |
| `complete_customer_records` | `complete_customer_records_passed` | All missing customer contacts correctly annotated with `"unavailable"` without dropping transactions. |
| `complete_customer_records` | `complete_customer_records_failed` | Missing customer records dropped or unannotated. Fill `missing_email_reason` with `"unavailable"`. |

---

## 4. Threshold, Progression, and Retry Logic

- **Passed Condition:**
  $$\text{score} \ge 75 \quad \text{AND} \quad \text{unique\_orders.passed} = \text{true}$$
  - Evaluator sets `passed: true`.
  - Learner state: transitions to `TASK_COMPLETED`.
  - Skill evidence: records created for each individual check that passed.
  - Progression: unlocks subsequent tasks.

- **Needs Retry Condition:**
  $$\text{score} < 75 \quad \text{OR} \quad \text{unique\_orders.passed} = \text{false}$$
  - Evaluator sets `passed: false`.
  - Learner state: transitions to `NEEDS_RETRY`.
  - Pedagogical feedback: Egyptian Arabic coaching highlights failed check diagnostic guidance without spoiling answers.
  - Attempt tracking: attempt count increments; past attempts and evaluation snapshots are immutable.

---

## 5. Member 4 Handoff Acceptance Criteria

Member 4 accepts this scoring contract when the evaluation test suite implements and proves:
1. **Critical Check Enforcement:** A test proves that a submission scoring 75 points with `unique_orders` failed produces `EvaluationResult(passed=False, score=75)`.
2. **Format Equivalence:** A test proves that identical tabular data submitted in `.csv` and `.xlsx` formats receives identical scores, check breakdowns, and diagnostics.
3. **Diagnostic Integrity:** All emitted diagnostic codes conform strictly to the finite vocabulary in Section 3 and survive the Member 3 feedback translation boundary without alteration.
4. **Content Pinning:** Evaluator validates task package assets against reviewed SHA-256 hashes before grading and refuses unpinned or modified draft packages.

