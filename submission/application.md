# Yom Awel (يوم أول) — Competition Application

<!-- Release status: no-go. Capability labels below follow docs/product/evidence/claim-matrix.yaml. -->

## 1. Project Title & Executive Summary

**Project Name:** Yom Awel (يوم أول)  
**Tagline:** Arabic-first workplace simulation for task-based digital and data skills training.  
**Primary Track:** AI for Education & Workforce Development (Egypt & MENA)

Yom Awel is a prototype for task-based preparation for entry-level digital roles in Egypt. Its intended experience places learners in a simulated Egyptian company as junior data associates, where they receive workplace assignments and submit spreadsheet deliverables instead of completing passive lectures or multiple-choice quizzes.

The current repository contains the domain and persistence foundation, while deterministic evaluation, Egyptian Arabic coaching, and the web experience remain experimental until their workstreams are integrated and accepted. The design keeps scoring in deterministic code and limits generative AI to explanatory coaching; it does not claim that any grading system is perfectly error-free.

---

## 2. Problem Statement

The team is exploring a practical learning problem: learners may understand concepts without having a safe place to rehearse everyday workplace workflows such as spreadsheet cleanup, date normalization, and error reconciliation. The current submission deliberately makes no numerical labor-market claim until a primary source and exact supporting table have been independently verified.

Furthermore, existing learning platforms suffer from two critical limitations:
1. **The Language and Cultural Disconnect:** Most technical tools and datasets are English-centric, failing to reflect the bilingual realities, local business scenarios, and cultural idioms of the Egyptian workplace.
2. **The LLM Grading Fallacy:** Many generative AI education tools use LLMs to score student assignments directly. This introduces hallucinations, non-reproducible grading, and security vulnerabilities (prompt injection).

---

## 3. The Yom Awel Solution & Innovation

Yom Awel re-engineers digital skills training through three structural innovations:

1. **Realistic Egyptian Workplace Simulation:**
   Learners don't take courses; they start their "First Workday" at simulated local enterprises (such as *شركة النيل للتوزيع والتجارة*). They interact with a virtual supervisor (*أستاذ طارق*) who communicates in professional, encouraging Egyptian Arabic.

2. **Deterministic Primacy with Generative Coaching:**
   <!-- claim: claim-cap-deterministic-eval -->
   <!-- claim: claim-cap-arabic-feedback -->
   The planned progression contract is governed by deterministic, versioned Python evaluators. Gemini is designed not to award scores or alter progression; its role is explanatory coaching. A deterministic fallback exists at unit-test level, but integrated outage behavior and availability have not yet been verified.

3. **Verifiable, Evidence-Backed Competencies:**
   <!-- claim: claim-cap-skills-projection -->
   <!-- claim: claim-cap-retry-handling -->
   The implemented domain model projects competency evidence from recorded evaluation checks. The learner-facing skills-profile experience remains pending integration and browser acceptance.

---

## 4. Technical Architecture & Zero Mandatory Cost

<!-- claim: claim-cap-state-machine -->
<!-- claim: claim-cap-artifact-upload -->

The repository is designed as a modular monolith with ports and adapters:
- **Frontend Channels (experimental):** A Next.js web application targeting Vercel, RTL Arabic, and WCAG AA acceptance; Telegram remains an adapter target rather than a verified release capability.
- **Backend Core:** FastAPI modular application with domain services isolated from third-party frameworks.
- **Database & Storage:** Adapters exist for Supabase PostgreSQL/private storage and for local SQLite/filesystem development.
- **AI Infrastructure (experimental):** Gemini-backed coaching with deterministic Arabic templates as a fallback path.
- **Cost boundary:** The team will use only no-cost plans for this prototype. Deployment eligibility, quotas, and end-to-end operation must still be checked before release; no claim of unlimited or permanently free operation is made.
