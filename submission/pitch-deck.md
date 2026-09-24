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

- **Practice Gap:** Learners need a safe environment to rehearse complete workplace workflows, not only recall concepts.
- **Evidence Boundary:** This no-go candidate intentionally omits numerical market claims until their primary sources are independently verified.

---

## 2. Our Solution: Yom Awel

<!-- claim: claim-cap-web-experience -->

- **No lectures. No multiple-choice tests.**
- **Authentic Workplace Simulation:** Learners start their "First Workday" at simulated Egyptian companies.
- **Planned Workplace Tasks:** Receive synthetic, realistic business datasets through an accessible web flow.
- **Artifact Deliverables:** Download, clean, format, and submit synthetic Excel/CSV spreadsheets after integration is complete.

---

## 3. The Core Innovation: Determinism + AI Coaching

<!-- claim: claim-cap-deterministic-eval -->
<!-- claim: claim-cap-arabic-feedback -->

| Layer | Technology | Role |
|---|---|---|
| **Evaluation (experimental)** | Deterministic Python Engine | Proposed 0–100 grading with a critical-check gate. |
| **Coaching (experimental)** | Gemini / local fallback | Explains deterministic results; never sets scores. |

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

- **No-paid-service target:** Vercel Hobby + Supabase Free + an eligible Gemini free allowance, subject to final eligibility and quota review.
- **Resilience target:** Local Arabic fallback exists in unit-tested code; integrated outage behavior is pending.

---

## 5. Current Evidence Boundary

<!-- claim: claim-cap-retry-handling -->
<!-- claim: claim-cap-skills-projection -->

- **Current:** Domain state, persistence contracts, retry records, and skill-evidence projection have automated tests.
- **Experimental:** Clean-sales evaluation, Arabic feedback, and the web experience require integration and end-to-end acceptance.
- **Release decision:** `no-go` until the final candidate has passing CI, browser acceptance, deployment evidence, and five-member review.

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
