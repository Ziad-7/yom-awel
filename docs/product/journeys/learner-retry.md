# Learner Journey: Task Failure, Coaching, and Retry

- **Journey ID:** `journey-learner-retry`
- **Target Task:** `clean-sales` (v1)
- **Feature Status:** `current`

---

## 1. Overview

| Attribute | Specification |
|---|---|
| **Actor** | Entry-level Egyptian digital/data job seeker (Learner) |
| **Channels** | Web Application (`apps/web/`) & Telegram Bot (`@yom_awel_bot`) |
| **Primary Goal** | Guide a learner whose submission did not meet the passing rule (score below 75 or any critical check failed) through actionable Egyptian Arabic feedback, allow them to revise their spreadsheet, submit a retry attempt, and achieve passing completion without state corruption. |
| **Preconditions** | 1. Learner has an active assignment in task `clean-sales`.<br>2. Learner previously submitted an artifact that failed one or more deterministic checks.<br>3. Learner lifecycle state is currently `NEEDS_RETRY`. |

---

## 2. State Machine Transitions

```
   IN_TASK
      │
      ▼ (Submit attempt #1 with defects)
  PROCESSING
      │
      ▼ (Score < 75 OR any critical check failed)
 NEEDS_RETRY
      │
      ▼ (Review feedback, upload corrected file, submit attempt #2)
  PROCESSING
      │
      ▼ (Score >= 75 AND every critical check passed)
TASK_COMPLETED
```

---

## 3. Numbered Normal Flow

1. **Evaluation Result and Feedback Presentation (`PROCESSING` ➔ `NEEDS_RETRY`):**
   - The deterministic evaluator completes run for Attempt #1. Score is below 75 (e.g., 50/100 because dates were not standardized and duplicate orders were retained).
   - The state transitions to `NEEDS_RETRY`.
   - The learner sees a clear breakdown:
     - Passed checks highlighted with green badges (e.g., `valid_numeric_values: 25/25`, `complete_customer_records: 25/25`).
     - Failed checks highlighted with retry badges (e.g., `unique_orders: 0/25`, `standard_dates: 0/25`).
   - Supervisor persona (أستاذ طارق) provides encouraging, actionable Egyptian Arabic coaching:
     > "بداية كويسة جداً في مراجعة الأسعار والإيرادات! بس خد بالك: لسه في طلبات متكررة في الملف محتاجة تتفلتر ونسيب نسخة واحدة بس من كل رقم طلب. كمان صيغ التواريخ مش موحدة، محتاجين نخليها كلها بصيغة YYYY-MM-DD. راجع النقطتين دول وارفع الملف تاني."
   - The advice points out the concepts to fix without giving away exact row numbers or expected cell values.

2. **Artifact Correction & Preparation:**
   - The learner reviews their working spreadsheet locally (or re-downloads the original dataset if they prefer a fresh start).
   - Learner filters duplicate `order_id` values and keeps unique records.
   - Learner reformats `order_date` column to ISO format `YYYY-MM-DD`.

3. **Re-Submission (`NEEDS_RETRY` ➔ `PROCESSING`):**
   - Learner clicks "إعادة إرسال الملف" (Submit Revision).
   - Learner requests a new private upload authorization.
   - Learner uploads the corrected file (`sales_cleaned_v2.xlsx` or `.csv`).
   - Client sends the new `artifact_id` and a fresh `idempotency_key` (UUIDv4) to `POST /api/submissions`.
   - The domain service verifies learner state is `NEEDS_RETRY`, reserves the submission, increments the attempt counter (`attempt_number = 2`), and transitions state to `PROCESSING`.

4. **Re-Evaluation and Success (`PROCESSING` ➔ `TASK_COMPLETED`):**
   - Evaluator runs all checks against Attempt #2. All 4 checks pass: Score = 100/100.
   - AI Feedback generates an updated praise response in Egyptian Arabic acknowledging the learner's effort in fixing previous mistakes.
   - Domain updates `attempts` with attempt #2 as successful.
   - Learner state advances to `TASK_COMPLETED`.
   - Learner's skills profile is credited with `data_cleaning` competencies.

