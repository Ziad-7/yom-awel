# Yom Awel Final Submission & Release Sign-Off Checklist

- **Target Release:** v1.0.0
- **Verified Commit:** Pending final integrated release candidate

---

## 1. Submission Deliverables Audit

- [ ] **Application Answers:** Freeze only after final claim/evidence review.
- [ ] **Pitch Presentation:** Export and inspect the Marp-compatible deck.
- [ ] **Demo Scripts:** Execute the primary and outage scripts against the final deployed candidate.
- [ ] **Asset Manifest:** Generate exports and record their SHA-256 digests.
- [ ] **No Leaked Secrets:** Attach a secret-scan report for the final candidate commit.
- [ ] **No Placeholder Tokens:** Scan the final public submission artifacts.

---

## 2. Platform & Quality Gates

- [ ] **Automated Tests:** Run all suites on the exact final integrated commit.
- [x] **Deterministic Evaluation:** every presenter upload in `demo/files/` is graded by the real evaluator in `tools/quality/tests/test_demo_kit.py`.
- [ ] **End-to-End Demo:** run `docs/product/release/product-acceptance.md` in Arabic and English, with CSV and XLSX.
- [ ] **Local Fallback Run:** start `demo/run_local.sh` and pass both health checks.
- [ ] **Recorded Video:** record the demo from the verified candidate and link it in `docs/operations/demo-runbook.md`.
- [ ] **Bilingual Copy:** Verify RTL layout, language, keyboard flow, screen-reader announcements, and contrast in a deployed browser.
- [ ] **Zero Mandatory Cost:** Confirm eligibility and quotas for Vercel, Supabase, and the selected model without adding a paid or card-backed dependency.
- [ ] **Five-Member Sign-Off:** Record linked reviews against the exact final candidate commit.
