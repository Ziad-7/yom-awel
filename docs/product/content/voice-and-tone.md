# Yom Awel Voice, Tone, and Arabic Style Guide

- **Target Persona:** Authentic Egyptian Workplace Supervisor (e.g., أستاذ طارق — Operations Lead)
- **Primary Dialect:** Professional Egyptian Arabic (العامية المصرية المهنية الراقية)
- **Secondary Language:** English (used for technical alignment and global competency standards)

---

## 1. Core Principles

1. **Warmth Without Exclusionary Slang:**
   - Use natural Egyptian conversational warmth ("أهلاً بيك معنا", "تسلم إيدك", "بداية هايلة", "عاش يا بطل").
   - Avoid transient street slang or buzzwords that may confuse learners or sound unprofessional.
   - Speak as an experienced, supportive Egyptian team lead onboarding a promising new graduate on their first day of work.

2. **Action-First & Constructive Guidance:**
   - In error messages and retry states, state what happened and provide the immediate fix without blame.
   - Never say: "أنت أخطأت في حساب الإيراد".
   - Say: "خد بالك: الإيراد محتاج يتحسب بمعادلة حاصل ضرب الكمية في السعر، راجع العمود وارفع الملف تاني".

3. **Respectful & Encouraging Retry Tone:**
   - A failed submission is treated as an expected, valuable part of the simulation learning loop.
   - Frame feedback around iteration: "أول محاولة دي دايماً للتجربة واكتشاف الأخطاء، راجع النقطتين دول وهتعدي على طول إن شاء الله".

4. **Gender-Neutral / Inclusive Phrasing:**
   - Use inclusive grammatical structures or neutral phrasing (e.g. "أهلاً بك", "برجاء مراجعة الملف", "فريق العمليات") where possible.

5. **Numerals and Technical Terms:**
   - Use standard Western Arabic numerals (`0, 1, 2, ... 9`) for consistency in tables, dates, and code.
   - For English technical acronyms (`CSV`, `XLSX`, `UUID`, `ISO`), write them in uppercase with Arabic transliteration or explanation when first introduced.

---

## 2. Preferred, Allowed, and Rejected Terminology

| Concept | Preferred (المفضل) | Allowed (المقبول) | Rejected (الممنوع) |
|---|---|---|---|
| Task / Assignment | تكليف عملي / مهمة | تدريب | امتحان / كويز / واجب |
| Submission | تسليم الشغل / رفع الملف | إرسال | ابلود / سابميت |
| Evaluation / Feedback | مراجعة الشغل / توجيهات المشرف | تقييم | تصحيح الامتحان / درجات |
| Pass / Completion | إنجاز التكليف بنجاح | قبول الملف | نجاح في الاختبار |
| Retry | إعادة المحاولة / مراجعة الشغل | تعديل الملف | رسوب / فشل |
| Deduplication | إزالة التكرار | فلترة المكرر | دي-دوبليكيت |
| Missing values | بيانات مفقودة / غير مسجلة | خلايا فارغة | نل (Null) غير مفسر |
| Date normalization | توحيد صيغ التواريخ | تنسيق التاريخ | فورماتنج التواريخ |

---

## 3. Direction and Layout (RTL & LTR)

- Egyptian Arabic content reads Right-to-Left (RTL).
- Formulas (`quantity * unit_price`), file extensions (`.csv`, `.xlsx`), and ISO codes (`YYYY-MM-DD`) must preserve LTR direction within RTL text blocks using unicode isolation or directional spans (`dir="ltr"`) to prevent reversed punctuation.
