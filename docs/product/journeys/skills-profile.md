# Learner Journey: Verifiable Skills Profile

- **Journey ID:** `journey-skills-profile`
- **Feature Status:** `current`

---

## 1. Overview

| Attribute | Specification |
|---|---|
| **Actor** | Learner, Recruiter, or Evaluator reviewing learner capabilities |
| **Channels** | Web Application (`/skills`) & Telegram Bot (`/profile` command) |
| **Primary Goal** | Display an authentic, auditable competency profile derived strictly from verified deterministic evaluation checks, without arbitrary progress percentages or fabricated skills. |
| **Preconditions** | 1. Learner has completed onboarding.<br>2. (Optional) Learner has submitted at least one task resulting in passing evaluation evidence. |

---

## 2. Invariants & Proof Principles

1. **Evidence-Backed Skills Only:**
   - Every skill point displayed must correspond to an immutable row in `skill_evidence` tied to an actual `evaluation_check_id` on an accepted submission.
   - The system never displays fabricated progress or vanity metrics.

2. **Skill Projection Independence:**
   - The skills profile is a read projection generated on-demand by the application service (`BuildSkillsProfileUseCase`), aggregating historical passed checks.

3. **Bilingual Clarity:**
   - Skill names and competencies have canonical English industry terms alongside clear Egyptian Arabic explanations (e.g., "تنظيف البيانات — Data Cleaning").

---

## 3. Numbered Normal Flow

1. **Profile Access:**
   - **Web:** Learner clicks "ملف المهارات" (Skills Profile) in the top navigation bar or follows the post-task completion prompt to `/skills`.
   - **Telegram:** Learner sends `/profile` or clicks the inline button "عرض مهاراتي".

2. **Evidence Aggregation (Application Service):**
   - The service queries all passed evaluation checks for the learner across completed tasks.
   - For task `clean-sales` (v1), the following 4 competencies are aggregated under `data_cleaning`:
     - **إزالة التكرار (Deduplication):** Evidenced by check `unique_orders` (25 pts).
     - **توحيد صيغ التواريخ (Date Normalization):** Evidenced by check `standard_dates` (25 pts).
     - **التحقق من القيم الرقمية (Numeric Validation & Formulas):** Evidenced by check `valid_numeric_values` (25 pts).
     - **معالجة القيم المفقودة (Handling Missing Data):** Evidenced by check `complete_customer_records` (25 pts).

3. **Profile Presentation:**
   - The page displays:
     - **Learner Identity:** Display name and join date.
     - **Summary Counters:** Completed tasks count (e.g. "1 تكليف مكتمل"), verified skills count ("1 مهارة رئيسية").
     - **Competency Cards:** Each card displays:
       - Competency title in Arabic & English.
       - Level indicator based on verified evidence count (e.g. "مستوى مبتدئ متقن — Junior Proficient").
       - Detailed checklist of specific skills verified, citing the exact task (`clean-sales@1`) and completion timestamp.
     - **Auditable Evidence Link:** Clean, shareable evidence summary showing the exact date, task version, and evaluation checks satisfied.

---

## 4. Alternative States & Edge Cases

- **Fresh Account with Zero Tasks (Empty State):**
  - If a learner navigates to `/skills` immediately after onboarding before completing any task:
    - The page renders a helpful, warm empty state in Egyptian Arabic:
      > "لسه مفيش مهارات مسجلة هنا. لما تخلّص أول تكليف عملي بنجاح، مهاراتك هتنزل هنا بالدليل العملي عشان تقدر تشاركها مع الشركات."
    - A direct primary CTA button points to: "ابدأ أول تكليف عملي" (Go to Active Task).

- **Partial Task Completion (In-Progress / Retry):**
  - If a learner has an active task in `NEEDS_RETRY` or `IN_TASK`, failed attempts do **not** contribute to verified competencies. The profile clearly indicates that verification requires task completion.

---

## 5. Completion Evidence & Visible Outcome

- **Completion Evidence:**
  - Query to `GET /api/learners/{id}/skills` returns an array of `SkillSummary` objects matching `contracts/schemas/skill-summary.json`.
- **Visible Outcome:**
  - Clear visual badges representing each evidenced skill.
  - A downloadable or shareable summary for prospective employers proving realistic task completion.

---

## 6. Accessibility & Language Standards

- **Semantic Markup:** Skills are presented in accessible semantic lists (`<ul>` and `<li>`) with appropriate ARIA roles.
- **RTL Alignment:** Cards, icons, and text align natively to the right in Arabic view, with English acronyms (CSV, ISO, SQL) flowing cleanly without visual distortion.
- **High Contrast:** All badge text complies with WCAG AA 4.5:1 minimum contrast ratio.

---

## 7. Analytics-Free Verification Procedure

1. Verify empty state: Navigate to `/skills` with a new user; confirm empty state message and CTA button render correctly.
2. Complete `clean-sales` task with a passing submission.
3. Refresh `/skills`; confirm `data_cleaning` card appears.
4. Verify the 4 sub-skills are checked and tagged with task `clean-sales v1`.

---

## 8. Cross-Lane Ownership Handoffs

- **Member 2 (Domain & Persistence):** Provides `skill_definitions`, `skill_evidence` repository, and `BuildSkillsProfileUseCase`.
- **Member 4 (Evaluation):** Supplies stable `skill_id` mappings on all evaluation checks.
- **Member 5 (Web & Transport):** Implements `/skills` page in Next.js and `/profile` response in Telegram bot.
