## Outcome

Member 3 feedback consumes the merged contracts without alternate domain schemas or grading
authority. Arabic coaching has a deterministic no-key path, bounded optional Gemini calls,
strict output validation, and a configuration-only provider handoff to Member 5.

Prepared description for replacement PR #21; supersedes stale PR #4. GitHub PR metadata updates
and closing #4 returned HTTP 403 (`Resource not accessible by integration`) on 2026-09-23.
This file records the completed template even while those remote administrative actions are blocked.

## Linked issue

- [Canonical consumer coordination #5](https://github.com/Ziad-7/yom-awel/issues/5)
- [Member 2 baseline/post-merge consumer review #3](https://github.com/Ziad-7/yom-awel/issues/3)
- [Member 3 plan](../superpowers/plans/2026-09-20-member-3-ai-feedback.md), M3-1 through M3-6.

## Owner and lane

- Member: 3, @SEIF-HAYTHAM.
- Lane: AI feedback/personas, provider resilience, privacy and quality tests.

## Owned paths changed

- `services/api/src/yom_awel/feedback/**`
- `services/api/tests/feedback/**`
- Member 3 team/plan documentation, `docs/product/feedback-rubric.md`,
  `docs/operations/gemini-free-tier.md`, and this evidence document.

## Cross-lane paths changed

- `services/api/pyproject.toml`, `services/api/uv.lock`: Google GenAI dependency; Member 2
  (@abdulrahman-111) owns these, with Member 5 runtime review required.
- `pytest.ini` and pyproject pytest settings: shared async test configuration; Members 2 and 5 review.
- Learner-visible Arabic examples/rubric: Member 1 approval required.
- No Member 4 implementation, domain, ports, persistence, migration, or canonical fixture changes.

## Contracts consumed or changed

Consumes `TaskVersion`, `EvaluationCheck`, `EvaluationResult`, `FeedbackResult`, `Language`,
and `FeedbackProvider.generate(evaluation, language, learner_note=None)` from Member 2.
Uses canonical `task-version-clean-sales.json` and `evaluation-{pass,fail}.json`.
The remote `contracts-v1` tag and current main both resolve to `054fbc4ceeb9b47986a5756718933388cfc2b941`.
No canonical contract changed. The Gemini JSON wire model is internal to the adapter, not a
replacement `FeedbackResult` or a source of authoritative grades.

Persona decision: use canonical `tarek`, matching Member 2's application fallback and fixture.
This implements Member 2's explicit review request; Eng. Tarek remains the display name.

## Acceptance evidence

Sources checked: Mohamed Sameh's Gmail notifications and
[PR #4 comment](https://github.com/Ziad-7/yom-awel/pull/4#issuecomment-5798169799),
[Member 2 review](https://github.com/Ziad-7/yom-awel/pull/4#pullrequestreview-5293718100),
and the baseline follow-ups on #2/#3. Older issue #5 proposals are superseded by merged contracts.

| Request | Resolution/evidence |
|---|---|
| Rebuild from merged Member 2 main | Branch `codex/member-3-ai-feedback-v2` starts at `054fbc4`; the three original M3 commits were replayed before fix-forward commits. Replacement PR #21 exists. Closing #4 is blocked by GitHub write permissions. |
| Read language-specific details, no removed optional `details` | `prompt.py` selects `details_ar`/`details_en`, preserves exact approved canonical text and maps all other free text to safe hints. `test_prompt.py` tests independent language selection and malicious rows. |
| Four canonical 25-point checks | Prompt and fallback map `unique_orders`, `standard_dates`, `valid_numeric_values`, `complete_customer_records`; per-check fallback tests cover each. |
| Canonical persona | Policy, personas, tests and plan use `tarek`. |
| Mutable provider exception | `test_errors.py` exercises raising/chaining and traceback assignment. |
| Current fixtures/snapshots | `conftest.py` loads canonical fixtures; prompt fixture equality and pass/fail snapshot tests run against them. |
| Root gates and zero cost | Commands below pass without model calls or a Gemini key; missing-key configuration never resolves task context or constructs an SDK client. |
| Plan's fixed output format | SDK uses the parser's JSON schema; prompt specifies all required fields/headings; strict parser rejects coercion, contradictions, missing references and English-only section content. |
| Strict budget/retry | Real hung-coroutine cancellation test; only one network/quota retry with an explicit finite nonnegative delay fitting the budget. Invalid/missing delays fall back. |
| Member 5 configuration handoff | `config.py` selects fallback, Gemini chain or injected fake while returning the canonical port. No changes to the application/composition root. |
| Meaningful quality cases | Provider-failure really raises; malicious-error text is injected into `EvaluationError`; all cases validate four sections/decision/score and failed-check guidance. The synthetic score-74 boundary tests authoritative score preservation, not the four equal-weight evaluator's reachable scores. |

Member 3 post-merge consumer review of #2: inspected the feedback port, domain payloads,
canonical fixtures, and `ProcessSubmission` feedback invocation/persistence boundary.
The call signature matches; `FeedbackResult` has no grading fields; progression still consumes
`eval_result.passed`, and feedback metadata is persisted separately. No blocker found in that
consumer boundary. This is not approval of unrelated database/RLS/platform work, and no remote
review submission or independent human approval is implied.

Mohamed's #10 follow-up concerns feedback consumers of Member 4's evaluator. Its branch emits
the same four IDs, bilingual details and diagnostic codes. Arbitrary detail strings remain
excluded from provider requests; approved mappings are used instead. Its full evaluator merge
and scoring review belong to Members 4/1/2. Issue #13 client-email coaching remains a blocked
later milestone, not a feature implemented or approved by this PR.

## Verification performed

- [x] Focused unit tests pass (78 feedback tests).
- [x] Contract tests pass as part of the root suite.
- [x] Available local integration tests pass in the root suite; 13 environment-dependent tests skip.
- [x] Automated security/privacy regressions pass; limitations documented in the operations guide.
- [x] Automated Arabic structure/grounding checks pass; human tone/rubric approval remains pending.
- [x] Zero-cost path requires no API credentials, provider calls, or billing.
- [ ] UI preview/accessibility review: not applicable to this backend-only change.
- [x] Author reviewed the Member 3 changes and shared-file scope.

Commands from repository root:

```text
uv run --project services/api pytest services/api/tests/feedback -q
  78 passed
uv run --project services/api pytest -q
  314 passed, 13 skipped
uv run --project services/api ruff check services/api
  passed
uv run --project services/api ruff format --check services/api
  passed
uv run --project services/api mypy --config-file services/api/pyproject.toml services/api/src/yom_awel
  passed, 42 source files
uv lock --check --project services/api
  passed, 52 packages
uv run --project services/api pre-commit run --all-files
  format, lint, strict mypy, full pytest passed
uv run --project services/api python services/api/scripts/export_schemas.py
git diff --exit-code -- contracts
  unchanged canonical schemas
```

CI on the newly pushed commit must be checked on PR #21; prior-head green CI is not evidence
for a later commit. No live Gemini or cloud Supabase verification is claimed.

## Failure and rollback behavior

Missing key, provider errors, timeout, refusal, malformed/non-grounded response select local
deterministic feedback. Maximum provider budget is 10 seconds including the bounded retry.
Disable the optional provider by selecting `FeedbackConfig(mode="fallback")`; rollback needs
no data migration. No grade/progression is determined by the provider response.

## Deployment or migration notes

No migration, generated client, endpoint or frontend change. Member 5 supplies the trusted task
resolver and runtime configuration. Secret keys belong only in the server secret store, never
source control. Default mode is fallback. Optional model availability/free-tier eligibility must
be rechecked at deployment; the required product path remains no-key and local.

## Security and privacy impact

Authorization, RLS and artifact storage are unchanged. No raw artifact objects enter the provider
request. Evaluator free text is replaced by approved mappings; bounded optional notes are
redacted/escaped/delimited. Known identifiers, storage URLs and key patterns are redacted before
truncation. This is not a universal PII classifier: callers must omit notes if arbitrary personal
or workbook data cannot be excluded. Logs exclude prompt/response bodies and exception messages.
Human quality review is still required for semantic grounding and solution non-disclosure.

## Zero-cost impact

Works locally with deterministic fallback and in existing free-compatible CI/runtime paths.
Google GenAI is optional at runtime; no billing, paid runner, Vercel/Supabase upgrade or paid model
is introduced. No hosting deployment was performed by this backend PR.

## Claim-to-evidence impact

Supports tested canonical Arabic fallback, optional validated model feedback, and graceful
provider-failure handling. Does not establish production model accuracy, human-approved tone,
complete semantic safety, Hazem/Mona journeys, or client-email coaching.

## Reviewer questions

- Member 2: confirm exact contract consumption, canonical `tarek`, and shared dependency/config edits.
- Member 1: approve persona, canonical snapshots and the quality rubric before learner release.
- Member 5: approve runtime dependency/config and wire the factory into the composition root.
- Independent Member 3-seat reviewer: review prompt/privacy/grounding changes; author cannot self-approve.
- GitHub maintainer: copy this completed description to #21 and close superseded #4 if integration
  permissions still prevent those actions. Do not resolve another reviewer's blocking threads.

## Required reviewers

- [ ] Independent lane reviewer (Member 3 author requires a backup).
- [ ] Affected contract owner, @abdulrahman-111 (Member 2).
- [ ] Product reviewer, Member 1.
- [ ] Integration/deployment reviewer, Member 5.

No human approval has been fabricated, and this PR is not asserted to be merge-ready until the
required reviews and current-head CI pass.
