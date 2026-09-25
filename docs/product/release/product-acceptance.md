# Yom Awel Product Acceptance Protocol

- **Release Target:** Release Candidate v1.0.0
- **Governing Tasks:** `clean-sales`, `sql-report`, and `client-email` (v1)
- **Owners:** Member 1 (Lead), with Member 4 (Evaluator) and Member 5 (Web Experience)
- **Status:** local automated journeys exist; final hosted three-task execution must be recorded in release sign-off.

---

## 1. Overview

The acceptance run follows the demo flow in the web app, once in Arabic (`ar-EG`) and once in
English (`en`). For clean-sales, upload CSV in one run and XLSX in the other. Uploads come from `demo/files/`;
their scores are already asserted against the real evaluator by
`tools/quality/tests/test_demo_kit.py`, so any different score in the browser is an integration
defect, not an evaluator change. Telegram is out of scope for this release.

## 2. Steps

### Step 1: Session and onboarding (`ONBOARDING` to `READY`)
- **Action:** open the app in a private window, choose a language, enter a display name.
- **Expected:** an anonymous session cookie is set (HttpOnly, SameSite=Lax); the learner is
  `READY`; the task list shows all three published tasks as available with pass threshold 75.

### Step 2: Start the task and download (`READY` to `IN_TASK`)
- **Action:** start clean-sales, read the brief and hints, download the dataset as CSV and as XLSX.
- **Expected:** the brief matches the pinned `content/brief.<lang>.md`; the CSV equals
  `task_packages/clean-sales/1/data/sales_dirty.csv`.

### Step 3: Rejection
- **Action:** upload `demo/files/sales_rejected_missing_columns.csv`.
- **Expected:** rejected with `missing_columns`, bilingual reason, no check marked as passed.

### Step 4: Critical-check retry (`IN_TASK` to `NEEDS_RETRY`)
- **Action:** upload `demo/files/sales_retry_duplicates.csv`.
- **Expected:** 75/100, `passed=false`, only `unique_orders` failed; Tarek's feedback in the
  learner's language; status retry.

### Step 5: Partial retry
- **Action:** upload `demo/files/sales_retry_half.xlsx`.
- **Expected:** 50/100, `passed=false`, `standard_dates` and `complete_customer_records` failed.

### Step 6: Pass (`NEEDS_RETRY` to `TASK_COMPLETED`)
- **Action:** upload `demo/files/sales_cleaned.csv` (or `sales_cleaned.xlsx` in the other run).
- **Expected:** 100/100, `passed=true`; the task shows completed; the attempt history lists every
  attempt with its `submission_id`.

### Step 7: Language switch
- **Action:** switch the language; reopen the last submission.
- **Expected:** feedback for the stored evaluation in the new language; the score is unchanged.

### Step 8: Feedback fallback
- **Action:** restart the API with `FEEDBACK_MODE=fallback`; repeat Step 4.
- **Expected:** `GET /api/v1/runtime` reports `feedback_provider: deterministic`; the same score,
  with deterministic Tarek feedback.

### Step 9: Accessibility and mobile (375 px)
- **Action:** run the flow by keyboard only and at 375 px width.
- **Expected:** full keyboard operability, visible focus, no horizontal overflow, correct `dir`
  for each language.

### Step 10: SQL report, retry, and pass
- **Action:** open `sql-report`, download its source CSV, submit `DROP TABLE sales` in the SQL
  editor, then submit the reference query from `task_packages/sql-report/1/examples/pass.sql`.
- **Expected:** the unsafe statement receives zero points with a specific rejection message; the
  read-only query scores 100, passes all four checks, and marks SQL reporting complete. A query
  with hard-coded rows that merely reads `sales` as a no-op must not pass.

### Step 11: Customer email, retry, and pass
- **Action:** open `client-email`, download its case CSV, submit
  `task_packages/client-email/1/examples/fail.en.txt` (or the Arabic equivalent), then the
  matching `pass.<language>.txt` example. Also try a message that says the refund or response
  will **not** happen.
- **Expected:** the incomplete or negated message needs revision and explains the missing action;
  the complete message scores 100 and passes. A denied refund or response cannot pass even at
  75 points because the action plan check is mandatory.

### Step 12: Cross-task persistence
- **Action:** switch among the three tasks, open each attempt from Skills & progress, then reload.
- **Expected:** all task statuses, per-task scores, and feedback remain attached to the correct
  task. Reopening a completed task keeps its own result. No late result may change another task's
  status.
