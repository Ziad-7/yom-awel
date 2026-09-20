# Member 2 Domain and Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the canonical contracts, deterministic domain state, application use cases, and interchangeable local/Supabase persistence required by every other lane.

**Architecture:** Domain objects enforce invariants without framework imports. Application services coordinate ports inside unit-of-work transactions. SQLite and Supabase implement identical repository contracts, while canonical Pydantic models and JSON fixtures keep AI, evaluation, transport, and web work compatible.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI-compatible schemas, pytest, mypy, Ruff, SQLite, Supabase Postgres/Storage.

**Spec:** `docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md`

## Global Constraints

- Only `EvaluationResult.passed` controls progression.
- Domain and application packages import no FastAPI, Telegram, Vercel, Supabase, Gemini, pandas, or Next.js modules.
- Every mutation is idempotent or protected by an explicit concurrency rule.
- Task versions, evaluations, feedback, attempts, and skill evidence are auditable and versioned.
- Supabase tables exposed through the Data API have RLS and explicit grants.
- Service-role credentials are server-only and never treated as learner authorization.
- SQLite and Supabase adapters satisfy the same contract suite.
- No database capability requires a paid Supabase feature.

## Review Focus

- Concurrent successful submissions for one task must advance once and create one accepted outcome.
- An `UPDATE` policy must include both row visibility and ownership checks; unauthorized updates must be denied rather than silently accepted.
- A duplicate idempotency key with different content must produce a conflict, not return or overwrite an unrelated outcome.
- Task/evaluator versions recorded on attempts must remain immutable after publication.
- Reset must be an audited administrative use case and unavailable through learner authorization.

---

### Task M2-1: Create Canonical Contracts and Fixtures

**Files:**
- Create: `services/api/pyproject.toml`
- Create: `services/api/src/yom_awel/domain/contracts.py`
- Create: `services/api/src/yom_awel/domain/enums.py`
- Create: `contracts/schemas/evaluation-result.json`
- Create: `contracts/schemas/feedback-result.json`
- Create: `contracts/schemas/submission-outcome.json`
- Create: `contracts/schemas/skills-profile.json`
- Create: `contracts/schemas/application-error.json`
- Create: `contracts/fixtures/evaluation-pass.json`
- Create: `contracts/fixtures/evaluation-fail.json`
- Create: `contracts/fixtures/feedback-generated.json`
- Create: `contracts/fixtures/feedback-fallback.json`
- Create: `contracts/fixtures/submission-pass.json`
- Create: `contracts/fixtures/submission-fail.json`
- Create: `contracts/fixtures/submission-duplicate.json`
- Create: `contracts/fixtures/skills-profile.json`
- Create: `contracts/fixtures/application-error.json`
- Test: `services/api/tests/contract/test_contract_fixtures.py`

**Interfaces:**
- Consumes: field definitions from the approved platform design.
- Produces: importable Pydantic models and stable fixture JSON used by Members 3–5.

- [ ] **Step 1: Add the Python project manifest**

Create `services/api/pyproject.toml` with Python `>=3.12,<3.13`, runtime dependencies `pydantic>=2,<3`, and development dependencies `pytest`, `pytest-asyncio`, `mypy`, and `ruff`. Configure package discovery under `src`, pytest under `tests`, strict mypy for `src/yom_awel`, and Ruff line length 100. Generate and commit `uv.lock` during execution.

- [ ] **Step 2: Write the failing fixture test**

```python
import json
from pathlib import Path

import pytest

from yom_awel.domain.contracts import (
    ApplicationError,
    EvaluationResult,
    FeedbackResult,
    SkillsProfile,
    SubmissionOutcome,
)

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("evaluation-pass.json", EvaluationResult),
        ("evaluation-fail.json", EvaluationResult),
        ("feedback-generated.json", FeedbackResult),
        ("feedback-fallback.json", FeedbackResult),
        ("submission-pass.json", SubmissionOutcome),
        ("submission-fail.json", SubmissionOutcome),
        ("submission-duplicate.json", SubmissionOutcome),
        ("skills-profile.json", SkillsProfile),
        ("application-error.json", ApplicationError),
    ],
)
def test_canonical_fixture_validates(filename: str, model: type) -> None:
    payload = json.loads((ROOT / "contracts" / "fixtures" / filename).read_text())
    assert model.model_validate(payload).model_dump(mode="json") == payload
```

