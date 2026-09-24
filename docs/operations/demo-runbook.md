# Live demo runbook / دليل العرض المباشر

- **Length:** 3 minutes, plus 2 minutes of questions.
- **Files:** `demo/files/` (see [the presenter kit](../../demo/README.md)). Every score quoted here
  is asserted against the real evaluator by `tools/quality/tests/test_demo_kit.py`.
- **Run it on:** the deployed web app if its preview is verified, otherwise the local run
  (`demo/run_local.sh`).

## How the local run is wired / التشغيل المحلي متوصل إزاي

`demo/run_local.sh` starts the API on `127.0.0.1:${API_PORT:-8000}` with `APP_ENV=local` and the
web app on `127.0.0.1:${WEB_PORT:-3000}` with `API_ORIGIN=http://127.0.0.1:${API_PORT}`.
`API_ORIGIN` is a server-only variable read by the Next.js `/api` rewrite; the browser calls only
relative `/api/v1/...` URLs on the web origin. `NEXT_PUBLIC_API_BASE_URL` is no longer used. For a
deployed web app, set `API_ORIGIN` to the deployed API origin in the web project's server
environment. The script waits for three health checks: the API directly, the web app, and
`/api/v1/health` through the web proxy.

السكريبت بيشغّل الـ API والموقع، والموقع بيوصل للـ API عن طريق `API_ORIGIN` من السيرفر بس، والمتصفح
بيكلم `/api/v1` على نفس الموقع.

## Before the demo (T-30 min) / قبل العرض

1. Open the app in a fresh private window. Confirm `GET /api/v1/runtime` reports the expected
   `feedback_provider` (`gemini` or `deterministic`).
2. Put the five files from `demo/files/` on the desktop, in beat order.
3. Do one full dry run in the language you will present in. Delete nothing afterwards: the demo
   uses a new anonymous session each time.
4. Have the fallback video open in a second tab (see Fallback plan).

## Script (English) / النص بالإنجليزي

| Time | Beat | Say | Do |
|---|---|---|---|
| 0:00-0:25 | Problem | "Graduates know the concepts but have never cleaned a real messy file. Yom Awel is their first day at a simulated Egyptian company." | Show the landing page, choose English, enter a name. |
| 0:25-0:50 | The task | "Tarek, the supervisor, gives a real assignment: a sales file with duplicates, bad dates, negative numbers and missing emails." | Open clean-sales, show the brief, download the CSV. Open it for five seconds. |
| 0:50-1:30 | The critical rule | "Our learner fixed three problems but left the duplicates. That is 75 points, which looks like a pass. It is not: duplicate orders are critical." | Upload `sales_retry_duplicates.csv`. Point at 75/100, the failed `unique_orders` check, and Tarek's feedback. |
| 1:30-2:10 | Success | "Grades come from deterministic code, never from the AI. The AI only explains. Same result from Excel or CSV." | Upload `sales_cleaned.xlsx`. Point at 100/100, four passed checks, progress now completed. |
| 2:10-2:40 | Bilingual | "Everything works in Egyptian Arabic, including the feedback." | Switch the language to Arabic; show the same result with Arabic feedback. |
| 2:40-3:00 | Close | "Deterministic grading, bilingual coaching with an offline fallback, secrets never in the code. Thank you." | Show the progress view. |

## النص بالعربي

| الوقت | اللحظة | تقول | تعمل |
|---|---|---|---|
| 0:00-0:25 | المشكلة | "الخريج بيفهم المفاهيم بس عمره ما نضف ملف حقيقي ملخبط. يوم أول هو أول يوم شغل ليه في شركة مصرية افتراضية." | افتح الصفحة الرئيسية، اختار العربي، واكتب اسم. |
| 0:25-0:50 | المهمة | "أستاذ طارق المشرف بيدي تكليف حقيقي: ملف مبيعات فيه تكرار وتواريخ غلط وأرقام بالسالب وإيميلات ناقصة." | افتح مهمة تنظيف المبيعات، اعرض التكليف، ونزّل ملف CSV وافتحه خمس ثواني. |
| 0:50-1:30 | القاعدة الحرجة | "المتدرب صلح تلات مشاكل وساب التكرار. ده 75 نقطة وشكلها نجاح، بس لأ: تكرار الطلبات فحص حرج." | ارفع `sales_retry_duplicates.csv`. شاور على 75 من 100 وفحص `unique_orders` اللي فشل وتعليق طارق. |
| 1:30-2:10 | النجاح | "الدرجة بيحطها كود ثابت، مش الذكاء الاصطناعي. الذكاء الاصطناعي بيشرح بس. ونفس النتيجة من Excel أو CSV." | ارفع `sales_cleaned.xlsx`. شاور على 100 من 100 والأربع فحوصات والتقدم اللي اكتمل. |
| 2:10-2:40 | لغتين | "كل حاجة شغالة بالإنجليزي كمان، حتى التعليق." | غيّر اللغة للإنجليزي واعرض نفس النتيجة. |
| 2:40-3:00 | الختام | "تصحيح ثابت، تعليق بلغتين مع بديل من غير إنترنت، ومفيش أسرار في الكود. شكراً." | اعرض صفحة التقدم. |

## Optional beats for questions / لحظات إضافية للأسئلة

- "What if the file is broken?" Upload `sales_rejected_missing_columns.csv`: rejected with
  `missing_columns`, no check runs.
- "Is 50 a pass?" Upload `sales_retry_half.xlsx`: 50/100, retry, with `standard_dates` and
  `complete_customer_records` failed.

## Fallback plan / الخطة البديلة

Apply the first step that fixes the problem; do not debug on stage.

1. **Gemini slow, failing or over quota.** Set `FEEDBACK_MODE=fallback` on the API and restart it
   (locally: add `FEEDBACK_MODE=fallback` to `.env` and rerun `demo/run_local.sh`). Feedback then
   comes from the deterministic Tarek templates. Grades are unaffected, because feedback never
   sets the grade.
   لو Gemini بطيء أو واقف: `FEEDBACK_MODE=fallback` وأعد تشغيل الـ API. الدرجات مابتتأثرش.
2. **Deployed app unreachable.** Switch to the local run: `demo/run_local.sh`, then open
   `http://127.0.0.1:3000`. It needs no internet except for Gemini, and falls back to
   deterministic feedback when no key is set.
   لو الموقع واقع: شغّل `demo/run_local.sh` على اللابتوب.
3. **Laptop or network unusable.** Play the recorded demo video produced by the web lane.
   لو مفيش حل: شغّل الفيديو المسجل.

Status of each fallback on the day of writing:

| Fallback | Status |
|---|---|
| `FEEDBACK_MODE=fallback` switch | Pending: the switch is part of the API lane; not yet verified end to end |
| Local run | Pending: `demo/run_local.sh` depends on the web app and API transport (PR #22) |
| Recorded video | Pending: to be produced by the web lane and linked here |

## Known limitations / حدود معروفة

- One task only: `clean-sales` version 1.
- Uploads: `.csv` and single-sheet `.xlsx`, at most 5 MiB and 10,000 rows. Macros, password
  protected and multi-sheet workbooks are rejected.
- Sessions are anonymous; there is no account recovery. A new private window is a new learner.
- Gemini quality and latency depend on the free-tier quota; the deterministic fallback is always
  available and never changes the grade.
- Telegram is not part of the demo.
- The Arabic dataset download is the same data as the English one; column names stay in English
  because the evaluator requires them.
