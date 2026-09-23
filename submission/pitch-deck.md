---
marp: true
theme: default
paginate: true
header: "Yom Awel (يوم أول) — Workplace Simulation Platform"
footer: "Cairo, Egypt • September 2026"
---

# Yom Awel (يوم أول)
### Arabic-First Workplace Simulation for Applied Digital Skills

**Connecting Egyptian Youth to Market-Ready Data Careers**

---

## 1. The Challenge in Egypt

<!-- claim: claim-stat-youth-unemployment -->
<!-- claim: claim-stat-skills-gap -->

- **25%+ Youth Unemployment** among university graduates (CAPMAS 2023).
- **The "Experience Paradox":** Companies require 1–2 years of experience; graduates have theoretical knowledge but lack practical workplace execution.
- **The Practical Skills Gap:** Employers identify spreadsheet data hygiene, validation, and error-handling as the primary operational bottleneck in entry-level hires.

---

## 2. Our Solution: Yom Awel

<!-- claim: claim-cap-web-experience -->
<!-- claim: claim-stat-spreadsheet-demand -->

- **No lectures. No multiple-choice tests.**
- **Authentic Workplace Simulation:** Learners start their "First Workday" at simulated Egyptian companies.
- **Real Enterprise Tasks:** Receive raw, messy business datasets via Web or Telegram.
- **Real Artifact Deliverables:** Download, clean, format, and submit real Excel/CSV spreadsheets.

---

## 3. The Core Innovation: Determinism + AI Coaching

<!-- claim: claim-cap-deterministic-eval -->
<!-- claim: claim-cap-arabic-feedback -->

| Layer | Technology | Role |
|---|---|---|
| **Evaluation** | Deterministic Python Engine | **Strict 0–100 grading.** Checks duplicate orders, date formats, negative values, and missing fields. **Zero hallucinations.** |
| **Coaching** | Gemini AI (Egyptian Arabic) | **Pedagogical Supervisor.** Explains errors warmly, offers constructive hints, and guides iteration. |

> **Key Invariant:** AI coaches the student, but **only deterministic code grades the student.**

---

## 4. System Architecture

<!-- claim: claim-cap-state-machine -->
<!-- claim: claim-cap-artifact-upload -->

```
[ Next.js Web App ]   [ Telegram Bot Adapter ]
          │                     │
          ▼                     ▼
     [ FastAPI Modular Application & Ports ]
          │                     │
   ┌──────┴──────────┐   ┌──────┴──────────┐
   ▼                 ▼   ▼                 ▼
[Supabase/SQLite] [Storage] [Evaluator] [Gemini/Fallback]
```

- **Zero-Cost Deployment:** Vercel Hobby + Supabase Free + Gemini Free Tier.
- **High Resilience:** Automatic failover to local Arabic fallback if AI is offline.

---

## 5. Live Verified Evidence

<!-- claim: claim-cap-retry-handling -->
<!-- claim: claim-cap-skills-projection -->

- **Task Clean-Sales (v1):** Real-world sales cleaning scenario with 4 automated checks.
- **Safe Iterative Retries:** Students learn by correcting mistakes; attempts are versioned without penalizing progression.
- **Auditable Skills Profile:** Direct evidence mapping—no vanity percentages or unearned certificates.

---

## 6. Sustainable Impact & Roadmap

<!-- claim: claim-cap-sql-sandbox -->

- **Immediate Goal:** Train 10,000 Egyptian job seekers in foundational data operations.
- **Employer Pipeline:** Connect verified competency profiles directly to regional logistics, retail, and tech employers.
- **Roadmap:**
  - Sandboxed SQL Query Evaluation.
  - Interactive Egyptian Dialect Voice Notes on Telegram.
  - Advanced Inventory & Accounting Simulations.

---

## شكراً لكم!
### Yom Awel — لأن أول يوم عمل بيبدأ هنا

**Live Demo & Repository:** `https://github.com/Ziad-7/yom-awel`
