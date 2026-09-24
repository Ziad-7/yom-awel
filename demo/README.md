# Presenter kit / عدة العرض

Five ready-made uploads for the clean-sales task, each derived from the learner's own dirty file
(`task_packages/clean-sales/1/data/sales_dirty.csv`, seed `20260920`). Every file is graded by the
real `sales-cleaning@1` evaluator in `tools/quality/tests/test_demo_kit.py`, so the scores below are
tested facts, not expectations.

خمس ملفات جاهزة للرفع في مهمة تنظيف المبيعات، كلها مبنية من نفس الملف الخام اللي المتدرب بينزله.
كل ملف بيتصحح بالمقيّم الحقيقي في الاختبار `tools/quality/tests/test_demo_kit.py`، يعني الدرجات اللي
تحت دي متختبرة فعلاً.

## Which file for which beat / أنهي ملف في أنهي لحظة

| Beat | File (`demo/files/`) | Score | Result | What the audience sees |
|---|---|---|---|---|
| 1. The raw file | download `sales_dirty.csv` from the task page | 0 | retry | All four checks fail: 10 duplicate rows, 4 bad dates, 3 bad numbers, 4 missing email reasons |
| 2. Wrong file shape | `sales_rejected_missing_columns.csv` | 0 | rejected, `missing_columns` | The learner deleted `missing_email_reason`. The file is refused before grading; no check runs |
| 3. The critical rule | `sales_retry_duplicates.csv` | 75 | retry | Three checks pass, but `unique_orders` is critical, so 75 is still a retry. 10 rows to fix |
| 4. Half done, in Excel | `sales_retry_half.xlsx` | 50 | retry | Duplicates and numbers fixed; dates (4 rows) and missing email reasons (4 rows) not |
| 5. Success (CSV) | `sales_cleaned.csv` | 100 | pass | All four checks pass; progress moves to completed |
| 5. Success (Excel) | `sales_cleaned.xlsx` | 100 | pass | Same result from a typed Excel workbook: format does not change the grade |

| اللحظة | الملف | الدرجة | النتيجة | الجمهور بيشوف إيه |
|---|---|---|---|---|
| ١. الملف الخام | نزّل `sales_dirty.csv` من صفحة المهمة | 0 | إعادة | الأربع فحوصات بتفشل: 10 صفوف مكررة، 4 تواريخ غلط، 3 أرقام غلط، 4 إيميلات من غير سبب |
| ٢. شكل الملف غلط | `sales_rejected_missing_columns.csv` | 0 | مرفوض `missing_columns` | المتدرب مسح عمود `missing_email_reason`، فالملف اترفض قبل التصحيح |
| ٣. القاعدة الحرجة | `sales_retry_duplicates.csv` | 75 | إعادة | تلات فحوصات نجحت، بس `unique_orders` فحص حرج، فـ 75 برضه إعادة |
| ٤. نص الشغل في Excel | `sales_retry_half.xlsx` | 50 | إعادة | التكرار والأرقام اتصلحوا، التواريخ (4) وأسباب الإيميل (4) لأ |
| ٥. نجاح (CSV) | `sales_cleaned.csv` | 100 | ناجح | الأربع فحوصات نجحت والتقدم بيتحدث |
| ٥. نجاح (Excel) | `sales_cleaned.xlsx` | 100 | ناجح | نفس النتيجة من ملف Excel: الصيغة مابتغيرش الدرجة |

Recommended order for a 3-minute demo: beat 3 (the critical rule is the memorable moment), then
beat 5. Use beats 2 and 4 only if time allows or a judge asks about rejection or Excel.

الترتيب المقترح لعرض 3 دقايق: اللحظة ٣ (القاعدة الحرجة هي اللي بتفضل في الذاكرة)، وبعدها اللحظة ٥.
استخدم ٢ و٤ لو فيه وقت أو لو حد من الحكام سأل عن الرفض أو Excel.

## What is scored / التصحيح بيتم إزاي

- Four checks, 25 points each: `unique_orders` (critical), `standard_dates`,
  `valid_numeric_values`, `complete_customer_records`.
- Pass rule: score >= 75 **and** `unique_orders` passed.
- The grade is deterministic. Tarek's feedback (Gemini or the deterministic fallback) explains the
  grade; it never changes it.

- أربع فحوصات، كل واحد 25 نقطة، و`unique_orders` فحص حرج.
- شرط النجاح: 75 أو أكتر **و** نجاح `unique_orders`.
- الدرجة ثابتة ومحددة بالكود. تعليق أستاذ طارق بيشرح الدرجة ومابيغيرهاش.

## Regenerate / إعادة التوليد

```bash
uv run --project services/api python demo/generate_demo_files.py
uv run --project services/api pytest tools/quality/tests/test_demo_kit.py
```

The output is byte-for-byte reproducible (fixed workbook properties and zip timestamps); the test
fails if a committed file drifts from a fresh regeneration.

## Run the demo locally / تشغيل العرض محلياً

See `demo/run_local.sh` and [the demo runbook](../docs/operations/demo-runbook.md).
