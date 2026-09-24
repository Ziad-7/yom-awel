# Yom Awel Known Limitations & Operational Boundaries

- **Release Version:** 1.0.0
- **Audience:** Judges, Evaluators, and Prospective Integrators

---

## 1. Scope & Task Catalog
- **No production release yet:** `clean-sales` (v1) is the only planned initial curriculum task. Evaluator, content, and web work must be integrated and accepted before it is described as playable.
- **Single Concurrent Task per Learner:** By domain design invariant, each learner has at most one active task in progress to enforce sequential competency acquisition.

---

## 2. File Ingestion Boundaries
- **Supported Formats:** Only `.csv` and single-sheet `.xlsx` files are accepted. Multi-tab workbooks, password-protected sheets, and macros (`.xlsm`) are safely rejected by design.
- **Size Limitation:** Maximum artifact upload size is bounded at 5 MB (5,242,880 bytes) to stay safely within free-tier Supabase Storage and Vercel serverless request limits.

---

## 3. AI Rate Limiting & Resilience
- **Gemini allowance:** Limits depend on the eligible model, account, region, and current provider terms; the final deployment must record the observed allowance instead of assuming a fixed RPM.
- **Graceful-degradation target:** Unit-tested deterministic Arabic fallback code exists. End-to-end outage behavior is still pending and no uptime guarantee is made.

---

## 4. Zero Mandatory Cost Commitment
- The prototype must not require a paid subscription or card-backed dependency. Vercel Hobby, Supabase Free, and any model allowance must be rechecked before deployment; free-tier permanence and unlimited capacity are not guaranteed.