---

## 4. Anti-Frustration & Integrity Rules

- **Deterministic Primacy:**
  - AI feedback cannot override a failing score. Even if the feedback is encouraging, the state remains `NEEDS_RETRY` until the evaluator approves the file.
- **Answer Security (No Spoilers):**
  - Hints and feedback explain the business rule (e.g. "التواريخ محتاجة توحيد"), but never print the specific ground-truth answer strings or coordinates (e.g. "غير الصف رقم 14").
- **Attempt History Preservation:**
  - Previous attempts are never overwritten or deleted. Both Attempt #1 and Attempt #2 remain immutable in the `attempts` table for learning progress auditability.
- **Idempotency Protection:**
  - If the learner double-clicks "إعادة إرسال", the duplicate request shares the same idempotency key and returns the same in-flight or completed attempt rather than creating an extraneous Attempt #3.

---

## 5. Failure & Edge Cases

- **Repeated Failure (Attempt #2 Also Fails):**
  - If the corrected file still scores below 75 or fails a critical check, state remains `NEEDS_RETRY`.
  - The supervisor feedback offers an additional progressive hint (e.g. referencing Excel date format options).
  - Attempt counter increments to #3 on next submission.
  - Learners are not permanently locked out.

- **Corrupted or Unreadable Upload on Retry:**
  - If the revised file has invalid encoding or corrupted sheets, the evaluator produces an `EvaluationError`.
  - Learner receives an immediate safe message: "الملف المرفوع غير قابل للقراءة، برجاء حفظه كملف Excel أو CSV سليم والمحاولة مرة أخرى."
  - No progression penalty is applied; state remains `NEEDS_RETRY`.

---

## 6. Completion Evidence & Visible Outcome

- **Completion Evidence:**
  - `attempts` table contains multiple records for the learner and task, with the latest record having `evaluation.passed == true`.
  - `learner_progress.state` transitioned from `NEEDS_RETRY` to `TASK_COMPLETED`.
  - `outbox_events` logs both the initial failure event and subsequent completion event.
- **Visible Outcome:**
  - Learner sees both attempts in their submission history.
  - Success message specifically celebrating the improvement ("عاش يا بطل! تم تعديل الأخطاء بنجاح والتسليم اتقبل").

---

## 7. Accessibility & Language Standards

- **RTL & Visual Structure:** Failed checks are clearly distinguished with red/amber badges and text labels, not relying solely on color.
- **Focus Management:** On returning to `NEEDS_RETRY`, focus shifts automatically to the feedback summary card.
- **Clarity of Instructions:** The re-upload button has an accessible label `إعادة رفع ملف التكليف بعد التعديل`.

---

## 8. Analytics-Free Verification Procedure

1. Onboard a fresh test learner.
2. Submit an intentionally defective artifact (e.g. `tests/evaluation/fixtures/clean_sales_dirty.csv` or missing dates).
3. Confirm score is < 75 and UI shows state `NEEDS_RETRY`.
4. Inspect Arabic feedback to confirm it notes the specific defect politely.
5. Upload the passing fixture (`clean_sales_reference.csv`).
6. Submit with a fresh idempotency key.
7. Confirm attempt counter is 2, score is 100, and final state is `TASK_COMPLETED`.

---

## 9. Cross-Lane Ownership Handoffs

- **Member 2 (Domain & Persistence):** Manages attempt incrementing, `NEEDS_RETRY` transitions, and transaction isolation.
- **Member 3 (AI Feedback):** Generates progressive coaching acknowledging prior errors in retry context.
- **Member 4 (Evaluation):** Re-runs identical pure evaluation logic with versioned check reporting.
- **Member 5 (Web & Transport):** Renders retry dashboard, check badges, and upload file dropper.
