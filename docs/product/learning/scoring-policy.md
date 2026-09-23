# Yom Awel Scoring & Pass Policy

- **Policy Version:** 1.0.0
- **Governing Task:** `clean-sales` (v1)
- **Owners:** Member 1 (Learning Design) & Member 4 (Deterministic Evaluation)

---

## 1. Principles of Deterministic Evaluation

1. **Zero Hallucination Grading:**
   All scoring decisions are computed purely using deterministic Python logic (`pandas`, `openpyxl`) in the evaluation service. Large Language Models (Gemini) are strictly prohibited from calculating or modifying scores.
2. **Predictable Pass Threshold:**
   Tasks specify a clear numerical pass threshold (default: 75 out of 100 points). Learners meeting or exceeding the threshold advance in the curriculum; learners scoring below transition to `NEEDS_RETRY`.
3. **Critical Checks & Hard Stops:**
   Certain baseline requirements are designated as critical prerequisites (e.g. valid file structure, non-empty data, presence of required column headers). A failure in structural integrity halts evaluation and yields an automatic failure, regardless of other checks.

---

## 2. Clean-Sales (v1) Point Allocation

The standard evaluation budget is 100 points, distributed equally across four core data quality dimensions:

| Check ID | Point Weight | Competency | Pass Requirement |
|---|:---:|---|---|
| `unique_orders` | 25 pts | Deduplication | Exactly one record per unique `order_id`. Zero duplicate keys remain. |
| `standard_dates` | 25 pts | Type Normalization | All values in `order_date` conform to ISO format `YYYY-MM-DD`. |
| `valid_numeric_values` | 25 pts | Numeric Validation | Zero negative `quantity` or `unit_price`; `revenue` matches `quantity * unit_price` (tolerance: ±0.01). |
| `complete_customer_records` | 25 pts | Missing Data Handling | Every missing customer email is documented with `"unavailable"` in `missing_email_reason`. |
| **Total** | **100 pts** | | **Pass Threshold: 75 pts** |

---

## 3. Threshold and Progression Logic

- **Score >= 75 points:**
  - Status: `PASSED`.
  - Learner state: transitions to `TASK_COMPLETED`.
  - Skill evidence: rows committed to `skill_evidence` for every individual check that passed.
  - Progression: unlocked for subsequent tasks.

- **Score < 75 points:**
  - Status: `FAILED`.
  - Learner state: transitions to `NEEDS_RETRY`.
  - Feedback: supervisor highlights areas needing attention based on failed check hints.
  - Attempt: attempt counter increments; previous attempts remain immutable in audit logs.

---

## 4. Change Control & Governance

- Neither Member 1 nor Member 4 may alter points, checks, thresholds, or validation tolerances unilaterally.
- Any change to check weights or pass thresholds requires:
  1. A joint GitHub Pull Request review and approval by both Member 1 and Member 4.
  2. A version bump on the task package (e.g. `clean-sales` version `2`).
  3. Re-running the baseline regression tests on historical benchmark fixtures to ensure backward compatibility.
