# Yom Awel Known Limitations & Operational Boundaries

- **Release Version:** 1.0.0
- **Audience:** Judges, Evaluators, and Prospective Integrators

---

## 1. Scope & Task Catalog
- **One task:** `clean-sales` (v1) is the only task. Its evaluator and bilingual content are on `main` and tested; the web flow is pending end-to-end verification.
- **Single Concurrent Task per Learner:** By domain design invariant, each learner has at most one active task in progress to enforce sequential competency acquisition.

---

## 2. File Ingestion Boundaries
- **Supported Formats:** Only `.csv` and single-sheet `.xlsx` files are accepted. Multi-sheet workbooks, password-protected files, macros, and external links are rejected with a coded reason.
- **Table bounds:** at most 10,000 data rows and 20 columns; at least 40 rows; the seven required columns keep their English names in both languages.
- **Size Limitation:** Maximum artifact upload size is bounded at 5 MB (5,242,880 bytes) to stay safely within free-tier Supabase Storage and Vercel serverless request limits.

---

## 3. AI Rate Limiting & Resilience
- **Gemini allowance:** Limits depend on the eligible model, account, region, and current provider terms; the final deployment must record the observed allowance instead of assuming a fixed RPM.
- **Fallback:** the deterministic Tarek feedback is unit-tested and can be forced with `FEEDBACK_MODE=fallback`. End-to-end outage behavior is pending verification and no uptime guarantee is made. Feedback never changes the grade.

---

## 4. Zero Mandatory Cost Commitment
- The prototype must not require a paid subscription or card-backed dependency. Vercel Hobby, Supabase Free, and any model allowance must be rechecked before deployment; free-tier permanence and unlimited capacity are not guaranteed.

---

## 5. Sessions & Channels
- **Anonymous sessions:** a learner is identified only by an HttpOnly session cookie; there is no account recovery, and a new private window is a new learner.
- **Telegram:** not part of the demo release.
