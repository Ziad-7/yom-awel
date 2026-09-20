# Member 1 Product and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved product design into measurable learning content, consistent Arabic copy, defensible release claims, and a fully evidenced submission package.

**Architecture:** Product truth is maintained as versioned Markdown, YAML, and machine-checkable indexes. Task intent is separated from evaluator implementation, every public claim maps to release evidence, and the final submission identifies the exact tested commit and deployment.

**Tech Stack:** Markdown, YAML, JSON Schema, Python 3.12 validation scripts, pytest, Marp-compatible Markdown for the pitch source, Vercel preview evidence, GitHub pull requests.

**Spec:** `docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md`

## Global Constraints

- Describe only verified behavior as current; label every unimplemented idea as roadmap.
- Do not introduce any service, asset, font, template, or publishing workflow that requires payment.
- Treat Egyptian Arabic, RTL behavior, accessibility, and mixed Arabic/English technical terms as acceptance requirements.
- Keep learner-facing instructions independent of evaluator internals so tasks remain understandable without revealing exact checks.
- Require Member 4 approval for scoring intent and Member 1 approval for evaluator semantics; neither role changes the rubric alone.
- Cite authoritative sources for every market, education, or impact statistic.
- Store no applicant identity documents, credentials, or private learner data in the public repository.
- Record the exact commit, preview URL, production URL, and evidence bundle used for release sign-off.

## Review Focus

- A learner must understand what to do, what artifact to submit, how success is measured, and how to retry without developer explanation.
- Arabic copy must be natural and consistent, not a literal translation of English implementation terms.
- Claims, screenshots, demo narration, and application answers must describe the same verified release.
- The demo must still complete when Gemini is missing, rate-limited, or unavailable.
- No acceptance criterion may be waived through a verbal explanation or manual database correction.
- Submission exports must not contain secrets, personal data, temporary URLs, or unsupported claims.

---

### Task M1-1: Define Product Journeys and the Capability Ledger

**Files:**
- Create: `docs/product/journeys/learner-first-task.md`
- Create: `docs/product/journeys/learner-retry.md`
- Create: `docs/product/journeys/skills-profile.md`
- Create: `docs/product/capability-ledger.yaml`
- Create: `tools/quality/validate_capability_ledger.py`
- Test: `tools/quality/tests/test_capability_ledger.py`

**Interfaces:**
- Consumes: state machine, submission sequence, and channel behavior from the approved platform design.
- Produces: the product behavior contract used by Members 2–5 and the authoritative current/experimental/roadmap classification.

- [ ] **Step 1: Write the failing ledger validation tests**

Create tests that load `docs/product/capability-ledger.yaml` and require each capability to have a unique ID, owner, status, learner outcome, acceptance evidence, and implementation path. Restrict status to `current`, `experimental`, or `roadmap`; require `current` items to name at least one automated test and one preview verification step.

```python
from pathlib import Path

import yaml

from tools.quality.validate_capability_ledger import validate_ledger


ROOT = Path(__file__).resolve().parents[3]


def test_capability_ledger_is_complete() -> None:
    ledger = yaml.safe_load(
        (ROOT / "docs/product/capability-ledger.yaml").read_text(encoding="utf-8")
    )
    errors = validate_ledger(ledger)
    assert errors == []


def test_current_capabilities_name_test_and_preview_evidence() -> None:
    ledger = yaml.safe_load(
        (ROOT / "docs/product/capability-ledger.yaml").read_text(encoding="utf-8")
    )
    for capability in ledger["capabilities"]:
        if capability["status"] == "current":
            assert capability["evidence"]["automated_tests"]
            assert capability["evidence"]["preview_checks"]
```

- [ ] **Step 2: Run the tests and confirm failure**

Run: `uv run pytest tools/quality/tests/test_capability_ledger.py -q`

Expected: FAIL because the ledger and validator do not exist.

- [ ] **Step 3: Write the three learner journeys**

For each journey, document actor, channel, goal, preconditions, numbered normal flow, failure and retry paths, state transitions, completion evidence, visible outcome, analytics-free verification procedure, accessibility expectations, and ownership handoffs. The first-task journey must cover onboarding, task retrieval, artifact upload, deterministic evaluation, feedback display, progression, and profile refresh.

- [ ] **Step 4: Create the capability ledger**

Add stable IDs for web onboarding, Telegram onboarding, spreadsheet task delivery, private artifact upload, deterministic evaluation, feedback fallback, retry, progression, and skills profile. Initially classify entries based on the repository evidence at execution time; never promote an item to `current` merely because this plan mentions it.

- [ ] **Step 5: Implement the ledger validator**

