# Yom Awel Final Submission & Release Sign-Off Checklist

- **Target Release:** v1.0.0
- **Verified Commit:** `a957768462d628ee4728a38bb44ce99b45401ac0` (three-task application)

---

## 1. Submission Deliverables Audit

- [ ] **Application Answers:** Freeze only after final claim/evidence review.
- [ ] **Pitch Presentation:** Export and inspect the Marp-compatible deck.
- [ ] **Demo Scripts:** Execute the primary and outage scripts against the final deployed candidate.
- [ ] **Asset Manifest:** Generate exports and record their SHA-256 digests.
- [x] **No Leaked Secrets:** PR #42 detect-secrets and gitleaks checks passed for the final application candidate.
- [ ] **No Placeholder Tokens:** Scan the final public submission artifacts.

---

## 2. Platform & Quality Gates

- [x] **Automated Tests:** CI passed on PR #42; results are recorded in `docs/quality/three-task-hosted-verification.md`.
- [x] **Deterministic Evaluation:** every presenter upload in `demo/files/` is graded by the real evaluator in `tools/quality/tests/test_demo_kit.py`.
- [x] **End-to-End Demo:** eight hosted Playwright journeys passed in Arabic and English with CSV, XLSX, SQL, and email submissions.
- [ ] **Local Fallback Run:** start `demo/run_local.sh` and pass both health checks.
- [ ] **Recorded Video:** record the demo from the verified candidate and link it in `docs/operations/demo-runbook.md`.
- [x] **Bilingual Copy:** hosted Arabic/mobile/Axe and local keyboard/accessibility browser checks passed.
- [ ] **Zero Mandatory Cost:** Confirm eligibility and quotas for Vercel, Supabase, and the selected model without adding a paid or card-backed dependency.
- [ ] **Five-Member Sign-Off:** Record linked reviews against the exact final candidate commit.
