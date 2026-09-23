# Yom Awel Known Limitations & Operational Boundaries

- **Release Version:** 1.0.0
- **Audience:** Judges, Evaluators, and Prospective Integrators

---

## 1. Scope & Task Catalog
- **Single Active Curriculum:** The initial production release provides task `clean-sales` (v1). Additional tracks (SQL relational analytics, inventory reconciliation) are documented as roadmap items and not currently playable in the live catalog.
- **Single Concurrent Task per Learner:** By domain design invariant, each learner has at most one active task in progress to enforce sequential competency acquisition.

---

## 2. File Ingestion Boundaries
- **Supported Formats:** Only `.csv` and single-sheet `.xlsx` files are accepted. Multi-tab workbooks, password-protected sheets, and macros (`.xlsm`) are safely rejected by design.
- **Size Limitation:** Maximum artifact upload size is bounded at 5 MB (5,242,880 bytes) to stay safely within free-tier Supabase Storage and Vercel serverless request limits.

---

## 3. AI Rate Limiting & Resilience
- **Gemini Free Tier Throughput:** Free-tier Gemini API operates under a 15 Requests-Per-Minute (RPM) limit. 
- **Graceful Degradation:** During high concurrency or temporary API quota exhaustion, the system automatically falls back to deterministic Egyptian Arabic template coaching, guaranteeing zero learner disruption.

---

## 4. Zero Mandatory Cost Commitment
- The platform does not use card-backed cloud services, paid queues, or metered infrastructure. All operational boundaries are tuned to live permanently on free-tier allocations (Vercel Hobby + Supabase Free + Gemini Free).