Return human-readable errors for duplicate IDs, invalid status, missing owner, missing outcome, missing implementation path, or incomplete evidence. Exit non-zero when invoked as a script and errors exist.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest tools/quality/tests/test_capability_ledger.py -q
uv run python tools/quality/validate_capability_ledger.py
git add docs/product/journeys docs/product/capability-ledger.yaml tools/quality
git commit -m "docs: define learner journeys and capability ledger"
```

---

### Task M1-2: Specify Learning Objectives, Task Content, and Scoring Intent

**Files:**
- Create: `docs/product/learning/competency-model.md`
- Create: `docs/product/learning/scoring-policy.md`
- Create: `task_packages/clean-sales/1/content/brief.ar-EG.md`
- Create: `task_packages/clean-sales/1/content/brief.en.md`
- Create: `task_packages/clean-sales/1/content/hints.ar-EG.md`
- Create: `task_packages/clean-sales/1/content/hints.en.md`
- Create: `task_packages/clean-sales/1/learning-objectives.yaml`
- Create: `tools/quality/validate_learning_objectives.py`
- Test: `tools/quality/tests/test_learning_objectives.py`

**Interfaces:**
- Consumes: evaluation contract from Member 4 and task version contract from Member 2.
- Produces: versioned task intent and learner content that Member 4 maps to deterministic checks.

- [ ] **Step 1: Write the failing objective-contract tests**

Require task ID `clean-sales`, version `1`, intended learner level, workplace context, measurable objectives, required input/output artifacts, allowed transformations, forbidden transformations, skill mappings, pass policy, misconception catalog, and retry guidance. Require every objective to map to one or more proposed check IDs without exposing expected cell values in learner content.

- [ ] **Step 2: Run the tests and confirm failure**

Run: `uv run pytest tools/quality/tests/test_learning_objectives.py -q`

Expected: FAIL because the learning documents and validator do not exist.

- [ ] **Step 3: Define the competency model and scoring policy**

Define observable competencies for spreadsheet hygiene, type normalization, missing-value decisions, duplicate handling, formula preservation, documentation, and professional delivery. State that pass/fail comes only from Member 4's deterministic evaluator, feedback cannot change progression, critical checks can force failure, and every scoring-policy change requires both Member 1 and Member 4 review.

- [ ] **Step 4: Write bilingual learner content**

Write a culturally credible Egyptian workplace scenario with equivalent Arabic and English meaning. State the requested deliverable, accepted spreadsheet formats, 5 MB maximum size, privacy warning, completion expectations, and retry path. Keep the Arabic brief primary and useful without the English version.

- [ ] **Step 5: Create the objective manifest and validator**

Use stable IDs such as `obj-normalize-dates`, `obj-handle-missing`, and `obj-preserve-source`. Validate uniqueness, required mappings, bilingual content presence, declared file paths, and consistency with the scoring policy.

- [ ] **Step 6: Obtain cross-owner review**

Open the pull request as draft. Request Member 4 review on objectives, permitted transformations, critical checks, and pass policy; request Member 3 review on misconception descriptions; request Member 5 review on learner clarity and upload constraints. Resolve disagreements in pull-request comments and update the decision log before approval.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
uv run pytest tools/quality/tests/test_learning_objectives.py -q
uv run python tools/quality/validate_learning_objectives.py
git add docs/product/learning task_packages/clean-sales/1/content task_packages/clean-sales/1/learning-objectives.yaml tools/quality
git commit -m "docs: define first task learning contract"
```

---

### Task M1-3: Establish the Arabic Content and Accessibility System

**Files:**
- Create: `docs/product/content/voice-and-tone.md`
- Create: `docs/product/content/glossary.yaml`
- Create: `docs/product/content/interface-copy.yaml`
- Create: `docs/product/content/accessibility-copy-checklist.md`
- Create: `tools/quality/validate_content_catalog.py`
- Test: `tools/quality/tests/test_content_catalog.py`

**Interfaces:**
- Consumes: feedback categories from Member 3 and interface state inventory from Member 5.
- Produces: canonical Arabic/English terms and learner-visible messages for web, Telegram, and deterministic fallback feedback.

- [ ] **Step 1: Write the failing catalog tests**

Test unique message IDs, required `ar-EG` and `en` values, non-empty accessible labels, placeholder parity across languages, valid interpolation names, glossary-term consistency, and coverage for loading, empty, success, failure, retryable, offline, unsupported-file, oversized-file, evaluation-failed, and fallback-feedback states.

- [ ] **Step 2: Run the tests and confirm failure**

Run: `uv run pytest tools/quality/tests/test_content_catalog.py -q`

Expected: FAIL because the content catalog and validator do not exist.

