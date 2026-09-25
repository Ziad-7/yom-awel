# Yom Awel (يوم أول) — Competition Application

---

### Box 1: Thematic Challenge (choose one)
**Assessment Revolution**  
*(Alternative track: AI Tutor)*

*Why:* Yom Awel fundamentally transforms how applied job skills are evaluated. It replaces passive multiple-choice testing and superficial course certificates with authentic workplace artifact evaluation, while resolving the fatal flaw of many AI education platforms (the "LLM grading fallacy") by keeping assessment deterministic, auditable, and cheat-proof, while using Generative AI strictly for personalized coaching.

---

### Box 2: Problem Statement
Youth and early-career job seekers across Egypt and the MENA region face a severe "experience paradox": they acquire theoretical knowledge from universities and online courses, but employers reject them because they lack practical, day-one job readiness. Traditional education measures learning through abstract multiple-choice quizzes and passive video completion, which fail to evaluate whether a candidate can actually execute real workplace workflows or produce authentic business artifacts.

Furthermore, existing digital learning solutions suffer from two critical flaws:
1. **Cultural and Linguistic Detachment:** Training materials and enterprise scenarios are overwhelmingly Western- and English-centric, leaving local youth unprepared for the bilingual and cultural dynamics of regional workplaces.
2. **The LLM Grading Fallacy:** Emerging EdTech solutions increasingly rely on Generative AI to directly score student work. This introduces grading hallucinations, non-reproducible evaluations, and severe prompt-injection vulnerabilities, undermining the credibility of the resulting credentials.

---

### Box 3: Target User / Beneficiary
* **Primary Users:** University students, recent graduates, and career-switchers in Egypt and the MENA region preparing for entry-level digital, operational, and technical roles.
* **Secondary Beneficiaries:**
  * **Higher Education & Vocational Training Providers:** Can integrate authentic simulation tasks into their curricula and receive automated, auditable competency evidence without manually grading student submissions.
  * **Employers, HR Teams, and Workforce Development Programs:** Gain verifiable, tamper-proof proof of demonstrated task execution, drastically reducing hiring risk and onboarding ramp-up time compared to traditional resume screening.

---

### Box 4: Evidence / Validation So Far
* **Labor Market Evidence:** The applied digital skills mismatch is extensively documented by recent national and international research:
  * **ILO & CAPMAS (2024):** *Analytical report: Labour demand and labour market skills needs in Egypt* identifies severe shortages in applied digital, data, and operational workplace capabilities.
  * **ILO (2024):** *Skills mapping in Egypt: Opportunity scouting and skills mapping analysis* highlights high youth underemployment driven by the gap between academic theory and practical enterprise needs.
  * **ILO (2025):** *Skills dynamics in the Arab region* emphasizes that regional growth demands training platforms that build verifiable, job-matched capabilities.
* **Technical & Platform Validation:**
  * An extensible, modular simulation platform built on an open Task Package architecture that supports diverse artifact types (spreadsheets, database queries, business communication, with extensible support for code, documents, and workflows).
  * Validated with three working pilot task packages across two production channels (accessible bilingual web app and Telegram bot).
  * **946+ automated unit, contract, and regression tests**, plus **14 Playwright E2E browser journeys** verifying zero-cost cloud architecture (Vercel, Supabase Postgres, Google Gemini) and deterministic fallback resilience.
* **Validation Boundary:** We have validated technical reproducibility, security, and end-to-end task mechanics. Live user satisfaction and post-simulation learning gains will be measured in our upcoming university student pilot.

---

### Box 5: Solution Overview
**Yom Awel ("First Day")** is an Arabic-first workplace simulation platform that bridges the gap between education and employment by turning skills training into a simulated first day on the job at regional enterprises.

Instead of passively watching lectures, learners step into the role of a newly hired associate at a simulated company. They receive workplace briefs from a virtual supervisor (**أستاذ طارق**), execute tasks using standard industry tools (spreadsheets, SQL databases, customer communications, business systems), and submit their actual workplace artifacts via web or Telegram.

**Platform Architecture:**
1. **Extensible Task Engine:** Organizations and educators can author standardized "Task Packages" containing contextual briefs, synthetic datasets, and evaluation rules across any business discipline.
2. **Dual-Engine Assessment & Coaching:** Combines a deterministic evaluation core (ensuring factual, auditable, cheat-proof grading) with a Generative AI coaching layer (providing culturally authentic, encouraging Egyptian Arabic mentorship).
3. **Evidence-Based Competency Profile:** Replaces unverified completion badges with an auditable competency ledger, directly linking acquired skills to the specific checks passed in submitted work.

---

### Box 6: How is Generative AI Used?
In Yom Awel, Generative AI (Google Gemini) serves as an empathetic, culturally authentic workplace mentor—deliberately decoupled from the grading authority.

* **Why it is necessary:**
  * **Contextual Workplace Coaching:** Translates dry, technical evaluation checks into supportive, natural Egyptian Arabic (*اللهجة المصرية*) feedback in the voice of a seasoned workplace supervisor.
  * **Actionable Pedagogical Remediation:** Explains the real-world business impact of specific mistakes and guides the learner toward improvement, fostering a safe environment to fail and iterate.
  * **Scalability at Zero Marginal Cost:** Delivers personalized 1-on-1 mentorship to thousands of learners concurrently without requiring human instructors to hand-grade submissions.
* **Ethical & Architectural Safety:**
  * Scores, pass/fail thresholds, and progression are strictly deterministic code, completely eliminating grading hallucinations, bias, and prompt-injection risks.
  * A deterministic fallback ensures 100% operational availability even during network drops or API quota exhaustion.

---

### Box 7: Current Development Stage (choose one)
**Working prototype / MVP**

*(Explanation: A fully functional, production-deployed platform running on Vercel and Supabase Postgres, supporting dual-channel access via Web and Telegram. Proven end-to-end with three pilot task packages demonstrating tabular data, database query, and business communication workflows, with 946+ automated quality tests and full Gemini integration).*
