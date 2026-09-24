# Member 2 / Member 5 Contract Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immutable artifact media-type verification and a public idempotent clean-sales assignment use case that Member 5 can consume without transport-owned persistence logic.

**Architecture:** Expand the canonical artifact contract first, then update local and Supabase persistence without a destructive database contraction. Add assignment as one application service over existing repositories and optimistic progress writes. Keep cloud composition, live RLS execution, evaluator binding, and deployment outside this branch.

**Tech Stack:** Python 3.12, Pydantic 2, asyncio, SQLite, PostgreSQL/Supabase SQL migrations, pytest, Ruff, mypy, pre-commit.

**Spec:** `docs/superpowers/specs/2026-09-24-member2-member5-contract-gate-design.md`

## Global Constraints

- Canonical media types are exactly `text/csv` and `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- Filename extension and content type must agree.
- Artifact ID, learner ID, filename, size, SHA-256, and content type are immutable after authorization.
- The database transition is expand/backfill only; do not add `NOT NULL` or delete legacy data.
- Assignment owns `READY -> IN_TASK`, selects published `clean-sales`, and is idempotent under repetition and concurrency.
- Domain and application modules must not import FastAPI, Supabase SDKs, or transport modules.
- Add no paid service or new product dependency.
- Do not mark issue #26, issue #27, cloud RLS, Member 4 integration, or Vercel release complete.

## Review Focus

- A `.csv` filename paired with XLSX media type must fail before metadata is reserved.
- A retry that changes only `content_type` must not reuse or overwrite the original artifact.
- A legacy row with null media type and a valid extension must map deterministically; an unknown extension must fail closed.
- Two assignment calls racing from `READY` must converge on one `clean-sales` assignment and one progress version advance.
- Assignment after `NEEDS_RETRY`, `PROCESSING`, or completion must return current state without selecting or mutating another task.

---

### Task 1: Canonical artifact media-type contract

**Files:**
- Modify: `services/api/src/yom_awel/domain/contracts.py`
- Modify: `services/api/src/yom_awel/domain/entities.py`
- Modify: `services/api/src/yom_awel/application/commands.py`
- Modify: `services/api/src/yom_awel/application/submissions.py`
- Modify: `services/api/src/yom_awel/application/tasks.py`
- Test: `services/api/tests/contract/test_contract_fixtures.py`
- Test: `services/api/tests/application/test_other.py`

**Interfaces:**
- Produces: `ArtifactContentType`, `artifact_content_type(filename: str) -> ArtifactContentType`, and required `content_type` fields on `ArtifactRef`, `Artifact`, and `CreateUploadCommand`.
- Consumes: existing Pydantic frozen/forbid model conventions and `CreateArtifactUpload.execute`.

- [ ] **Step 1: Write failing model and application tests**

Add tests that construct CSV and XLSX artifacts with matching canonical values, reject missing/unknown/mismatched values, assert `CreateArtifactUpload` persists the value in the authorized artifact and outbox payload, and assert `ProcessSubmission` copies it into `ArtifactRef`.

```python
def test_artifact_rejects_extension_content_type_mismatch() -> None:
    with pytest.raises(ValidationError):
        Artifact(
            artifact_id=uuid4(),
            learner_id=uuid4(),
            filename="sales.csv",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=1,
            sha256="a" * 64,
        )
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
uv run --project services/api pytest services/api/tests/contract/test_contract_fixtures.py services/api/tests/application/test_other.py -q
```

Expected: failures because `content_type` and `ArtifactContentType` are not defined.

- [ ] **Step 3: Implement the minimal canonical contract**

In `domain/contracts.py`, define the literal alias and deterministic extension mapping:

```python
ArtifactContentType = Literal[
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]

def artifact_content_type(filename: str) -> ArtifactContentType:
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        return "text/csv"
    if lowered.endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    raise ValueError("artifact filename must end in .csv or .xlsx")
