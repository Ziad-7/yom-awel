# Yom Awel (يوم أول): Competition Application

<!-- Release status: no-go until docs/product/release/release-signoff.yaml records a go decision. Capability labels follow docs/product/evidence/claim-matrix.yaml. -->

## 1. Project Title & Executive Summary

**Project Name:** Yom Awel (يوم أول)
**Tagline:** Arabic-first workplace simulation for task-based digital and data skills training.
**Primary Track:** AI for Education & Workforce Development (Egypt & MENA)

Yom Awel puts a learner in a simulated Egyptian company on their first workday. Their supervisor,
Tarek, hands them a real assignment: clean a messy daily sales file. The learner downloads the
file, cleans it in any spreadsheet tool, uploads the result, and gets a deterministic score for
each check plus feedback from Tarek in Egyptian Arabic or English.

What is on `main` and covered by tests today: the learner state machine, persistence, the
clean-sales task package in both languages, the deterministic `sales-cleaning@1` evaluator for CSV
and XLSX, the feedback package with its deterministic fallback, and a presenter kit of graded
demo uploads. The web experience and its end-to-end wiring to the real evaluator are **pending**
verification; see section 5.

---

## 2. Problem Statement

Learners may understand spreadsheet concepts without ever having rehearsed an everyday workplace
workflow such as removing duplicate orders, normalizing dates, or reconciling revenue. The
submission makes no numerical labor-market claim until a primary source and its exact table are
independently verified.

Two limitations of existing tools motivate the design:

1. **Language and context.** Most technical practice material is English-only and does not
   reflect Egyptian workplace scenarios.
2. **LLM grading.** Tools that let a language model grade assignments produce non-reproducible
   scores and are exposed to prompt injection through the submitted file.

---

## 3. The Yom Awel Solution

1. **A realistic first task.**
   <!-- claim: claim-cap-bilingual-task -->
   The clean-sales brief and hints exist in Egyptian Arabic and English and are pinned by SHA-256
   in the task package, so the graded content cannot drift silently.

2. **Deterministic grading, explained by AI.**
   <!-- claim: claim-cap-deterministic-eval -->
   <!-- claim: claim-cap-safe-ingestion -->
   <!-- claim: claim-cap-arabic-feedback -->
   Four checks worth 25 points each: `unique_orders` (critical), `standard_dates`,
   `valid_numeric_values`, `complete_customer_records`. A submission passes only with a score of
   at least 75 **and** the critical check passed, so a file that still has duplicate orders is a
   retry even at 75 points. Unreadable or unsafe files are rejected with a coded bilingual reason
   before any check runs. Tarek's feedback explains the result using Gemini when configured and a
   deterministic fallback otherwise; feedback never changes the grade. Integrated feedback
   delivery is pending end-to-end verification.

3. **Progress backed by evidence.**
   <!-- claim: claim-cap-skills-projection -->
   <!-- claim: claim-cap-retry-handling -->
   A failed attempt moves the learner to a retry state without losing history, and skills
   evidence is a direct projection of passed checks.

---

## 4. Technical Architecture

<!-- claim: claim-cap-state-machine -->
<!-- claim: claim-cap-artifact-upload -->
<!-- claim: claim-cap-secret-hygiene -->

- **Web (pending):** a Next.js app; the browser calls only relative `/api/v1` URLs, proxied
  to the API.
- **API:** FastAPI transport over framework-free domain and application services.
- **Evaluation:** the versioned `sales-cleaning@1` evaluator, reading CSV and XLSX into the same
  table so format never changes the grade.
- **Feedback:** Tarek persona, Gemini adapter with output validation, deterministic fallback.
- **Persistence:** SQLite and local files in local mode; hosted Postgres and private storage in
  cloud mode.
- **Security:** detect-secrets in pre-commit and gitleaks in CI; secrets only in runtime
  environment variables of the API.
- **Cost boundary:** only no-cost plans are used for this prototype. Quotas and eligibility must be
  rechecked before release; no claim of unlimited or permanently free operation is made.

---

## 5. Evidence Boundary

<!-- claim: claim-cap-demo-kit -->
<!-- claim: claim-cap-web-experience -->
<!-- claim: claim-cap-local-demo -->

- **Current:** the presenter kit's five uploads are graded by the real evaluator in an automated
  test: 100 (CSV), 100 (XLSX), 75 retry (critical check failed), 50 retry, and a
  `missing_columns` rejection.
- **Pending:** the web experience, the one-command local demo, and bilingual feedback shown in
  the browser. Each is listed with its reason in the claim matrix and becomes current only after
  an end-to-end run is recorded.
