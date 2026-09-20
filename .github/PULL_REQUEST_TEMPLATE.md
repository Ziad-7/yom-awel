## Outcome

Describe the user or system outcome, not only the files changed.

## Linked issue

Link the issue that defines scope and acceptance criteria.

## Owner and lane

- Member:
- Lane:

## Owned paths changed

List paths owned by this lane.

## Cross-lane paths changed

List shared or other-owner paths and tag their owners. Write `None` when the change is lane-local.

## Contracts consumed or changed

Name every schema, fixture, endpoint, event, port, or generated client involved. A contract change must link its approved contract-change issue.

## Acceptance evidence

Map each issue acceptance criterion to a test, preview action, screenshot, log, or other verification evidence.

## Verification performed

- [ ] Focused unit tests pass
- [ ] Contract tests pass
- [ ] Integration tests pass when applicable
- [ ] Security and privacy checks pass
- [ ] Arabic and accessibility checks pass when user-facing
- [ ] Zero-cost check confirms no paid dependency or billing requirement
- [ ] Vercel preview or screenshots are attached when user-facing
- [ ] Author reviewed the complete diff

Commands and results:

```text
List exact verification commands and concise results.
```

## Failure and rollback behavior

Explain retry, fallback, rollback, disable, or compensating behavior.

## Deployment or migration notes

Describe environment variables, migrations, generated clients, preview behavior, and rollout order. Write `None` when not applicable.

## Security and privacy impact

Explain authorization, RLS, secrets, PII, artifacts, logging, and untrusted-input effects. Write `No change` only after checking each category.

## Zero-cost impact

Confirm the change works on Vercel Hobby, Supabase Free, Gemini free/fallback, public GitHub Actions, and local mode as applicable.

## Claim-to-evidence impact

List product/application/deck claims enabled, changed, or invalidated by this pull request. Write `None` when it changes no claim.

## Reviewer questions

Call out design decisions or risky areas that need focused review.

## Required reviewers

- [ ] Lane owner reviewer
- [ ] Affected contract owner
- [ ] Product reviewer when learner-visible
- [ ] Integration/deployment reviewer when cross-cutting