- [ ] **Step 3: Run the test and confirm failure**

Run: `cd services/api && uv run pytest tests/contract/test_contract_fixtures.py -q`

Expected: FAIL because contract models and fixtures do not exist.

- [ ] **Step 4: Define canonical enums**

Create string enums with exact values:

```python
class LearnerStatus(StrEnum):
    ONBOARDING = "ONBOARDING"
    READY = "READY"
    IN_TASK = "IN_TASK"
    PROCESSING = "PROCESSING"
    NEEDS_RETRY = "NEEDS_RETRY"
    TASK_COMPLETED = "TASK_COMPLETED"
    PROGRAM_COMPLETED = "PROGRAM_COMPLETED"


class SubmissionStatus(StrEnum):
    RECEIVED = "RECEIVED"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

Also define `Language` with `ar-EG` and `en`, `Channel` with `web` and `telegram`, and stable application error categories.

- [ ] **Step 5: Define Pydantic contracts**

Implement constrained models for `ArtifactRef`, `TaskVersion`, `EvaluationCheck`, `EvaluationError`, `EvaluationResult`, `FeedbackResult`, `SkillSummary`, `SkillsProfile`, `SubmissionOutcome`, and `ApplicationError`. Enforce score `0..100`, non-negative durations, SHA-256 format, 5 MB maximum artifacts, and non-empty version identifiers.

- [ ] **Step 6: Create deterministic fixtures**

Use fixed UUIDs, timestamps, hashes, task version `clean-sales@1`, evaluator version `sales-cleaning@1`, prompt version `tarek-feedback@1`, and score combinations that exercise pass, fail, fallback, and duplicate outcomes. The duplicate fixture must be byte-for-byte equal to the original successful outcome except for no fields.

- [ ] **Step 7: Run contract tests**

Run:

```bash
cd services/api
uv run pytest tests/contract/test_contract_fixtures.py -q
uv run mypy src
uv run ruff check .
```

Expected: all commands pass.

- [ ] **Step 8: Generate JSON schemas**

Add `services/api/scripts/export_schemas.py` that writes sorted, stable schemas to `contracts/schemas/`. Test that rerunning the script produces no diff.

- [ ] **Step 9: Commit**

```bash
git add services/api contracts
git commit -m "feat: define canonical platform contracts"
```

### Task M2-2: Implement Domain Entities and Progression State Machine

**Files:**
- Create: `services/api/src/yom_awel/domain/entities.py`
- Create: `services/api/src/yom_awel/domain/state_machine.py`
- Create: `services/api/src/yom_awel/domain/errors.py`
- Test: `services/api/tests/domain/test_state_machine.py`
- Test: `services/api/tests/domain/test_skill_evidence.py`

**Interfaces:**
- Consumes: `LearnerStatus`, `EvaluationResult`, task/skill contracts.
- Produces: pure transition functions and auditable domain entities used by application services.

- [ ] **Step 1: Write invalid-transition tests**

```python
import pytest

from yom_awel.domain.enums import LearnerStatus
from yom_awel.domain.errors import InvalidTransition
from yom_awel.domain.state_machine import transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (LearnerStatus.ONBOARDING, LearnerStatus.PROCESSING),
        (LearnerStatus.READY, LearnerStatus.TASK_COMPLETED),
        (LearnerStatus.NEEDS_RETRY, LearnerStatus.PROGRAM_COMPLETED),
        (LearnerStatus.PROGRAM_COMPLETED, LearnerStatus.IN_TASK),
    ],
)
def test_invalid_transition_is_rejected(current, target) -> None:
    with pytest.raises(InvalidTransition):
        transition(current, target)
```

- [ ] **Step 2: Write progression authority tests**

Test that a failed evaluation produces `NEEDS_RETRY`, a passed evaluation produces `TASK_COMPLETED`, feedback fields are not accepted by the transition function, and a completed curriculum produces `PROGRAM_COMPLETED` only after a passed final task.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/domain -q`

Expected: FAIL because the domain modules do not exist.

- [ ] **Step 4: Implement domain errors and state table**

Create explicit allowed transition pairs matching the approved state diagram. `transition(current, target)` returns the target for allowed pairs and raises `InvalidTransition(code="invalid_transition", current=..., target=...)` otherwise.

- [ ] **Step 5: Implement immutable entities**

