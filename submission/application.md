# Yom Awel (يوم أول) — Competition Application

<!-- claim: claim-cap-web-experience -->
<!-- claim: claim-stat-youth-unemployment -->
<!-- claim: claim-stat-skills-gap -->
<!-- claim: claim-stat-spreadsheet-demand -->

## 1. Project Title & Executive Summary

**Project Name:** Yom Awel (يوم أول)  
**Tagline:** Arabic-first workplace simulation for task-based digital and data skills training.  
**Primary Track:** AI for Education & Workforce Development (Egypt & MENA)

Yom Awel is an innovative educational platform that bridges the acute transition gap between graduation and employment for entry-level digital roles in Egypt. Instead of watching passive lectures or taking multiple-choice quizzes, learners join a simulated Egyptian company as junior data associates. They receive realistic workplace assignments, download authentic dirty enterprise datasets, clean and process deliverables using Excel or spreadsheets, and submit their work. 

The platform pairs rigorous deterministic automated grading (guaranteeing 100% factual correctness and zero grading hallucinations) with empathetic, culturally authentic Egyptian Arabic AI coaching powered by Gemini, backed by an offline-resilient local deterministic fallback. Every completed task builds an auditable, evidence-backed skills profile that proves real-world capability to prospective employers.

---

## 2. Problem Statement

<!-- claim: claim-stat-youth-unemployment -->
<!-- claim: claim-stat-skills-gap -->
<!-- claim: claim-stat-spreadsheet-demand -->

In Egypt, youth unemployment disproportionately affects university and intermediate degree graduates, with rates exceeding 25% according to official national statistics (CAPMAS 2023). While thousands graduate each year with academic qualifications, employers consistently report a severe applied skills gap: candidates understand theoretical concepts but struggle with everyday workplace data hygiene, spreadsheet formulas, date normalization, and error reconciliation.

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
   Progression is strictly governed by deterministic, versioned Python evaluators. The AI model (Gemini) is never permitted to award scores or alter progression; its sole purpose is pedagogical—explaining the deterministic results, identifying misconceptions, and offering encouraging hints in authentic Egyptian dialect. If Gemini is unavailable, a deterministic fallback ensures zero downtime.

3. **Verifiable, Evidence-Backed Competencies:**
   <!-- claim: claim-cap-skills-projection -->
   <!-- claim: claim-cap-retry-handling -->
   Skills profiles do not display arbitrary progress bars or gamified vanity scores. Instead, each competency maps directly to immutable, cryptographic evaluation check evidence from submitted work.

---

## 4. Technical Architecture & Zero Mandatory Cost

<!-- claim: claim-cap-state-machine -->
<!-- claim: claim-cap-artifact-upload -->

The platform is engineered as a modular monolith with ports and adapters:
- **Frontend Channels:** Next.js 15 web application on Vercel Hobby with full Right-to-Left (RTL) Arabic typography and WCAG AA accessibility, accompanied by an idempotent Telegram bot adapter.
- **Backend Core:** FastAPI modular application with domain services isolated from third-party frameworks.
- **Database & Storage:** Supabase Free tier for PostgreSQL and private signed artifact storage, with SQLite and local filesystem storage for cloud-free offline operation.
- **AI Infrastructure:** Google Gemini 2.5 Flash free tier for conversational coaching, with automatic failover to templated deterministic Arabic feedback.
- **Zero-Cost Guarantee:** Yom Awel requires zero paid subscriptions, card-backed cloud dependencies, or metered overages, ensuring infinite sustainability on free tiers.
