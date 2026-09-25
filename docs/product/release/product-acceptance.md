# Yom Awel Product Acceptance Protocol

- **Release Target:** Release Candidate v1.0.0
- **Governing Task:** `clean-sales` (v1)
- **Owners:** Member 1 (Lead), with Member 4 (Evaluator) and Member 5 (Web Experience)
- **Status:** protocol updated to the demo flow; execution pending the web app (PR #22) and its
  wiring to the real evaluator

---

## 1. Overview

The acceptance run follows the demo flow in the web app, once in Arabic (`ar-EG`) and once in
English (`en`), uploading CSV in one run and XLSX in the other. Uploads come from `demo/files/`;
their scores are already asserted against the real evaluator by
`tools/quality/tests/test_demo_kit.py`, so any different score in the browser is an integration
defect, not an evaluator change. Telegram is out of scope for this release.

## 2. Steps

### Step 1: Session and onboarding (`ONBOARDING` to `READY`)
- **Action:** open the app in a private window, choose a language, enter a display name.
- **Expected:** an anonymous session cookie is set (HttpOnly, SameSite=Lax); the learner is
  `READY`; the task list shows `clean-sales` as available with pass threshold 75.

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