```

Add a model validator to `ArtifactRef` and `Artifact` that requires equality with `artifact_content_type(filename)`. Add the required field to `CreateUploadCommand`, apply the same validator, pass it into `Artifact`, include it in the authorization outbox payload, and include it when `ProcessSubmission` creates `ArtifactRef`.

- [ ] **Step 4: Update existing artifact fixtures mechanically**

Every existing `Artifact(...)`, `ArtifactRef(...)`, and `CreateUploadCommand(...)` fixture receives the canonical value matching its filename. Rename invalid test filenames such as `test.txt` to `test.csv` unless the test specifically asserts rejection.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 1 command again. Expected: all selected tests pass.

- [ ] **Step 6: Commit Task 1**

```bash
git add services/api/src/yom_awel/domain services/api/src/yom_awel/application services/api/tests/contract services/api/tests/application
git commit -m "feat(contracts): bind artifact media type"
```

### Task 2: Compatibility-safe SQLite and Supabase artifact persistence

**Files:**
- Modify: `services/api/src/yom_awel/persistence/memory.py`
- Modify: `services/api/src/yom_awel/persistence/sqlite.py`
- Modify: `services/api/src/yom_awel/persistence/local_artifacts.py`
- Modify: `services/api/src/yom_awel/persistence/supabase_artifacts.py`
- Create: `supabase/migrations/20260924150000_artifact_content_type.sql`
- Test: `services/api/tests/ports/test_memory_contract.py`
- Test: `services/api/tests/persistence/test_sqlite_contract.py`
- Test: `services/api/tests/persistence/test_local_artifacts.py`
- Test: `services/api/tests/persistence/test_supabase_artifacts.py`
- Test: `services/api/tests/persistence/test_migrations.py`

**Interfaces:**
- Consumes: required `Artifact.content_type` and `artifact_content_type(filename)` from Task 1.
- Produces: persisted/returned `content_type`, `reserve_artifact_v2` SQL RPC, and completion verification against immutable metadata.

- [ ] **Step 1: Write failing adapter contract tests**

Add tests proving:

```python
assert loaded.content_type == "text/csv"
```

for memory, local, and SQLite adapters; a second authorization with a different media type raises the existing uniqueness/idempotency error; Supabase row mapping rejects unexpected or mismatched `content_type`; signed upload metadata contains `content_type`; and completion rejects content whose authorized media type differs from returned storage metadata.

Extend the test storage protocol/fake with:

```python
async def object_metadata(self, bucket: str, path: str) -> Mapping[str, object]: ...
```

returning `content_type`, `size_bytes`, and `sha256` for the uploaded object.

- [ ] **Step 2: Write failing migration tests**

Add an SQLite legacy-database test that creates the pre-change artifacts table, inserts `legacy.csv`, opens the current factory, and expects `text/csv`. Add SQL assertions that the new Supabase migration adds/backfills `content_type`, creates `reserve_artifact_v2`, compares `content_type` during retry, and does not add `NOT NULL`.

- [ ] **Step 3: Run persistence tests and verify RED**

```bash
uv run --project services/api pytest services/api/tests/ports/test_memory_contract.py services/api/tests/persistence/test_sqlite_contract.py services/api/tests/persistence/test_local_artifacts.py services/api/tests/persistence/test_supabase_artifacts.py services/api/tests/persistence/test_migrations.py -q
```

Expected: failures for the missing column, row key, storage metadata method, and v2 RPC.

- [ ] **Step 4: Implement SQLite expansion and mapping**

Add nullable `content_type TEXT` to the SQLite schema. During factory initialization, inspect `PRAGMA table_info(artifacts)`; if absent, run `ALTER TABLE artifacts ADD COLUMN content_type TEXT`, then backfill valid `.csv`/`.xlsx` rows. Update all SELECT/INSERT/UPDATE statements and `_artifact` mapping. For a legacy null, call `artifact_content_type(filename)`; unknown extensions raise the adapter's stable integrity error.

- [ ] **Step 5: Implement Supabase expansion and v2 reservation**

The migration must:

```sql
alter table public.artifacts add column if not exists content_type text;
update public.artifacts
set content_type = case
  when lower(filename) like '%.csv' then 'text/csv'
  when lower(filename) like '%.xlsx' then 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
