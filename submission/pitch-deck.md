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
- **First task: clean-sales.** Supervisor Tarek hands over a messy sales file: duplicate orders, mixed dates, negative numbers, missing emails.
- **Real deliverables:** download the file, clean it in any spreadsheet tool, upload CSV or XLSX.
- **Web flow (pending):** end-to-end browser verification is still in progress.

---

## 3. The Core Innovation: Determinism + AI Coaching

<!-- claim: claim-cap-deterministic-eval -->
<!-- claim: claim-cap-arabic-feedback -->

| Layer | Technology | Role |
|---|---|---|
| **Evaluation (current)** | `sales-cleaning@1`, deterministic Python | Four 25-point checks. Pass = score >= 75 **and** `unique_orders` passed. |
| **Coaching (pending)** | Gemini with a deterministic fallback | Explains the result in Egyptian Arabic or English; never sets scores. |

**The critical rule:** a file with only the duplicates left scores 75 and is still a retry.

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
- **Resilience:** `FEEDBACK_MODE=fallback` forces the deterministic feedback; grading never depends on Gemini. Integrated outage behavior is pending verification.

---

## 5. Current Evidence Boundary

<!-- claim: claim-cap-retry-handling -->
<!-- claim: claim-cap-skills-projection -->

<!-- claim: claim-cap-demo-kit -->

- **Current:** domain state, persistence, retry records, skill evidence, the bilingual task package, and the clean-sales evaluator have automated tests. Five demo uploads (100 CSV, 100 XLSX, 75 retry, 50 retry, rejected) are graded by the real evaluator in a test.
- **Pending:** the web experience, bilingual feedback in the browser, and the one-command local demo, until an end-to-end run is recorded.
- **Release decision:** `no-go` until the final candidate has passing CI, browser acceptance, deployment evidence, and five-member review.

---

## 6. Sustainable Impact & Roadmap

<!-- claim: claim-cap-sql-sandbox -->

- **Roadmap:**
  - More workplace tasks beyond clean-sales.
  - Employer-facing competency profiles backed by passed checks.
  - Sandboxed SQL Query Evaluation.
  - Interactive Egyptian Dialect Voice Notes on Telegram.
  - Advanced Inventory & Accounting Simulations.

---

## شكراً لكم!
### Yom Awel — لأن أول يوم عمل بيبدأ هنا

**Live Demo & Repository:** `https://github.com/Ziad-7/yom-awel`