- [ ] **Step 3: Define voice, tone, and glossary rules**

Document Egyptian Arabic warmth without slang that excludes learners, direct action-first errors, respectful retry language, gender-neutral phrasing where practical, consistent persona naming, readable numerals, date formatting, and treatment of unavoidable English technical terms. Include preferred, allowed, and rejected variants for core concepts.

- [ ] **Step 4: Create the interface copy catalog**

Assign stable IDs such as `upload.invalid_type`, `upload.too_large`, `evaluation.processing`, `evaluation.retry`, `feedback.fallback_notice`, and `profile.empty`. Provide screen-reader labels separately from visual shorthand when the visible phrase is insufficient.

- [ ] **Step 5: Add accessibility review instructions**

Require logical reading order in RTL, keyboard-operable retry actions, error association with the affected control, status announcements that do not rely only on color, predictable rendering of mixed-direction technical terms, and comprehension testing without developer narration.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest tools/quality/tests/test_content_catalog.py -q
uv run python tools/quality/validate_content_catalog.py
git add docs/product/content tools/quality
git commit -m "docs: establish bilingual content system"
```

---

### Task M1-4: Build the Source Register and Claim-to-Evidence Matrix

**Files:**
- Create: `docs/product/evidence/source-register.yaml`
- Create: `docs/product/evidence/claim-matrix.yaml`
- Create: `docs/product/evidence/evidence-policy.md`
- Create: `tools/quality/validate_release_evidence.py`
- Test: `tools/quality/tests/test_release_evidence.py`

**Interfaces:**
- Consumes: release-candidate test reports, preview checks, screenshots, and authoritative external sources.
- Produces: the only approved set of claims for the README, pitch, application, and demo narration.

- [ ] **Step 1: Write the failing evidence tests**

Require every claim to have a stable ID, exact wording, usage locations, status, owner, and evidence. Statistical claims must reference a source entry containing title, publisher, publication date, canonical URL, access date, and the exact supported interpretation. Capability claims marked `current` must reference an automated test and verified preview evidence tied to a commit SHA.

- [ ] **Step 2: Run the tests and confirm failure**

Run: `uv run pytest tools/quality/tests/test_release_evidence.py -q`

Expected: FAIL because the evidence files and validator do not exist.

- [ ] **Step 3: Define the evidence policy**

Set source priorities to official statistics, peer-reviewed research, and authoritative program documentation. Define when a claim must be removed, narrowed, dated, or labeled as an estimate. Forbid using a search-result excerpt, unsourced slide, planned test, or developer statement as final evidence.

- [ ] **Step 4: Populate the source register**

Add only sources actually used by product materials. Record a short paraphrase rather than copying long passages. Verify the source URL, publication identity, date, and interpretation before merging.

- [ ] **Step 5: Populate the claim matrix**

Map every README, application, deck, and demo claim to test paths, evidence artifact paths, preview verification steps, or a `roadmap` label. Reject entries whose proof depends on a local uncommitted state or private link that reviewers cannot access.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
uv run pytest tools/quality/tests/test_release_evidence.py -q
uv run python tools/quality/validate_release_evidence.py
git add docs/product/evidence tools/quality
git commit -m "docs: add release claim evidence controls"
```

---

### Task M1-5: Create the Application, Pitch, and Demo Package

**Files:**
- Create: `submission/application.md`
- Create: `submission/pitch-deck.md`
- Create: `submission/demo-script.md`
- Create: `submission/demo-contingency.md`
- Create: `submission/asset-manifest.yaml`
- Create: `tools/quality/validate_submission_package.py`
- Test: `tools/quality/tests/test_submission_package.py`

**Interfaces:**
- Consumes: approved claim matrix, production-shaped preview, team details supplied outside the public repository, and application requirements verified at execution time.
- Produces: reviewable source files and a deterministic asset manifest for final submission exports.

- [ ] **Step 1: Write the failing package tests**

Test that all required source files exist, every claim ID used in the application/deck/demo exists in the matrix, every manifest artifact has a SHA-256 digest and purpose, no source contains placeholder markers, and no committed URL contains localhost or an expired Vercel preview alias.

- [ ] **Step 2: Run the tests and confirm failure**

Run: `uv run pytest tools/quality/tests/test_submission_package.py -q`

Expected: FAIL because the submission package and validator do not exist.

- [ ] **Step 3: Draft the application from verified evidence**

Answer each application prompt directly, maintain one consistent description of the learner and value proposition, cite claim IDs inline in comments that are removed from the final export, and keep private team/eligibility material outside Git. Do not invent form limits or deadlines; verify current requirements before final export.

- [ ] **Step 4: Create the pitch source**

