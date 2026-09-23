# Learner Journey: First Task Onboarding and Completion

- **Journey ID:** `journey-first-task`
- **Target Task:** `clean-sales` (v1)
- **Feature Status:** `current` (Architecture and core contracts merged; interface integration under PR)

---

## 1. Overview

| Attribute | Specification |
|---|---|
| **Actor** | Entry-level Egyptian digital/data job seeker (Learner) |
| **Channels** | Web Application (`apps/web/`) & Telegram Bot (`@yom_awel_bot`) |
| **Primary Goal** | Onboard into the simulated Egyptian workplace, accept the dirty sales spreadsheet cleaning assignment, submit a cleaned file, receive deterministic evaluation and Arabic coaching, and advance progress. |
| **Preconditions** | 1. Learner visits the Web app or starts the Telegram bot with `/start`.<br>2. Learner has no previous completion history (`ONBOARDING` lifecycle state).<br>3. Task package `clean-sales` v1 is active in the repository catalog. |

---

## 2. State Machine Transitions

```
[Unregistered]
      │
      ▼ (Onboard with display name & language: ar-EG)
  ONBOARDING ──► READY
      │
      ▼ (Assign clean-sales task)
   IN_TASK
      │
      ▼ (Upload artifact & submit with idempotency key)
  PROCESSING
      │
      ▼ (Deterministic score >= 75)
TASK_COMPLETED ──► READY (or PROGRAM_COMPLETED)
```

---

## 3. Numbered Normal Flow (Happy Path)

1. **Channel Entry & Profile Creation (`ONBOARDING` ➔ `READY`):**
   - **Web:** Learner navigates to `/onboarding`, enters their name (e.g., "أحمد ممدوح"), chooses preferred language (`ar-EG`), and clicks "ابدأ أول يوم عمل" (Start First Workday).
   - **Telegram:** Learner sends `/start`. Bot welcomes them warmly in Egyptian Arabic and asks for their name.
   - An external identity mapping (`web` or `telegram`) and a domain `Learner` record are created.
   - State advances to `READY`.

2. **Task Assignment (`READY` ➔ `IN_TASK`):**
   - System assigns task `clean-sales` version `1`.
   - Learner sees the simulated workplace workplace context: A supervisor assignment from *شركة النيل للتوزيع* requesting data cleanup of the daily sales transactions file.
   - Learner downloads `sales_dirty.csv` (or `.xlsx`) deliverable template.
   - Instructions outline the 4 required business objectives:
     1. Remove duplicate order IDs (`unique_orders`).
     2. Standardize dates to `YYYY-MM-DD` (`standard_dates`).
     3. Fix negative quantities/prices and calculate revenue accurately (`valid_numeric_values`).
     4. Annotate missing customer emails with "unavailable" in `missing_email_reason` (`complete_customer_records`).
   - State advances to `IN_TASK`.

3. **Artifact Preparation & Submission (`IN_TASK` ➔ `PROCESSING`):**
   - Learner cleans the dataset using Excel, Google Sheets, or LibreOffice.
   - Learner requests private upload authorization. System returns a secure signed upload URL (Supabase Storage / local adapter).
   - Learner uploads the cleaned file (`sales_cleaned.csv` or `.xlsx`, under 5 MB).
   - Web/Telegram sends the artifact ID and a UUIDv4 idempotency key to `POST /api/submissions`.
   - System reserves the submission in an atomic transaction; state becomes `PROCESSING`.

4. **Deterministic Evaluation & AI Coaching:**
   - Evaluator (`sales-cleaning` v1) executes deterministic checks:
     - All 4 checks pass (25 points each = 100/100 points, exceeding the 75-point pass threshold).
   - AI Feedback service generates pedagogical coaching in Egyptian Arabic using Gemini free tier (or deterministic fallback if provider is unavailable).
   - Feedback tone is authentic, encouraging, and explains why the work was professional without revealing hidden test internals.