Use frozen dataclasses or frozen Pydantic models for published `TaskVersion`, completed `EvaluationRecord`, `FeedbackRecord`, `Attempt`, and `SkillEvidence`. Keep `LearnerProgress` mutation behind methods that increment an optimistic `version`.

- [ ] **Step 6: Implement skill evidence aggregation**

Aggregate only passed check evidence. Calculate display scores from stored weighted evidence and clamp output to `0..100`. Preserve source attempt, check ID, task version, and awarded/available points.

- [ ] **Step 7: Run domain tests and static checks**

Run:

```bash
cd services/api
uv run pytest tests/domain -q
uv run mypy src/yom_awel/domain
uv run ruff check src/yom_awel/domain tests/domain
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add services/api/src/yom_awel/domain services/api/tests/domain
git commit -m "feat: add learner progression domain"
```

### Task M2-3: Define Ports and In-Memory Unit of Work

**Files:**
- Create: `services/api/src/yom_awel/ports/repositories.py`
- Create: `services/api/src/yom_awel/ports/artifacts.py`
- Create: `services/api/src/yom_awel/ports/evaluation.py`
- Create: `services/api/src/yom_awel/ports/feedback.py`
- Create: `services/api/src/yom_awel/ports/unit_of_work.py`
- Create: `services/api/src/yom_awel/persistence/memory.py`
- Test: `services/api/tests/ports/test_memory_contract.py`

**Interfaces:**
- Consumes: domain entities/contracts.
- Produces: exact async protocols used by Members 3–5 and a fast reference adapter.

- [ ] **Step 1: Write the repository contract test**

Define a reusable test mixin that verifies create/get, uniqueness, learner scoping, optimistic version conflict, attempt ordering, idempotency lookup, and rollback.

- [ ] **Step 2: Run the contract test and confirm failure**

Run: `cd services/api && uv run pytest tests/ports/test_memory_contract.py -q`

Expected: FAIL because the ports and adapter do not exist.

- [ ] **Step 3: Define repository protocols**

Use async methods with exact names:

```python
class LearnerRepository(Protocol):
    async def get(self, learner_id: UUID) -> Learner | None: ...
    async def get_by_external_identity(
        self, provider: str, provider_subject: str
    ) -> Learner | None: ...
    async def add(self, learner: Learner) -> None: ...
    async def save_progress(self, progress: LearnerProgress, expected_version: int) -> None: ...


class SubmissionRepository(Protocol):
    async def get_by_idempotency_key(
        self, learner_id: UUID, key: str
    ) -> Submission | None: ...
    async def add(self, submission: Submission) -> None: ...
    async def save_outcome(self, outcome: SubmissionOutcome) -> None: ...
```

Define corresponding task, attempt, skill, outbox, artifact, evaluator, and feedback protocols.

- [ ] **Step 4: Define the unit of work**

Expose repositories as attributes and methods `__aenter__`, `__aexit__`, `commit`, and `rollback`. Application services receive a `Callable[[], UnitOfWork]` factory.

- [ ] **Step 5: Implement the in-memory adapter**

Use per-unit-of-work snapshots so rollback discards staged mutations. Enforce uniqueness and optimistic versions in the adapter rather than relying only on application code.

- [ ] **Step 6: Run contract tests**

Run: `cd services/api && uv run pytest tests/ports/test_memory_contract.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services/api/src/yom_awel/ports services/api/src/yom_awel/persistence/memory.py services/api/tests/ports
git commit -m "feat: define application ports and memory adapters"
```

### Task M2-4: Implement Application Use Cases and Idempotent Submission Processing

**Files:**
- Create: `services/api/src/yom_awel/application/commands.py`
- Create: `services/api/src/yom_awel/application/onboarding.py`
- Create: `services/api/src/yom_awel/application/tasks.py`
- Create: `services/api/src/yom_awel/application/submissions.py`
- Create: `services/api/src/yom_awel/application/profiles.py`
- Create: `services/api/src/yom_awel/application/admin.py`
- Test: `services/api/tests/application/test_process_submission.py`
- Test: `services/api/tests/application/test_onboarding.py`
- Test: `services/api/tests/application/test_profiles.py`

**Interfaces:**
- Consumes: unit of work, evaluator, feedback, artifact, clock, and ID ports.
- Produces: typed use cases invoked by Member 5 transport adapters.