end
where content_type is null;
alter table public.artifacts add constraint artifacts_content_type_check
check (content_type is null or content_type in (
  'text/csv',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
));
```

Create `public.reserve_artifact_v2` with the existing reservation arguments plus `p_content_type text`. Validate extension/type agreement, compare content type on existing rows, and insert it for new rows. Keep the old `reserve_artifact` RPC and nullable column for rollback compatibility. Revoke public execution and grant only the existing service role used by the prior RPC.

- [ ] **Step 6: Implement Supabase adapter verification**

Add `content_type` to `_ARTIFACT_KEYS`, reserved rows, cleanup rows where appropriate, and signed upload metadata. Before activation, request object metadata and compare canonical media type, size, and SHA-256; then download and independently verify byte length/hash. Any mismatch raises `ArtifactIntegrityFailure` before `activate_artifact`.

- [ ] **Step 7: Run persistence tests and verify GREEN**

Run the Task 2 command again. Expected: all selected tests pass.

- [ ] **Step 8: Commit Task 2**

```bash
git add services/api/src/yom_awel/persistence services/api/tests/ports services/api/tests/persistence supabase/migrations/20260924150000_artifact_content_type.sql
git commit -m "feat(persistence): verify immutable artifact media type"
```

### Task 3: Idempotent current-task assignment use case

**Files:**
- Modify: `services/api/src/yom_awel/application/tasks.py`
- Test: `services/api/tests/application/test_task_assignment.py`

**Interfaces:**
- Produces: `AssignCurrentTask(uow_factory, clock, task_id="clean-sales")` and `async execute(learner_id: UUID) -> CurrentTaskResult`.
- Consumes: `LearnerRepository.get_progress/save_progress`, `TaskRepository.get_current_published_version`, `LearnerProgress`, `transition`, `OptimisticConflict`, and the existing `Clock` port.

- [ ] **Step 1: Write failing assignment tests**

Cover READY assignment, repeated call, existing IN_TASK/PROCESSING/NEEDS_RETRY/TASK_COMPLETED return, missing learner, missing published task, and a factory wrapper that injects one `OptimisticConflict` while committing a competing winner.

```python
result = await AssignCurrentTask(factory, clock).execute(learner_id)
assert result.status == "IN_TASK"
assert result.task is not None
assert result.task.task_id == "clean-sales"
```

- [ ] **Step 2: Run tests and verify RED**

```bash
uv run --project services/api pytest services/api/tests/application/test_task_assignment.py -q
```

Expected: import failure because `AssignCurrentTask` does not exist.

- [ ] **Step 3: Implement minimal assignment service**

Read progress and return the existing `GetCurrentTask` result when status is not `READY`. For `READY`, load the current published `clean-sales` version, create a progress copy with `IN_TASK`, stable task ID, version + 1, and `clock.now()`, then save with `expected_version=progress.version`. On one `OptimisticConflict`, reopen a unit of work and return the winner if it has a current task; otherwise re-raise. Commit only the successful mutation.

- [ ] **Step 4: Run assignment and application suites**

```bash
uv run --project services/api pytest services/api/tests/application/test_task_assignment.py services/api/tests/application -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add services/api/src/yom_awel/application/tasks.py services/api/tests/application/test_task_assignment.py
git commit -m "feat(application): assign current task idempotently"
```

### Task 4: Contract exports, handoff, and full verification

**Files:**
- Modify if generated: `contracts/schemas/*.json`
- Modify: `docs/team/member-2-domain-persistence.md`
- Create: `docs/operations/member2-member5-contract-handoff.md`

**Interfaces:**
- Consumes: Tasks 1–3 public contract and verification commands.
- Produces: reviewable Member 5 handoff with constructor, canonical values, migration order, error codes, and deferred gates.

- [ ] **Step 1: Export schemas and inspect drift**

```bash
uv run --project services/api python services/api/scripts/export_schemas.py
git diff -- contracts/schemas
```

Commit only deterministic schema changes caused by the canonical models.

- [ ] **Step 2: Document Member 5 consumption**

Document:

```text
CreateUploadCommand(..., filename="sales.csv", content_type="text/csv")
AssignCurrentTask(factory, clock).execute(learner_id)
```

Include the exact errors, migration/rollback sequence, and explicit statement that full cloud composition/RLS/evaluator/Vercel remain pending.

- [ ] **Step 3: Run complete local verification**

```bash
uv lock --check --project services/api
uv run --project services/api pre-commit run --all-files
uv run --project services/api ruff format --check services/api tools/quality
uv run --project services/api ruff check services/api tools/quality
uv run --project services/api mypy --config-file services/api/pyproject.toml services/api/src/yom_awel
uv run --project services/api pytest -q
uv run --project services/api python services/api/scripts/export_schemas.py
git diff --exit-code
```

Expected: every command exits 0; pytest reports zero failures; schema export leaves no diff.

- [ ] **Step 4: Commit documentation and generated contracts**

```bash
git add contracts/schemas docs/team/member-2-domain-persistence.md docs/operations/member2-member5-contract-handoff.md
git commit -m "docs(contracts): publish member5 integration handoff"
```

- [ ] **Step 5: Push and request Member 5 review**

Push `codex/member2-member5-contract-gate`, open a PR to `main`, and comment on PR #22 plus issue #26 with the PR URL. Request Member 5 to review canonical MIME values, authorization/completion fields, `AssignCurrentTask` consumption, and whether its local starter can be removed in its next integration PR. Do not merge until that requested review is received or the user explicitly overrides the review gate.