5. **Completion and Progression (`PROCESSING` ➔ `TASK_COMPLETED`):**
   - Atomic CAS finalization persists the `EvaluationResult`, `FeedbackResult`, `Attempt` record, and domain skill evidence.
   - Learner status updates to `TASK_COMPLETED`.
   - Skills profile updates: competency `data_cleaning` increments with verified evidence tags.
   - Web UI / Telegram presents the passing grade, supervisor coaching note, and a button to view their updated Skills Profile.

---

## 4. Failure and Alternative Paths

- **File Validation Rejection (Client/Transport Level):**
  - If learner uploads an unsupported format (e.g. `.pdf` or `.exe`) or a file exceeding 5 MB (5,242,880 bytes), the request is rejected immediately with an informative Arabic error: `نوع الملف غير مدعوم` or `حجم الملف يتعدى الحد الأقصى (5 ميجابايت)`.
  - No attempt is created; state remains `IN_TASK`.

- **Deterministic Evaluation Failure (Score < 75):**
  - If the learner submits incomplete work (e.g. forgot date normalization), the evaluator calculates the score (e.g. 50/100).
  - Learner state transitions to `NEEDS_RETRY`.
  - Feedback highlights specific guidance points without exposing exact cell values or answers.
  - See [Learner Retry Journey](learner-retry.md) for the recovery sequence.

- **External Provider Outage (Gemini Offline / Rate-Limited):**
  - System automatically switches to the deterministic Arabic template fallback (`used_fallback: true`).
  - Learner receives clear, structured Arabic feedback based strictly on the evaluation check outputs.
  - Progression is unaffected because LLMs never control pass/fail.

- **Transient Transport / Database Failure:**
  - Network interruption during submission does not corrupt state. The client retries with the same idempotency key; the API returns `202 Accepted` while evaluating, or returns the cached outcome once completed.

---

## 5. Completion Evidence & Visible Outcome

- **Completion Evidence:**
  - A committed row in `evaluation_results` with `passed = true` and `score >= 75`.
  - An immutable row in `attempts` linked to `task_version_id` and `submission_id`.
  - Updated `skill_evidence` linked to check IDs (`unique_orders`, `standard_dates`, etc.).
  - `learner_progress.state` set to `TASK_COMPLETED`.
- **Visible Outcome:**
  - Clear success banner in Egyptian Arabic ("تسلم إيدك يا بطل! الشغل مظبوط").
  - Breakdown of points earned per check.
  - Constructive supervisor feedback.
  - Navigational link to view the updated Skills Profile.

---

## 6. Accessibility & Language Standards

- **Language:** Egyptian Arabic (`ar-EG`) is the default primary language with culturally natural phrasing.
- **Direction:** Full Right-to-Left (RTL) layout support; numbers and technical terms render cleanly without bidirectional punctuation bleed.
- **Accessibility:**
  - Keyboard operable tab flow for file selection and submission buttons.
  - Screen reader announcements (`aria-live="polite"`) for submission progress and evaluation results.
  - Color contrast satisfies WCAG AA standards (success/error states convey information via icons and text, not color alone).

---

## 7. Analytics-Free Verification Procedure

To verify this journey without external tracking tools:
1. Open an incognito browser window at `/onboarding`.
2. Enter a test name and register.
3. Verify the assigned task is `clean-sales` and download the sample dataset.
4. Upload `tests/evaluation/fixtures/clean_sales_reference.csv` (the known passing fixture).
5. Submit the task.
6. Verify response within 5 seconds: score = 100, pass banner rendered, Egyptian Arabic feedback present.
7. Navigate to `/skills` and confirm the `data_cleaning` skill reflects 100% mastery with 4 evidence items.

---

## 8. Cross-Lane Ownership Handoffs

- **Member 2 (Domain & Persistence):** Provides `Learner`, `Submission`, `Attempt`, and `LearnerProgress` persistence, idempotency reservation, and CAS finalization.
- **Member 3 (AI Feedback):** Delivers persona-driven Egyptian Arabic feedback prompt and deterministic fallback templates.
- **Member 4 (Evaluation):** Provides `sales-cleaning` evaluator, boundary validation, and check points.
- **Member 5 (Web & Transport):** Delivers Next.js onboarding & workplace pages, Telegram webhook, and upload dialogs.