- [ ] **Step 1: Write the duplicate-submission tests**

Test the same learner/key/hash twice returns one outcome and one attempt. Test the same learner/key with a different hash raises `IdempotencyConflict`. Test two concurrent passed submissions advance once.

- [ ] **Step 2: Write provider-fallback authority tests**

Use a feedback fake that raises timeout. Assert `ProcessSubmission` substitutes a fallback result, persists the deterministic evaluation, and advances solely from `evaluation.passed`.

- [ ] **Step 3: Run application tests and confirm failure**

Run: `cd services/api && uv run pytest tests/application -q`

Expected: FAIL because use cases do not exist.

- [ ] **Step 4: Implement command models**

Define `OnboardLearnerCommand`, `CreateUploadCommand`, `ProcessSubmissionCommand`, and `ResetDemoLearnerCommand`. `ProcessSubmissionCommand` contains learner ID, task version ID, artifact ID, artifact SHA-256, channel, idempotency key, optional learner note, and channel event ID.

- [ ] **Step 5: Implement submission orchestration**

Order operations exactly:

1. retrieve learner and active task;
2. validate artifact ownership and task version;
3. resolve existing idempotency key;
4. create received submission;
5. evaluate artifact;
6. persist immutable evaluation;
7. generate or fall back feedback;
8. create attempt and skill evidence;
9. advance from evaluation result;
10. record outbox events;
11. commit and return `SubmissionOutcome`.

- [ ] **Step 6: Implement onboarding, task, profile, and reset use cases**

Onboarding is idempotent by external identity. Profile derives from evidence. Reset requires an administrative actor flag and emits an audited event.

- [ ] **Step 7: Run application tests**

Run:

```bash
cd services/api
uv run pytest tests/application -q
uv run mypy src/yom_awel/application
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add services/api/src/yom_awel/application services/api/tests/application
git commit -m "feat: add idempotent learning use cases"
```

### Task M2-5: Implement SQLite and Local Artifact Adapters

**Files:**
- Create: `services/api/src/yom_awel/persistence/sqlite.py`
- Create: `services/api/src/yom_awel/persistence/local_artifacts.py`
- Create: `services/api/tests/persistence/test_sqlite_contract.py`
- Create: `services/api/tests/persistence/test_local_artifacts.py`

**Interfaces:**
- Consumes: repository/unit-of-work and artifact-store ports.
- Produces: zero-cloud local adapters used by CI and development.

- [ ] **Step 1: Parameterize the adapter contract suite**

Run the same repository assertions against memory and SQLite factories. Use a temporary database per test and enable foreign keys and WAL for integration tests.

- [ ] **Step 2: Write artifact path safety tests**

