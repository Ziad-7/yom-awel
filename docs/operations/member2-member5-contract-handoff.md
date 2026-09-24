# Member 2 to Member 5 Contract Handoff

## Scope

This handoff is the local integration contract for artifact uploads and current
task assignment. It is ready for Member 5's local adapter/client work. It does
not complete issue #26, issue #27, cloud RLS, evaluator integration, or a
Vercel release gate.

## Artifact upload and completion

Construct `CreateUploadCommand` with the learner UUID, non-empty filename,
canonical content type, size in bytes (0 through 5 MiB), and a lowercase
64-character SHA-256 digest. For example:

```python
command = CreateUploadCommand(
    learner_id=learner_id,
    filename="sales.csv",
    content_type="text/csv",
    size_bytes=size_bytes,
    artifact_sha256=sha256,
)
authorization = await CreateArtifactUpload(factory, clock, id_gen).execute(command)
```

The only canonical MIME values are:

| Filename extension | `content_type` |
| --- | --- |
| `.csv` | `text/csv` |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |

Extensions are case-insensitive, but the MIME string is exact. Do not send a
browser-provided alias or infer a different type. `filename` and `content_type`
must match before authorization reserves metadata.

`UploadAuthorizationResult` returns `artifact_id`, `expires_in_seconds`,
`upload_url`, optional `upload_token`, and `headers`. Preserve the returned
headers and upload bytes that match the authorized size, SHA-256, and content
type. Then call `CompleteArtifactUpload(...).execute(learner_id, artifact_id)`;
it returns `UploadCompletionResult(artifact_id=...)`. The content type is part
of the immutable reservation, provider metadata, authorization outbox payload,
and completion verification.

Exact error contract for this path:

- Pydantic rejects an unsupported MIME value and reports `content_type must
  match filename` when a supported MIME does not match the filename extension.
- `CreateArtifactUpload` raises `DomainError(code="not_found", message="Learner
  progress not found")` when progress is absent.
- It raises `DomainError(code="invalid_status", message="Learner is not in a
  task")` unless the learner is `IN_TASK` or `NEEDS_RETRY`.
- It raises `DomainError(code="invalid_artifact", message="Artifact invalid")`
  for an empty filename or a file over 5 MiB.
- A conflicting immutable reservation raises
  `UniqueConstraintViolation(code="unique_constraint")`.
- Completion can raise `ArtifactNotReady(code="artifact_not_ready")`,
  `LearnerScopeViolation(code="learner_scope_violation")`, or
  `ArtifactIntegrityFailure(code="artifact_integrity_failure")`. Treat these as
  failed completion; do not submit the artifact.

## Current-task assignment

Use the application service, not a repository write:

```python
result = await AssignCurrentTask(factory, clock).execute(learner_id)
```

The constructor is `AssignCurrentTask(uow_factory, clock, task_id="clean-sales")`.
It returns `CurrentTaskResult(status: str, task: TaskVersion | None)`. A `READY`
learner receives the currently published `clean-sales` task and one optimistic
progress write to `IN_TASK`. Replays and established `IN_TASK`, `PROCESSING`,
`NEEDS_RETRY`, or `TASK_COMPLETED` states return their current result without a
new progression. On one optimistic conflict, the service rereads and returns a
competing winner only when it has `current_task_id`; otherwise it re-raises the
original `OptimisticConflict`.

Exact error contract:

- `DomainError(code="not_found", message="Learner progress not found")` when
  progress is absent.
- `DomainError(code="task_not_found", message="Task not found")` when a READY
  learner has no published `clean-sales` task.
- `OptimisticConflict(code="optimistic_conflict", message="learner_progress
  changed concurrently")` when the retry read has no winner or no winner
  `current_task_id`.

## Migration and rollback order

1. Apply `20260924150000_artifact_content_type.sql`. It adds nullable
   `artifacts.content_type`, backfills `.csv` and `.xlsx` legacy rows, limits
   non-null values to the two canonical MIME strings, and creates
   `reserve_artifact_v2`.
2. Deploy consumers that call `reserve_artifact_v2` and include `content_type`
   in reservation, upload metadata, and completion checks.
3. Keep `reserve_artifact` and the nullable column during rollout. This is the
   rollback path: revert callers to the original RPC without dropping the
   column, constraint, or backfilled data.
4. Do not issue a destructive contraction as part of this gate. Any later
   `NOT NULL` or legacy-RPC removal requires a separately reviewed migration
   after all consumers are upgraded.

## Deferred gates

The following are explicitly pending: full cloud composition/factory wiring,
live Supabase RLS execution and authorization proof, Member 4 evaluator
binding, and Vercel preview/production configuration and release verification.
They must not be represented as complete by this handoff.
