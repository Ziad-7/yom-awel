# Yom Awel: Video Demo Script (Primary Flow)

- **Total Duration:** 3 minutes (180 seconds)
- **Presenter:** Member 1 (Lead Presenter)
- **Audience:** Hackathon judges and educational evaluators
- **Environment:** a fresh private browser window on the verified deployment, or the local run
  (`demo/run_local.sh`). Do not record until the web flow is verified end to end (claim
  `claim-cap-web-experience` is pending).
- **Uploads:** `demo/files/` (see `demo/README.md`). Every score below is asserted against the
  real evaluator by `tools/quality/tests/test_demo_kit.py`.
- **Live version with both languages and timings:** `docs/operations/demo-runbook.md`.

<!-- claim: claim-cap-web-experience -->
<!-- claim: claim-cap-deterministic-eval -->
<!-- claim: claim-cap-arabic-feedback -->
<!-- claim: claim-cap-demo-kit -->

---

## Timeline & Scene Breakdown

### Scene 1: The problem and onboarding (0:00-0:30)
- **Speaker:** "مرحباً بكم في يوم أول. الخريج بيفهم المفاهيم، بس عمره ما نضف ملف شغل حقيقي ملخبط. يوم أول هو أول يوم شغل ليه في شركة مصرية افتراضية."
- **Screen:** open the app, choose Arabic, enter a display name.
- **Expected:** the task list in Arabic (right to left) showing clean-sales as available.

### Scene 2: The assignment (0:30-0:55)
- **Speaker:** "أستاذ طارق المشرف بيدي أول تكليف: ملف مبيعات فيه طلبات مكررة وتواريخ بأشكال مختلفة وأرقام بالسالب وإيميلات ناقصة."
- **Screen:** start clean-sales, show the brief, download the CSV and open it for a few seconds.

### Scene 3: The critical rule (0:55-1:40)
- **Speaker:** "المتدرب صلح التواريخ والأرقام والإيميلات، بس ساب التكرار. ده 75 نقطة، وشكلها نجاح، بس الفحص ده حرج: من غير ما التكرار يتشال مفيش نجاح."
- **Screen:** upload `demo/files/sales_retry_duplicates.csv`.
- **Expected:** 75/100, not passed, only `unique_orders` failed (10 rows to fix), Tarek's feedback
  in Arabic, status retry.

### Scene 4: Success, from Excel (1:40-2:25)
- **Speaker:** "الدرجة بيحطها كود ثابت ومتختبر، مش الذكاء الاصطناعي. الذكاء الاصطناعي بيشرح بس. ونفس النتيجة سواء الملف CSV أو Excel."
- **Screen:** upload `demo/files/sales_cleaned.xlsx`.
- **Expected:** 100/100, four passed checks, progress shows the task completed.

### Scene 5: Bilingual and wrap-up (2:25-3:00)
- **Speaker:** "وكل ده متاح بالإنجليزي كمان. تصحيح ثابت، تعليق بلغتين، ومفيش أسرار في الكود."
- **Screen:** switch the language to English and show the result and feedback in English. Close
  with the repository link.

---

## Recovery Lines
- **If evaluation is slow:** "النظام بيفحص شكل الملف وأمانه الأول قبل ما يصحح."
- **If Gemini is unavailable:** follow `submission/demo-contingency.md`. The grade does not
  depend on Gemini.
