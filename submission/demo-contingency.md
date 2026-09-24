# Yom Awel — Contingency Demo Script (Offline / Gemini-Disabled Fallback)

- **Purpose:** Planned acceptance script for deterministic Egyptian Arabic fallback when external AI APIs are blocked, disabled, or rate-limited.
- **Presenter:** Member 1 (Lead Presenter)
- **Pre-Condition:** Gemini API key unset or mocked offline mode enabled (`GEMINI_API_KEY=""`).

<!-- claim: claim-cap-arabic-feedback -->
<!-- claim: claim-cap-deterministic-eval -->
<!-- claim: claim-cap-retry-handling -->

---

## Scenario Overview

Run this script only after the integrated release candidate passes it. Until then, it specifies expected behavior rather than claiming verified availability.

---

## Timeline & Execution

### 1. Offline Mode Demonstration (0:00 – 0:45)
- **Speaker:** "في سيناريو انقطاع الإنترنت الخارجي أو نفاد حصة نماذج الذكاء الاصطناعي المجانية، Yom Awel لا يتوقف أبداً عن تقديم تجربة تعليمية كاملة."
- **Screen Action:**
  - Show system logs or environment panel indicating `used_fallback: true`.
  - Confirm whether the learner can access `/workplace`; record failure as a failed release gate.

### 2. Evaluator Execution & Deterministic Fallback Notice (0:45 – 1:30)
- **Speaker:** "التقييم الحتمي البرمجي يعمل محلياً بنسبة 100%. التلميحات والتوجيهات تظهر للمتدرب بالعامية المصرية المنضبطة من محرك الملاحظات الاحتياطي المحلي."
- **Screen Action:**
  - Submit test workbook with incomplete date formatting.
  - Evaluation produces score (e.g. 75/100).
  - Supervisor card renders local template coaching note with fallback indicator badge:
    > "تم توليد هذه التوجيهات باستخدام النظام الآلي المباشر لضمان استمرار الخدمة دون انقطاع."

### 3. Retry and Progression Continuity (1:30 – 2:15)
- **Speaker:** "المتدرب يستطيع تصحيح الخطأ فوراً وإعادة التسليم دون فقدان أي سجلات، ونظام التقدم يواصل العمل بثبات تام."
- **Screen Action:**
  - Submit corrected workbook.
  - Final score reaches 100/100.
  - Verify that state advances to `TASK_COMPLETED` only when the threshold and critical-check gate pass.
  - Verify that the competency profile updates; retain evidence for release sign-off.