Assert original filenames containing `../`, absolute paths, Unicode separators, and repeated names never influence stored paths. Assert deletion and failed-write cleanup.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/persistence -q`

Expected: FAIL because SQLite/local adapters do not exist.

- [ ] **Step 4: Implement SQLite schema initialization and unit of work**

Use explicit SQL schema matching canonical tables, foreign keys, uniqueness, UTC timestamps, and transaction control. Do not create a second set of business rules in SQL triggers.

- [ ] **Step 5: Implement local artifact storage**

Under the configured artifact-storage root, use the learner UUID as the first path segment and artifact UUID as the filename. Keep the original filename only as sanitized metadata. Write to a temporary generated path, fsync/close, hash, then atomically rename.

- [ ] **Step 6: Run parity tests**

Run: `cd services/api && uv run pytest tests/ports tests/persistence -q`

Expected: memory and SQLite adapters pass identical contract behavior.

- [ ] **Step 7: Commit**

```bash
git add services/api/src/yom_awel/persistence services/api/tests/persistence
git commit -m "feat: add zero-cloud persistence adapters"
```

### Task M2-6: Create Supabase Schema, RLS, and Storage Policies

**Files:**
- Create: `supabase/config.toml`
- Create via `supabase migration new platform_schema`: the CLI-generated `platform_schema` migration in `supabase/migrations/`
- Create: `supabase/tests/database/rls.sql`
- Create: `docs/operations/data-retention.md`

**Interfaces:**
- Consumes: canonical entities and repository contract.
- Produces: Free-plan-compatible Postgres schema and private artifact policies.

- [ ] **Step 1: Discover the installed CLI commands**

Run:

```bash
supabase --version
supabase migration --help
supabase db --help
```

Record the version in the pull request. Use MCP equivalents when the CLI capability is unavailable.

- [ ] **Step 2: Create the migration through the CLI**

Run: `supabase migration new platform_schema`

Use the generated filename; never invent a timestamp.

- [ ] **Step 3: Write complete relational schema**

Create tables for learners, external identities, tasks, task versions, artifacts, submissions, evaluation results, feedback results, attempts, skill definitions, skill evidence, learner progress, and outbox events. Add foreign keys, unique constraints, checks, indexes, UTC defaults, and immutable-version protections documented in the spec.

- [ ] **Step 4: Enable RLS and grants**

Enable RLS on every exposed table. Add learner ownership policies using `(select auth.uid())`, and include both `USING` and `WITH CHECK` for updates. Revoke unnecessary public function/table privileges. Keep administrative operations in server-only paths.

- [ ] **Step 5: Configure private storage policies**

Create a private `submissions` bucket. Restrict object paths to generated learner/artifact IDs. Allow signed operations only through the backend workflow; do not grant public read access.

- [ ] **Step 6: Write SQL allow/deny tests**

Test learner A own read, learner B denial, anonymous denial, cross-user update denial, signed artifact ownership, and service operation boundaries.

- [ ] **Step 7: Write retention documentation**

Set artifact retention to 30 days for the prototype, attempts/evaluations retained for audit, and deletion behavior for learner requests. Explain that retention is configurable but not silently extended.

- [ ] **Step 8: Run migration and advisor verification**

Run the local migration from an empty database, execute SQL tests, and run Supabase security/performance advisors when a project is connected. Attach outputs to the PR.

- [ ] **Step 9: Commit**

```bash
git add supabase docs/operations/data-retention.md
git commit -m "feat: add secure Supabase persistence schema"
```

### Task M2-7: Implement Supabase Repository and Artifact Adapters

**Files:**
- Create: `services/api/src/yom_awel/persistence/supabase.py`
- Create: `services/api/src/yom_awel/persistence/supabase_artifacts.py`
- Create: `services/api/tests/persistence/test_supabase_contract.py`
- Create: `services/api/tests/persistence/test_supabase_artifacts.py`

**Interfaces:**
- Consumes: Supabase schema, repository/artifact ports, canonical contracts.
- Produces: cloud adapters selected by Member 5's composition root.

- [ ] **Step 1: Reuse the adapter contract suite**

Parameterize the existing contract tests with a Supabase test project or local Supabase environment. Mark them `integration` but keep behavior identical to memory/SQLite.

- [ ] **Step 2: Write signed-upload tests**

Assert generated object path, 5 MB metadata limit, ownership, short expiry, private bucket, content hash verification, and rejection of missing/wrong-owner artifacts.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest -m integration tests/persistence/test_supabase_contract.py -q`

Expected: FAIL because adapters do not exist.

- [ ] **Step 4: Implement typed row mappers**

Map database rows to domain/contracts in focused functions. Reject unexpected nulls or enum values with stable persistence errors rather than leaking raw provider payloads.

- [ ] **Step 5: Implement transactional repository behavior**

Use one application transaction for attempt, skill evidence, progress, and outbox mutations. Enforce idempotency and optimistic versions at the database level.

- [ ] **Step 6: Implement private artifact operations**

Create signed upload/download operations, metadata verification, hash checks, and deletion. Never return service-role credentials or public bucket URLs.

- [ ] **Step 7: Run full adapter parity and RLS tests**

Run:

```bash
cd services/api
uv run pytest tests/ports tests/persistence -q
```

Expected: memory, SQLite, and Supabase satisfy the same observable contract.

- [ ] **Step 8: Commit**

```bash
git add services/api/src/yom_awel/persistence services/api/tests/persistence
git commit -m "feat: add Supabase repository adapters"
```

## Member 2 Completion Gate

- Canonical fixtures validate and are consumed by Members 3–5.
- Domain/application strict type checks pass without framework imports.
- Idempotency and concurrency tests pass.
- Memory, SQLite, and Supabase adapters pass the same contract suite.
- Migrations apply from empty state and RLS allow/deny tests pass.
- Security/performance advisor results contain no unaccepted error.
- Member 5 approves transport-facing contracts.
- Member 1 approves progression/profile semantics.
