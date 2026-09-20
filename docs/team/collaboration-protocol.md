# Team Collaboration and Pull Request Protocol

This protocol is mandatory for all five contributors. Its purpose is to keep parallel work compatible, reviewable, secure, and easy to integrate.

## 1. Source of truth

Use these sources in order:

1. merged platform design;
2. canonical contracts and shared fixtures;
3. approved implementation plan;
4. accepted Architecture Decision Records;
5. lane-specific member task file;
6. pull request discussion for implementation detail.

If two sources conflict, stop implementation and open a contract or architecture discussion. Do not silently select one interpretation.

## 2. GitHub is the technical communication record

All decisions that affect code, contracts, behavior, data, security, deployment, costs, or another member's work must be recorded in GitHub.

- Use an **issue** for requirements, bugs, design questions, and work tracking.
- Use a **draft pull request** as soon as a branch has a testable skeleton or a contract question.
- Use **review threads** for line-specific feedback.
- Use an **ADR pull request** for architectural boundary changes.
- Use the linked issue checklist for progress and blockers.

Chat or verbal discussions may be faster, but the responsible member must summarize the decision in the issue or pull request before implementation continues. A decision not recorded in GitHub is not authoritative.

## 3. Branch rules

Branch from the latest verified `main` contract baseline.

Naming:

```text
member-1/<issue>-<short-purpose>
member-2/<issue>-<short-purpose>
member-3/<issue>-<short-purpose>
member-4/<issue>-<short-purpose>
member-5/<issue>-<short-purpose>
```

Examples:

```text
member-2/12-submission-idempotency
member-4/18-sales-evaluator-v1
member-5/24-web-upload-flow
```

Rules:

- one concern per branch;
- no direct commits to `main`;
- no long-lived `develop` branch;
- rebase or merge `main` before final review according to repository policy;
- do not force-push after review begins unless reviewers are notified;
- never rewrite another member's branch;
- do not mix formatting, refactoring, and feature work without explicit scope.

## 4. Issue readiness

An issue may enter `Ready` only when it contains:

- owner;
- product or technical outcome;
- exact acceptance criteria;
- owned and affected paths;
- consumed and produced interfaces;
- dependencies and blocking issues;
- required tests;
- security/privacy impact;
- zero-cost impact;
- expected reviewers.

Workflow:

```text
Backlog -> Ready -> In progress -> Review -> Preview verification -> Done
                         |            |
                         +-> Blocked <-+
```

A blocked issue must name the blocking decision, owner, and linked issue or pull request.

## 5. Pull request lifecycle

### Draft stage

Open a draft pull request early. The description must state:

- linked issue;
- user-visible outcome;
- architecture boundary affected;
- contracts consumed and produced;
- current status;
- explicit questions for reviewers;
- files another member should not edit concurrently.

Draft pull requests are collaboration surfaces, not merge candidates.

### Ready-for-review stage

Mark ready only after:

- acceptance criteria are implemented;
- tests are added and passing locally;
- contract fixtures are updated when relevant;
- the branch is current with `main`;
- generated files are identified;
- screenshots or preview links are attached for user-facing work;
- security, privacy, and zero-cost checks are completed;
- the author performs a self-review of the full diff.

### Review stage

Reviewers classify comments:

- **Blocking:** correctness, contract, security, privacy, data loss, paid dependency, accessibility, or acceptance failure.
- **Required:** maintainability, test coverage, observability, or documented convention failure.
- **Suggestion:** optional improvement that may be deferred.
- **Question:** clarification that must be answered but does not automatically block.

Authors respond to every blocking and required thread with either:

- the commit that resolves it;
- evidence that the existing behavior is correct;
- a linked follow-up issue explicitly accepted by the reviewer.

Only reviewers resolve their blocking threads unless they explicitly delegate resolution to the author.

## 6. Required pull request description

Every pull request must include:

```markdown
## Outcome

## Linked issue

## Owned paths changed

## Cross-lane paths changed

## Contracts consumed or changed

## Verification performed
- [ ] Unit tests
- [ ] Contract tests
- [ ] Integration tests
- [ ] Security/privacy checks
- [ ] Zero-cost check
- [ ] Preview or screenshots when applicable

## Failure and rollback behavior

## Deployment or migration notes

## Reviewer questions

## Claim-to-evidence impact
```

## 7. Review matrix

The author cannot approve or merge their own pull request. A required role occupied by the author is replaced by a designated backup reviewer from a different lane, recorded in the linked issue before review starts. The backup must own or consume the affected contract; authors cannot choose an uninvolved reviewer merely to satisfy the count.

| Change area | Required approving roles | Minimum approvals |
|---|---|---:|
| Product behavior, Arabic copy, task instructions, submission claims | Member 1; for code, the affected implementation owner | 1 for docs-only, 2 for code |
| Domain contracts, state machine, application services | Member 2 and one consumer owner | 2 |
| Schema, migrations, RLS, storage policy | Member 2 and Member 5; security tests required | 2 |
| AI prompts, provider behavior, fallback | Member 3 and Member 1 | 2 |
| Evaluator or scoring policy | Member 4 and Member 1 | 2 |
| Web, Telegram, FastAPI transport | Member 5 and each directly affected service owner | 2 minimum |
| Vercel, dependencies, CI, runtime configuration | Member 5 and Member 2 | 2 |
| Shared contract change | Member 2 and every affected consumer owner | All listed roles |
| Cross-cutting architecture | Members 2 and 5 plus one other unaffected member | 3 |

