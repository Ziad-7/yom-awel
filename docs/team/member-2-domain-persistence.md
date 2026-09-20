# Member 2 — Domain, Application Services, and Persistence

## Mission

Create the stable business core that makes learner progress correct, reproducible, secure, and independent of Telegram, Vercel, Supabase, Gemini, and the web framework.

Execution checklist: [Member 2 implementation plan](../superpowers/plans/2026-09-20-member-2-domain-persistence.md)

## Owned paths

- `services/api/src/yom_awel/domain/**`
- `services/api/src/yom_awel/application/**`
- `services/api/src/yom_awel/ports/**`
- `services/api/src/yom_awel/persistence/**`
- `supabase/migrations/**`
- `contracts/schemas/**`
- `contracts/fixtures/**` as contract custodian
- domain, application, repository, migration, and RLS tests

## Inputs

- approved product journeys and completion rules from Member 1;
- canonical architecture;
- evaluator port behavior from Member 4;
- feedback port behavior from Member 3;
- transport requirements from Member 5.

## Outputs

- canonical Pydantic models and enums;
- stable JSON schemas and fixtures;
- domain entities, value objects, and errors;
- explicit state machine and invariants;
- application use cases;
- repository, artifact, evaluator, feedback, clock, and ID ports;
- SQLite/local adapters for tests and fallback;
- Supabase schema, migrations, repositories, RLS, and storage policies;
- idempotency and transaction design;
- contract, persistence, concurrency, and security tests.

## Work packages

### 1. Canonical contracts

Define exact fields, types, nullability, constraints, serialization, and compatibility policy for:

- learner;
- external identity;
- task and task version;
- artifact;
- submission;
- evaluation result and checks;
- feedback result;
- attempt;
- skill definition, evidence, and summary;
- progression state;
- submission outcome;
- stable application errors.

Publish JSON fixtures for happy, failed, provider-fallback, duplicate, and unauthorized cases. Coordinate TypeScript generation with Member 5.

### 2. Domain model

Implement behavior around aggregates instead of mutable dictionaries. Encode:

- one active task per learner;
- legal progression transitions;
- immutable published task versions;
- score range and pass-policy validation;
- append-only attempts and skill evidence;
- deterministic progression;
- versioned evaluator/prompt references;
- administrative reset restrictions.

### 3. Application services

Define use cases with typed inputs/outputs:

- `OnboardLearner`;
- `GetCurrentTask`;
- `CreateArtifactUpload`;
- `ProcessSubmission`;
- `GetSubmissionOutcome`;
- `GetSkillsProfile`;
- `ResetDemoLearner`.

Transactions belong at the application boundary. Transport adapters map into these use cases but do not call repositories directly.

### 4. Idempotency and concurrency

Use channel event IDs and client idempotency keys. Reserve and commit the key, request fingerprint, submission ID, and processing lease in a short transaction before expensive work. Run evaluation/feedback outside a database transaction, then compare-and-swap finalize attempt/progress/outbox state in a second short transaction. Active duplicates receive the same submission ID and retry guidance; completed duplicates receive the original outcome; fingerprint mismatch is a conflict. Supabase uses atomic reservation/finalization RPCs and SQLite implements the same contract. Protect progress with database uniqueness and optimistic versioning. Test simultaneous submissions, lease recovery, and retry after partial failure.

### 5. Persistence model

Create migrations for all approved tables, indexes, constraints, grants, policies, and storage configuration. Use UTC timestamps and database-generated UUIDs where consistent with the contract. Add indexes for learner progress, submission idempotency, attempts by learner/task, and outbox processing.

### 6. Authorization and RLS

- Enable RLS on every exposed table.
- Revoke unnecessary role grants.
- Scope web sessions to the authenticated learner.
- Treat Telegram access as trusted-server access only after webhook and identity validation.
- Never authorize from user-editable metadata.
- Keep service-role credentials server-side.
- Test ownership, cross-user denial, anonymous denial, and administrative paths.

### 7. Retention execution

Own the 30-day artifact purge implementation, not only its documentation. Claim expired rows with a lease, delete private storage objects, finalize audited tombstones, retry failed reconciliation, and remove expired anonymous Auth users only after application data is reconciled. Run bounded cleanup after cloud submissions and from a daily/manual zero-cost GitHub Actions workflow reviewed by Member 5.

### 8. Local adapters

Provide SQLite and local artifact adapters that implement the same ports. Local mode supports development, deterministic tests, and zero-cloud fallback without changing domain code.

## Acceptance criteria

- Contracts have no conflicting aliases or undocumented optional fields.
- Invalid state transitions fail with stable domain errors.
- Failed evaluations never advance progress.
- A passed task advances once under retries and concurrent requests.
- Duplicate idempotency keys return the original outcome.
- Attempt and skill evidence history is auditable and reproducible.
- SQLite and Supabase repositories pass the same contract suite.
- Migrations apply from an empty database and preserve existing shared environments.
- RLS tests prove allowed and denied behavior.
- Retention tests prove idempotent storage/row reconciliation and anonymous-identity cleanup without a paid scheduler.
- Domain and application packages contain no framework/provider imports.

## Required tests and reviews

- Unit tests for every transition, invariant, and score boundary.
- Property or parameterized tests for transition combinations.
- Repository adapter contract tests.
- Transaction rollback and concurrent-submission tests.
- Migration smoke tests from an empty database.
- RLS allow/deny tests.
- Serialization snapshots shared with Member 5.

## Pull request responsibilities

Member 2 is the contract custodian and required reviewer for:

- shared types and fixtures;
- domain/application behavior;
- schema, migration, policy, or storage changes;
- dependency changes affecting the Python backend;
- cross-cutting architecture changes.

Member 2 cannot approve an interface change until every affected owner acknowledges the migration and contract tests cover it.

## Handoffs

- To Member 3: final `EvaluationResult`, `FeedbackResult`, error, and timeout contracts.
- To Member 4: evaluator port and task-version structures.
- To Member 5: use-case interfaces, OpenAPI schema, auth context, and repository-independent fakes.
- To Member 1: authoritative state descriptions and profile evidence semantics.

## Out of scope

- Rendering web or Telegram messages.
- Writing persona prompts.
- Implementing task-specific grading.
- Bypassing domain services from transport or migration code.
