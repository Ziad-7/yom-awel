# Yom Awel Evidence & Truthfulness Policy

- **Governing Version:** 1.0.0
- **Lead Owner:** Member 1 (Product, Evidence & Release)

---

## 1. Core Mandate: Evidence Before Claims

The Yom Awel product, pitch deck, README, and hackathon submission must describe only verified, demonstrable capabilities. Unimplemented ideas, future extensions, and speculative metrics must never be represented as existing functionality.

---

## 2. Hierarchy of Authoritative Sources

When making statistical, market, or educational claims (e.g. youth unemployment rates, digital skills gaps in Egypt, spreadsheet proficiency needs):

1. **Tier 1 (Highest Authority):**
   - Official national statistical agencies (e.g. CAPMAS — Central Agency for Public Mobilization and Statistics).
   - International multilateral bodies (e.g. World Bank, ILO, UNESCO, OECD).
   - Ministry reports (e.g. Ministry of Communications and Information Technology — MCIT Egypt).
2. **Tier 2 (Acceptable with Exact Context):**
   - Peer-reviewed academic publications and established think-tank whitepapers.
   - Published surveys from major industry recruiting platforms (e.g. Wuzzuf / Forasna Annual Hiring Reports).
3. **Strictly Prohibited as Evidence:**
   - Unverified social media slides, blog posts, or search engine AI summary snippets.
   - Developer assertions, uncommitted code, or planned roadmap tasks.
   - Generalized, unsourced claims (e.g. "80% of companies require X" without a citation).

---

## 3. Claim Classification Standards

Every claim in the project is assigned one of four classifications:

| Status | Definition | Evidence Requirement |
|---|---|---|
| `current` | A capability on `main`, covered by passing tests. | Must cite at least one automated test and one preview check. Every cited path must exist. |
| `verified` | A `current` capability that was also exercised end to end on a recorded candidate. | Same as `current`, plus the run is recorded in the release sign-off. |
| `pending` | Implemented or in review, but not yet verified end to end. | Must state its `pending_reason`. Any cited test or artifact must exist. |
| `roadmap` | A planned future capability. | Must be explicitly labeled as "Roadmap" or "المستقبل" in all decks and product copy. |

`tools/quality/validate_release_evidence.py` enforces these rules, including that every path under
`evidence.automated_tests` and `evidence.artifacts` exists in the repository.

---

## 4. Citation and Maintenance Rules

1. **Source Register Entry:**
   Every cited statistic must have an entry in `source-register.yaml` with:
   - Unique `id`
   - Publication `title`
   - Authoritative `publisher`
   - Publication date (`year` or `date`)
   - Canonical `url`
   - Exact `supported_claim` summary
2. **Date Qualification:**
   Statistics older than 3 years must explicitly cite the survey year in the text (e.g. "According to CAPMAS 2023 labor bulletin...").
3. **Zero-Tolerance for Fabrication:**
   Any claim in a deck or README lacking a supporting entry in the Claim-to-Evidence Matrix will block release sign-off.