When the author occupies a required role, the predesignated backup fills that seat and the minimum count does not decrease. A normal lane-local pull request not covered by a stricter row requires one approval from another member.

Repository branch rules and `.github/CODEOWNERS` enforce required pull requests, required status checks, conversation resolution, stale-review dismissal after new commits, no force pushes, no branch deletion, and no self-merge. `docs/team/reviewer-roster.yaml` maps each member role and backup role to verified GitHub usernames; the roster is the source used to generate CODEOWNERS and must contain no unverified handle.

## 8. Merge gates

Merging is prohibited unless:

- required approvals are present;
- every blocking and required review thread is resolved;
- all automated checks pass;
- contract compatibility passes;
- migrations include forward verification and a recovery strategy;
- user-facing changes have a verified preview;
- security-sensitive changes include negative tests;
- no paid dependency or billing requirement was introduced;
- documentation reflects changed behavior;
- the pull request remains within its accepted scope.
- the author is not the merger and every required reviewer is independent of the author.

Use squash merge for ordinary work so each pull request becomes one coherent `main` commit. Preserve separate commits only when repository maintainers explicitly need them for migration sequencing.

## 9. Contract-change protocol

Before changing a shared field, enum, endpoint, event, repository method, evaluator result, or fixture:

1. Open a GitHub issue titled `Contract change: <name>`.
2. Explain the current contract, proposed contract, reason, migration, and affected consumers.
3. Tag every affected owner.
4. Obtain approval from Member 2 and affected consumers.
5. Update schema, typed model, JSON fixture, producer, consumers, and contract tests in the same pull request.
6. Record backward compatibility or the coordinated cutover.

No consumer may merge an independently invented variant of a shared contract.

## 10. Architecture-change protocol

Create `docs/architecture/decisions/NNNN-short-title.md` containing:

- context;
- decision;
- alternatives considered;
- consequences;
- security and privacy effect;
- zero-cost effect;
- migration or rollback effect.

An ADR becomes accepted only after the required architecture reviewers approve its pull request. Update the canonical design when the decision materially changes it.

## 11. Database and migration review

Every migration pull request must include:

- schema intent;
- exact affected tables, indexes, policies, and functions;
- forward migration verification;
- recovery or compensating migration strategy;
- RLS allow and deny tests;
- generated TypeScript/Python contract updates if applicable;
- proof that no production data is assumed to exist in a particular state;
- Supabase security and performance advisor results when a project is available.

Never edit a migration that has already been applied to a shared environment. Add a new migration.

## 12. Reviewer checklist

Reviewers verify behavior, not just style:

- Does the change meet every acceptance criterion?
- Does it preserve architectural boundaries?
- Are names and types identical to canonical contracts?
- Are failure, retry, duplicate, and unauthorized paths tested?
- Can the change leak PII, secrets, prompts, or uploaded content?
- Can it create unexpected cost or require a paid plan?
- Does it work without Gemini through the fallback?
- Does it assume durable Vercel local storage?
- Are Arabic and accessibility requirements preserved?
- Does documentation tell the next member enough to integrate safely?

## 13. Author handoff checklist

Before requesting final review, the author states:

- what changed;
- what deliberately did not change;
- how to run the focused tests;
- how to exercise the behavior manually;
- which fixtures or interfaces consumers should use;
- known risks;
- rollback or disable path;
- whether downstream members must rebase or regenerate clients.

## 14. Integration protocol

- Member 5 integrates against canonical fakes from the beginning.
- When a real module becomes available, replace one fake at a time and run its contract suite.
- Integration bugs are assigned to the layer that violates the contract, not automatically to Member 5.
- If the contract is ambiguous, pause integration and use the contract-change protocol.
- The full end-to-end suite runs after each real adapter replaces a fake.
- The exact release candidate is deployed to a Vercel preview and verified before promotion.

## 15. Release review

Member 1 owns the release checklist but cannot waive technical gates.

Release requires:

- all five lane owners confirm their acceptance criteria;
- Member 5 confirms preview and production configuration;
- Member 2 confirms migrations and data integrity;
- Member 3 confirms provider fallback;
- Member 4 confirms evaluator reproducibility;
- Member 1 confirms claim-to-evidence accuracy and submission assets;
- a second member witnesses the end-to-end rehearsal;
- the verified commit is tagged and referenced in the demo documentation.

## 16. Disagreement and escalation

Resolve disagreements with evidence:

1. restate the acceptance criterion or architectural rule;
2. reproduce the behavior with a test, trace, preview, or minimal example;
3. document competing trade-offs in the issue;
4. ask the relevant owner and one neutral reviewer to decide;
5. use an ADR when the decision changes architecture.

Do not merge an unresolved disagreement because a deadline is close. Reduce scope through an explicit product decision instead of accepting an inconsistent system.
