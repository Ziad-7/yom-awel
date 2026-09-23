# Yom Awel — Official Video Demo Script (Primary Flow)

- **Total Duration:** 3 Minutes (180 Seconds)
- **Presenter:** Member 1 (Lead Presenter)
- **Target Audience:** Hackathon Judges & Educational Evaluators
- **Environment:** Production Vercel Preview (Incognito Browser)

<!-- claim: claim-cap-web-experience -->
<!-- claim: claim-cap-deterministic-eval -->
<!-- claim: claim-cap-arabic-feedback -->
<!-- claim: claim-cap-skills-projection -->

---

## Timeline & Scene Breakdown

### Scene 1: The Problem & Onboarding (0:00 – 0:35)
- **Speaker:** "مرحباً بكم في يوم أول (Yom Awel). المشكلة اللي بنحلها هي الفجوة الكبيرة بين الدراسة الأكاديمية والمهارات المطلوبة فعلياً في سوق العمل المصري في وظائف البيانات والعمليات."
- **Screen Action:**
  - Browser opens to `/onboarding`.
  - Enter name: "أحمد ممدوح" (Ahmed Mamdouh), language set to `ar-EG`.
  - Click "ابدأ أول يوم عمل".
- **Expected Visual State:** Seamless RTL transition to the workplace dashboard. Welcome card introduces Nile Distribution Co. and supervisor Tarek.

### Scene 2: Task Assignment & Data Hygiene Challenge (0:35 – 1:10)
- **Speaker:** "المتدرب هنا مش بيشوف كورس نظري، المتدرب استلم أول تكليف عملي من مشرفه أستاذ طارق في شركة النيل للتوزيع: تنظيف ملف مبيعات يومي حقيقي فيه تكرار وتواريخ وأسعار غير منضبطة."
- **Screen Action:**
  - Show workplace briefing card with the 4 clear objectives.
  - Download `sales_dirty.csv`. Open briefly to show the seeded errors (duplicate rows, inverted dates, negative prices).

### Scene 3: Artifact Upload & First Evaluation (1:10 – 1:50)
- **Speaker:** "المتدرب صلح الملف ورفعه. دلوقتي النظام بيفحص الشغل بطريقة فريدة: التقييم حتمي برمجي 100% بدون أي فتي أو هلوسة من الذكاء الاصطناعي."
- **Screen Action:**
  - Drag and drop corrected file into the upload zone.
  - Click "تسليم الشغل".
  - Show loading indicator (`aria-live="polite"`).

### Scene 4: Supervisor AI Coaching & Feedback (1:50 – 2:25)
- **Speaker:** "النتيجة طلعت: الدرجة 100 من 100 في كل المعايير! والمشرف بيكلمه باللهجة المصرية الدافئة بيشرح له إيه اللي اتعمل صح ويشجعه."
- **Screen Action:**
  - Highlight the 4 green passing badges (Deduplication, Dates, Numeric Integrity, Missing Records).
  - Highlight the Egyptian Arabic coaching note from supervisor Tarek.

### Scene 5: Verifiable Skills Profile & Wrap-Up (2:25 – 3:00)
- **Speaker:** "أهم ميزة: المهارات مش مجرد نسب وهمية؛ كل مهارة في صفحة ملف المهارات مبنية على دليل رقمي موثق من التكليف اللي أنجزه، جاهزة للمشاركة مع الشركات."
- **Screen Action:**
  - Navigate to `/skills`.
  - Show the verified `data_cleaning` card with 4 sub-skills tied to `clean-sales v1`.
  - Final closing slide with repository link.

---

## Contingency & Recovery Lines
- **If network latency delays evaluation:** Presenter notes: "النظام بيعمل فحص أمني دقيق للتأكد من بنية الملف وسلامة الأعمدة قبل تأكيد النتيجة."
- **If Gemini free tier hits rate limits:** Presenter seamlessly transitions: "لاحظوا هنا إن النظام مصمم لضمان الاستمرارية التامة؛ لو خدمة الذكاء الاصطناعي واجهت ضغط، نظام الملاحظات المحلي الاحتياطي بيشتغل فوراً بدون أي توقف."
