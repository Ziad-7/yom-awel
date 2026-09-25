# Yom Awel (يوم أول) — Competition Application

---

### Box 1: Thematic Challenge (choose one)
**Assessment Revolution**  
*(Alternative track: AI Tutor)*

*Why:* We replace multiple-choice quizzes and attendance certificates with authentic workplace task evaluation. Crucially, we keep grading in deterministic code so it is 100% objective and cheat-proof, while using Generative AI strictly for personalized coaching.

---

### Box 2: Problem Statement
*What specific education problem are you addressing, and who experiences it?*

Fresh graduates in Egypt struggle to get entry-level jobs because employers want practical experience that universities and courses don't provide. Courses teach theory and test memorization through multiple-choice quizzes, but students never get to practice real job workflows—like cleaning corrupted sales spreadsheets, writing SQL queries to answer business questions, or drafting professional customer emails.

At the same time, platforms that try using AI to grade student assignments run into serious problems: LLMs hallucinate scores, can be tricked by prompt injection, and give inconsistent grades. Students are left without safe, realistic workplace practice or credible proof of their skills.

---

### Box 3: Target User / Beneficiary
*students, teachers, parents, institutions…etc*

* **Primary users:** Egyptian university students, fresh graduates, and career switchers preparing for entry-level digital, operations, and data roles.
* **Educators and universities:** Can assign realistic workplace simulations to students without having to manually grade hundreds of messy files.
* **Employers:** Gain verifiable proof of what a candidate can actually do on real tasks, rather than relying on self-reported resumes and course completion certificates.

---

### Box 4: Evidence / Validation So Far
*What evidence do you currently have that this problem is real? (interviews, observations, surveys, existing data, early testing)*

1. **Labor Market Evidence:** 2024–2025 reports by the International Labour Organization (ILO) and CAPMAS (Egypt's central statistics agency) highlight a severe gap between university education and the practical digital skills Egyptian employers require.
2. **Working Technical Proof:** We built an extensible simulation engine and proved it end-to-end with 3 pilot workplace tasks (spreadsheet cleaning, SQL reporting, and client email) running across both a modern web app and a Telegram bot.
3. **Automated Verification:** Over 940 automated tests and 14 end-to-end browser journeys verify that submissions are graded consistently, securely, and without AI grading hallucinations.
4. **Validation Boundary:** We have proven the technical foundation, security, and grading reliability. Our next step is a classroom pilot with Egyptian university students to measure confidence and skill gains before and after the simulation.

---

### Box 5: Solution Overview
*Briefly describe how your proposed solution addresses the problem.*

Yom Awel ("First Day") turns learning into a simulated first day on the job at an Egyptian company.

1. **The Brief:** A virtual supervisor named Tarek hands the learner a realistic workplace assignment in Arabic.
2. **The Work:** The learner downloads real files, does the work in standard tools (Excel, SQL, or a text editor), and submits their actual file via our website or Telegram bot.
3. **Objective Grading:** A deterministic Python evaluator checks the file against clear business rules (e.g., verifying duplicate rows are removed, dates are standardized, and calculations are accurate). Grades are instant, reproducible, and immune to AI hallucinations.
4. **AI Coaching:** Generative AI acts as supervisor Tarek, explaining mistakes and giving actionable advice in warm, professional Egyptian Arabic.
5. **Skills Profile:** Every passed check adds auditable evidence to the learner’s profile, proving what they can actually do.

---

### Box 6: How is Generative AI Used?
*Explain the specific role of Generative AI in your solution and why it is necessary.*

Generative AI (Google Gemini) acts strictly as a **workplace supervisor and coach**—not the grading authority.

* **Why it is necessary:** Standard code can only return dry error codes like "Row 14 invalid", which frustrates learners. Gemini translates technical errors into supportive, conversational coaching in authentic Egyptian Arabic (e.g., *"Great job on the dates, but you missed duplicate order YA-102. If we keep that, we'll double-bill the client—take another look and resubmit!"*). This delivers 1-on-1 mentorship at scale without requiring human instructors to hand-grade every file.
* **Why it must NOT grade:** Scores, pass/fail decisions, and progression are handled strictly by deterministic code. This eliminates grading hallucinations, bias, and prompt-injection attacks. A built-in offline fallback ensures the platform stays functional even if the AI API is temporarily unavailable.

---

### Box 7: Current Development Stage (choose one)
**Working prototype / MVP**

The platform is fully functional and deployed live on Vercel and Supabase Postgres. Both the web application and Telegram bot are live, supporting 3 complete workplace tasks, bilingual coaching, and over 940 passing quality tests.
