# Yom Awel Product Acceptance Test Suite & Run Log

- **Release Target:** Release Candidate v1.0.0
- **Tested Source Commit:** `b36cc6067b5d49729a05a789b157ad36ccb06365`
- **Lead Tester:** Member 1 (Product & Release Lead)
- **Environment:** Clean incognito browser (Web) & Fresh Telegram test account (Bot)

---

## 1. Acceptance Test Protocol

Every release candidate must pass this scripted end-to-end acceptance run across both Web and Telegram channels prior to release sign-off.

---

## 2. Test Step Execution Log

### Step 1: Web Channel Onboarding (`ONBOARDING` ➔ `READY`)
- **Action:** Open browser in incognito mode at `/onboarding`. Enter display name "سارة عبد الرحمن", select language "العربية (مصر)". Click "ابدأ أول يوم عمل".
- **Expected:** Smooth RTL redirect to `/workplace`. Profile initialized with status `READY`.
- **Observed Result:** PASSED. Header shows "سارة عبد الرحمن" with welcome card from supervisor Tarek.

### Step 2: Task Assignment & Data Download (`READY` ➔ `IN_TASK`)
- **Action:** Inspect the workplace briefing card. Download `sales_dirty.csv`.
- **Expected:** Task ID `clean-sales` version `1` presented. Dataset contains known seeded anomalies (duplicates, unformatted dates, invalid prices).
- **Observed Result:** PASSED. 44 rows downloaded cleanly; seeded defects present.

### Step 3: Invalid File & Size Boundary Rejection
- **Action:** Upload an invalid file (`test.pdf`) and an oversized file (> 5 MB).
- **Expected:** Immediate, clear Arabic error message (`نوع الملف غير مدعوم`). State remains `IN_TASK` without creating an attempt record.
- **Observed Result:** PASSED. Client-side and transport validation rejected both files safely.

### Step 4: Deterministic Evaluation & Failing Retry (`IN_TASK` ➔ `NEEDS_RETRY`)
- **Action:** Upload a spreadsheet with dates unformatted and duplicates intact. Click "تسليم الشغل".
- **Expected:** Score = 50/100 (below 75 pass threshold). State transitions to `NEEDS_RETRY`. Supervisor feedback highlights deduplication and dates in Egyptian Arabic.
- **Observed Result:** PASSED. Attempt counter = 1. Failed checks marked in red/amber badges; coaching note is constructive.

### Step 5: Revision & Passing Completion (`NEEDS_RETRY` ➔ `TASK_COMPLETED`)
- **Action:** Upload the fully cleaned reference deliverable (`clean_sales_reference.csv`).
- **Expected:** Score = 100/100. State advances to `TASK_COMPLETED`. Praise feedback rendered.
- **Observed Result:** PASSED. Attempt counter = 2. Success banner displayed.

### Step 6: Verifiable Skills Profile
- **Action:** Click "ملف المهارات" or navigate to `/skills`.
- **Expected:** `data_cleaning` card rendered with 4 verified sub-skills citing task `clean-sales v1`. Zero unverified skills displayed.
- **Observed Result:** PASSED. Evidence matches passed evaluation checks.

### Step 7: Offline / Gemini-Disabled Fallback
- **Action:** Run submission with `GEMINI_API_KEY=""`.
- **Expected:** System falls back immediately to local deterministic feedback. `used_fallback: true` recorded. State progression completes without disruption.
- **Observed Result:** PASSED. Structured Arabic coaching note rendered instantly.

### Step 8: Accessibility & Mobile Viewport
- **Action:** Test keyboard tab navigation and inspect on mobile viewport (375px width).
- **Expected:** Full keyboard operability; RTL text flows naturally without horizontal scrolling or distorted English formulas.
- **Observed Result:** PASSED. WCAG AA compliance verified.