Use a concise sequence: learner problem, product experience, why deterministic evaluation matters, system architecture, live evidence, responsible AI/fallback behavior, impact path, and roadmap. Each capability slide must reference claim IDs in source comments.

- [ ] **Step 5: Create primary and contingency demos**

The primary script covers onboarding through the skills profile against a verified preview. The contingency script demonstrates the same value with Gemini disabled and uses the deterministic fallback. Add timestamp targets, speaker ownership, reset instructions, expected screen state, and a recovery line for each external dependency failure.

- [ ] **Step 6: Build the asset manifest**

Record source path, export path, MIME type, maximum accepted size verified from official requirements, SHA-256, claim IDs, generated-at time, and source commit. Exclude identity records, enrollment proof, secrets, and access tokens from Git; record only a private-checklist reference for those items.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
uv run pytest tools/quality/tests/test_submission_package.py -q
uv run python tools/quality/validate_submission_package.py
git add submission tools/quality
git commit -m "docs: assemble application pitch and demo sources"
```

---

### Task M1-6: Execute Product Acceptance and Release Sign-Off

**Files:**
- Create: `docs/product/release/product-acceptance.md`
- Create: `docs/product/release/release-signoff.yaml`
- Create: `docs/product/release/known-limitations.md`
- Create: `docs/product/release/submission-checklist.md`
- Create: `tools/quality/validate_release_signoff.py`
- Test: `tools/quality/tests/test_release_signoff.py`

**Interfaces:**
- Consumes: Member 2 contract results, Member 3 fallback proof, Member 4 evaluation report, Member 5 accessibility/E2E report, and verified Vercel preview.
- Produces: final go/no-go decision and an auditable record of exactly what was released.

- [ ] **Step 1: Write the failing sign-off tests**

Require a full 40-character commit SHA, immutable evidence artifact digests, preview URL, production URL when promoted, reviewer approvals for all five lanes, zero-cost review outcome, secret-scan result, automated test result, browser acceptance result, Gemini-disabled demo result, known limitations, and an explicit `go` or `no-go` decision. Reject `go` when any required gate is missing or failed.

- [ ] **Step 2: Run the tests and confirm failure**

Run: `uv run pytest tools/quality/tests/test_release_signoff.py -q`

Expected: FAIL because the release artifacts and validator do not exist.

- [ ] **Step 3: Write the acceptance script**

Specify a fresh-account test for web and Telegram: onboarding, task retrieval, valid upload, invalid upload, deterministic pass, deterministic fail, retry, duplicate delivery, feedback fallback, progression, profile display, keyboard operation, Arabic RTL review, and mobile viewport. Record expected evidence for each step.

- [ ] **Step 4: Run acceptance against the exact preview commit**

Use an incognito browser and a new Telegram test identity. Save no personal identifiers in Git. Link the preview deployment to the commit SHA, record test reports and screenshot digests, and file every failure as a GitHub issue or blocking pull-request comment. Re-run the complete affected journey after fixes.

- [ ] **Step 5: Verify zero-cost and failure-mode operation**

Confirm both Vercel projects and Supabase remain on free plans, no paid integration is enabled, spending paths are documented, artifact retention is bounded, and Gemini-disabled operation completes. If the release requires payment, mark `no-go` until the dependency is removed or replaced.

- [ ] **Step 6: Complete cross-member sign-off**

Require Member 2 approval for data/state integrity, Member 3 for feedback and fallback, Member 4 for evaluation determinism, Member 5 for delivery/accessibility, and Member 1 for product truth. Record approvals as linked pull-request reviews, not names typed by one person.

- [ ] **Step 7: Validate, tag the evidence commit, and commit the sign-off**

Run:

```bash
uv run pytest tools/quality/tests/test_release_signoff.py -q
uv run python tools/quality/validate_release_signoff.py
git add docs/product/release tools/quality
git commit -m "docs: record product release acceptance"
```

Create the release tag only after this commit is reviewed, CI is green, the production promotion references the same tree, and the repository has no uncommitted changes.

---

## Completion Gate

Member 1 is complete only when:

- journeys and learning objectives are versioned and machine-validated;
- Member 4 has approved scoring intent and Member 1 has approved evaluator semantics;
- learner-facing Arabic copy has passed content, RTL, and accessibility review;
- every external statistic has a verified authoritative source;
- every current capability claim maps to automated and preview evidence;
- the application, pitch, and demo describe the same verified commit;
- the full learner journey passes with Gemini disabled;
- all five member approvals and all merge checks are recorded in GitHub;
- the release needs no paid service or paid plan;
- the exact accepted commit and artifact hashes are recorded before submission.
