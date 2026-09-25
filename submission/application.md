# Yom Awel (يوم أول) — Competition Application

---

### Box 1: Thematic Challenge
**Assessment Revolution**  
*(Alternative track: AI Tutor)*

---

### Box 2: Problem Statement
Many Egyptian university students and early-career job seekers face an "experience paradox": they understand technical concepts from online courses and university lectures, but have never rehearsed the practical, messy workflows required on Day 1 of a real job (e.g., standardizing corrupted dates, removing duplicate transaction records, querying sales databases, or handling client escalations). 

Existing digital learning platforms fail them in two critical ways:
1. **The Language and Cultural Disconnect:** Almost all technical training datasets and exercises are in English and detached from local workplace realities.
2. **The LLM Grading Fallacy:** Many emerging EdTech platforms use Generative AI to directly score student work, leading to hallucinations, non-reproducible grades, and security vulnerabilities (prompt injection). Meanwhile, traditional courses rely on multiple-choice quizzes that test passive recall instead of applied capability.

---

### Box 3: Target User / Beneficiary
* **Primary Users:** Egyptian university students, fresh graduates, and career switchers preparing for entry-level digital, data, and operational roles.
* **Secondary Beneficiaries:**
  * **Educators & Training Academies:** Can assign authentic practical tasks and receive auditable, granular evidence of competencies without manually grading hundreds of spreadsheets.
  * **Employers & Recruiters:** Gain verified proof of demonstrated task execution rather than trusting self-reported course completion certificates.

---

### Box 4: Evidence / Validation So Far
* **Labor Market Evidence:** The skills gap is documented by authoritative national and regional data:
  * **ILO & CAPMAS (2024):** *Analytical report: Labour demand and labour market skills needs in Egypt* highlights acute shortages in applied digital and data competencies.
  * **ILO (2024):** *Skills mapping in Egypt: Opportunity scouting and skills mapping analysis* details high youth underemployment driven by training-to-job mismatch.
  * **ILO (2025):** *Skills dynamics in the Arab region* emphasizes the urgent need for training that reduces the gap between education and online vacancy demands.
* **Technical Validation:**
  * **946+ automated tests** verifying deterministic evaluation, state-machine progression, bilingual feedback generation, and replay safety.
  * **14 Playwright E2E browser tests** validating full learner journeys, keyboard navigation, WCAG AA accessibility, and mobile RTL responsiveness.
  * **Production Deployment:** Live on Vercel with managed Postgres and Google Gemini, alongside a production Telegram bot interface.
* **Validation Boundary:** We have validated technical reproducibility, security, and end-to-end task mechanics. Live user satisfaction and post-simulation learning gains will be measured in our upcoming university student pilot.

---

### Box 5: Solution Overview
**Yom Awel ("First Day")** transforms digital skills training into a simulated first day at work in an Egyptian enterprise (*شركة النيل للتوزيع والتجارة*).

Instead of watching passive videos, the learner receives a business brief and dataset from their virtual supervisor (**أستاذ طارق**), completes the work using everyday workplace tools (Excel, LibreOffice, SQL editor, or text editor), and submits their actual artifact through either a modern web app or Telegram.

A transparent, deterministic evaluator checks the submission against rigorous task specifications across three playable tracks:
1. **`clean-sales`:** Removing duplicate orders, formatting ISO dates, validating positive numeric revenue, and handling missing emails.
2. **`sql-report`:** Writing aggregated SQL queries to compute paid regional revenue and order counts.
3. **`client-email`:** Drafting professional bilingual customer responses with exact case facts and resolution commitments.

Each passed check directly updates an auditable skills profile, proving what the learner can actually do.

---

### Box 6: How Generative AI Is Used
In Yom Awel, Generative AI (Google Gemini) serves strictly as an **empathetic workplace coach and pedagogical translator**—never as the grading judge.

* **Why it is necessary:**
  * Translates raw, technical validation errors into supportive, actionable coaching in authentic Egyptian Arabic (*اللهجة المصرية*).
  * Adapts to the learner's specific mistakes, explaining the business impact of their error and motivating them to retry.
  * Scales individualized mentorship to thousands of learners at zero marginal cost without requiring human instructors to hand-write feedback for every submission.
* **Architectural Safety:**
  * Scoring, pass/fail thresholds, and progression are strictly deterministic code—eliminating prompt injection and grading hallucinations.
  * A deterministic Arabic fallback is built-in, ensuring uninterrupted coaching even during AI service outages or quota limits.

---

### Box 7: Current Development Stage
**Working prototype / MVP**

All three tasks are fully implemented, graded deterministically, and playable across two production channels (Web application and Telegram bot), backed by managed cloud persistence, strict security controls, and Gemini-powered coaching.
