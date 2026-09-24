## Outcome

Invalid feedback timeout configuration now fails immediately instead of disabling the deadline. One shared validator is used by FeedbackConfig, GeminiAdapter and ResilientFeedbackProvider.

## Linked issue

Fixes #24. Follow-up to merged PR #21.

## Owner and lane

Member 3 (@SEIF-HAYTHAM), feedback provider resilience.

## Owned paths changed

- services/api/src/yom_awel/feedback/{timeouts,config,gemini,service}.py
- services/api/tests/feedback/test_timeouts.py
- docs/operations/gemini-free-tier.md
- docs/team/member-3-timeout-review.md (this handoff)

## Cross-lane paths changed

None. No dependency, shared configuration, transport, evaluator, persistence or canonical contract edits.

## Contracts consumed or changed

Existing FeedbackProvider, EvaluationResult, FeedbackResult, TaskVersion and Language are unchanged. Only Member 3 timeout construction semantics change: invalid numeric budgets raise ValueError; finite positive budgets are capped at 10 seconds.

## Acceptance evidence

- NaN, positive/negative infinity, zero, negative zero and negative values: rejected at all three public construction boundaries.
- Positive values 0.01 and 10: preserved; 11 and 1e100: capped at 10.
- Real hanging injected Gemini call through the configuration factory and resilient chain: cancelled at a 0.01-second budget and replaced with deterministic feedback. An outer 1-second test guard detects a hung regression.
- Existing real hanging-provider test remains passing.
- Before the fix: new tests reported 20 failed, 3 passed. After: all 23 pass.

## Verification performed

- [x] Focused tests: 114 feedback tests passed.
- [x] Full suite including available local integration/contract tests: 350 passed, 13 skipped.
- [x] Ruff format/lint, strict mypy and pre-commit.
- [x] Security/privacy: no sensitive values added to errors or logs.
- [x] Zero-cost: injected clients only; no live Gemini requests or credentials.
- [x] Author reviewed scoped diff.
- UI preview/accessibility: not applicable; no learner-facing UI change.

Commands from repository root:

```text
uv run --project services/api pytest services/api/tests/feedback -q
uv run --project services/api pytest -q
uv run --project services/api ruff check services/api
uv run --project services/api mypy --config-file services/api/pyproject.toml services/api/src/yom_awel
uv run --project services/api pre-commit run --all-files
uv lock --check --project services/api
uv run --project services/api python services/api/scripts/export_schemas.py
git diff --exit-code -- contracts
```

All passed; schema export unchanged. Skipped tests still require their external environment. Current-head GitHub CI must also pass before merge.

## Failure and rollback behavior

Invalid timeout raises ValueError with a fixed message at construction. Correct invalid deployment configuration before startup; it is not treated as a transient provider failure. Valid configuration retains deterministic fallback on provider timeout and all existing error paths. Keep mode=fallback with a valid budget if Gemini is disabled. No data migration or destructive rollback needed.

## Deployment or migration notes

No migration, new environment variable or dependency. Default remains 10 seconds. Any existing NaN/infinite/nonpositive timeout configuration must be corrected before deployment.

## Security and privacy impact

Closes a deadline bypass/availability issue. Authorization, RLS, artifact handling, prompt redaction and logging behavior are unchanged. Validation errors do not echo supplied values or secrets.

## Zero-cost impact

No paid service or live model calls. Existing local/fallback and free-compatible deployment paths remain available.

## Claim-to-evidence impact

Supports the bounded-provider-deadline claim for accepted timeout configuration. Does not claim other Member 3 follow-ups or full product integration are resolved.

## Reviewer questions

@abdulrahman-111: verify all issue #24 acceptance criteria and immediate ValueError behavior. Member 5: ensure configuration loading surfaces the fixed error clearly.

## Required reviewers

- [ ] Independent Member 3-seat backup reviewer.
- [ ] Member 1 for provider/fallback behavior under the review matrix.
- [ ] Member 2 (@abdulrahman-111) issue verification/re-review.

No approval is asserted; no self-merge.
