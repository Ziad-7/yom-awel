# Yom Awel Product Acceptance Protocol & Verification Script

- **Release Target:** Release Candidate v1.0.0
- **Governing Task:** `clean-sales` (v1)
- **Owners:** Member 1 (Lead), with Member 4 (Evaluator) & Member 5 (Web Experience)
- **Status:** Protocol frozen; execution pending Member 4 & 5 branch integration

---

## 1. Acceptance Protocol Overview

This document specifies the exact 8-step scripted end-to-end acceptance run across Web (`apps/web`) and Telegram (`@yom_awel_bot`) channels. It must be executed against the integrated deployment once Member 4 (evaluator) and Member 5 (web experience) PRs are merged to `main`.

---

## 2. Scripted Acceptance Test Steps

### Step 1: Web Channel Onboarding (`ONBOARDING` ➔ `READY`)
- **Route:** `/onboarding`
- **Action:** Open browser in incognito mode at `/onboarding`. Enter display name "نور الدين", select language "العربية (مصر)". Click "ابدأ أول يوم عمل".
- **Expected Outcome:** Smooth RTL redirect to `/workplace`. Profile initialized with status `READY`. Header displays "نور الدين" with welcome card from supervisor Tarek. Copy ID: `state.empty`.

### Step 2: Task Assignment & Data Download (`READY` ➔ `IN_TASK`)
- **Route:** `/workplace`
- **Action:** Inspect the workplace briefing card. Download `sales_dirty.csv`.
- **Expected Outcome:** Task ID `clean-sales` version `1` presented with 4 business objectives. Dataset contains known seeded anomalies (duplicates, unformatted dates, invalid prices). State: `IN_TASK`.

### Step 3: Boundary & Rejection Verification
- **Route:** `/workplace`
- **Action:** Upload an invalid file (`test.pdf`) and an oversized file (> 5 MiB).
- **Expected Outcome:** Immediate, accessible Arabic error banner with `aria-describedby` (Copy IDs: `upload.invalid_type`, `upload.oversize`). State remains `IN_TASK` without creating an attempt record.

### Step 4: Deterministic Evaluation & Failing Retry (`IN_TASK` ➔ `NEEDS_RETRY`)
- **Route:** `/workplace`
- **Action:** Upload dirty or partially cleaned spreadsheet (e.g., duplicate order IDs intact). Click "سلّم للمراجعة".
- **Expected Outcome:** Score = 50/100 (below 75 pass threshold, or `unique_orders` critical failure). State transitions to `NEEDS_RETRY`. Focus shifts to `#result-heading`. Supervisor feedback in Egyptian Arabic highlights deduplication. Copy IDs: `evaluation.failure`, `evaluation.retry`. Attempt counter = 1.

### Step 5: Revision & Passing Completion (`NEEDS_RETRY` ➔ `TASK_COMPLETED`)
- **Route:** `/workplace`
- **Action:** Upload the fully cleaned reference deliverable (`clean_sales_reference.csv`).
- **Expected Outcome:** Score = 100/100, critical check passed. State advances to `TASK_COMPLETED`. Green success banner rendered (Copy ID: `evaluation.success`). Attempt counter = 2.

### Step 6: Verifiable Skills Profile Projection
- **Route:** `/skills`
- **Action:** Click "عرض ملف المهارات" or navigate to `/skills`.
- **Expected Outcome:** `data_cleaning` competency card rendered with 4 verified sub-skills citing task `clean-sales@1` and completion timestamp. Zero unverified skills displayed. Copy ID: `profile.empty` only if 0 tasks completed.

### Step 7: Deterministic Local Fallback Contingency
- **Route:** `/workplace`
- **Action:** Run submission with `GEMINI_API_KEY=""` or simulated provider timeout.
- **Expected Outcome:** System falls back immediately to local deterministic Arabic feedback (`used_fallback: true`). Structured Egyptian Arabic coaching note rendered instantly (Copy ID: `feedback.gemini_fallback`). Progression is uninterrupted.

### Step 8: Accessibility & Mobile Viewport (375 px)
- **Viewport:** 375 px width (iPhone SE standard)
- **Action:** Navigate entire flow via keyboard (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`) and test on small mobile screen.
- **Expected Outcome:** Full keyboard operability, visible 2px focus outlines, zero horizontal overflow, minimum 44x44px touch targets.

