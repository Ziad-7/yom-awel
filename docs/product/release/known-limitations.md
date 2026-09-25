# Yom Awel Known Limitations & Operational Boundaries

- **Release Version:** 1.0.0
- **Audience:** Judges, Evaluators, and Prospective Integrators

---

## 1. Scope & Task Catalog
- **Three tasks:** `clean-sales`, `sql-report`, and `client-email` each have a versioned bilingual brief, source file, and deterministic four-check evaluator. Learners can switch tasks and revisit saved attempts.
- **One selected task:** A learner submits to one selected task at a time. Switching tasks keeps prior results.

---

## 2. File Ingestion Boundaries
- **Supported submissions:** `clean-sales` accepts `.csv` or single-sheet `.xlsx`; `sql-report` accepts UTF-8 `.sql`; `client-email` accepts UTF-8 `.txt`. The SQL and email tasks also offer a CSV/XLSX source download. Multi-sheet workbooks, password-protected files, macros, and external links are rejected.
- **Task limits:** `clean-sales` permits at most 10,000 data rows and 20 columns, and requires at least 40 rows. SQL execution is read-only and bounded. The email rubric checks stated case facts and commitments; it is a deterministic exercise, not a human-quality writing assessment.
- **Size limitation:** `clean-sales` accepts up to 5 MiB locally; the hosted API caps request bodies at 4,000,000 bytes. Text tasks have a 65,536-byte package limit.

---

## 3. AI Rate Limiting & Resilience
- **Gemini allowance:** Limits depend on the eligible model, account, region, and current provider terms; the final deployment must record the observed allowance instead of assuming a fixed RPM.
- **Fallback:** deterministic task-specific feedback can be forced with `FEEDBACK_MODE=fallback`. Feedback never changes the grade; no uptime guarantee is made.

---

## 4. Zero Mandatory Cost Commitment
- The prototype must not require a paid subscription or card-backed dependency. Vercel Hobby, Supabase Free, and any model allowance must be rechecked before deployment; free-tier permanence and unlimited capacity are not guaranteed.

---

## 5. Sessions & Channels
- **Anonymous sessions:** a learner is identified only by an HttpOnly session cookie; there is no account recovery, and a new private window is a new learner.
- **Telegram:** not part of the demo release.
- **Retention:** the hosted Postgres demo keeps anonymous learner records and uploaded artifacts until its dedicated `yom_awel` schema is removed after the event. The older Supabase Storage retention workflow does not purge this database.
