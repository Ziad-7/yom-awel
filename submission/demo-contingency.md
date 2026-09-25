# Yom Awel: Contingency Demo Script (Gemini Disabled)

- **Purpose:** show that grading and progress do not depend on the AI provider.
- **Presenter:** Member 1 (Lead Presenter)
- **Pre-condition:** the API runs with `FEEDBACK_MODE=fallback`, or with no `GEMINI_API_KEY`.
  `GET /api/v1/runtime` then reports `"feedback_provider": "deterministic"`.
- **Status:** pending. The feedback fallback is unit-tested on `main`; the switch through the
  API and the browser has not yet been verified end to end (claim `claim-cap-arabic-feedback`).

<!-- claim: claim-cap-arabic-feedback -->
<!-- claim: claim-cap-deterministic-eval -->
<!-- claim: claim-cap-retry-handling -->
<!-- claim: claim-cap-demo-kit -->

---

## Timeline & Execution

### 1. Show the provider is off (0:00-0:30)
- **Speaker:** "لو الإنترنت وقع أو حصة الذكاء الاصطناعي المجانية خلصت، التصحيح مايقفش، لأنه أصلاً مش معتمد على الذكاء الاصطناعي."
- **Screen:** show the runtime response with `feedback_provider: deterministic`.

### 2. A retry with fallback feedback (0:30-1:15)
- **Speaker:** "المتدرب صلح نص الشغل بس. الدرجة 50 وده إعادة، وطارق بيشرح من القوالب الثابتة بالعامية المصرية."
- **Screen:** upload `demo/files/sales_retry_half.xlsx`.
- **Expected:** 50/100, not passed, `standard_dates` and `complete_customer_records` failed, Tarek's
  feedback from the deterministic templates.

### 3. Retry and completion (1:15-2:00)
- **Speaker:** "المتدرب يقدر يصلح ويسلم تاني من غير ما يخسر المحاولة الأولى."
- **Screen:** upload `demo/files/sales_cleaned.csv`.
- **Expected:** 100/100, passed, the task shows as completed, and the attempt history lists both
  attempts.

If any expected state does not appear, stop and record a failed release gate rather than claiming
uninterrupted service.
