# Member 2 / Member 5 Contract Gate — Design

## Purpose

Give Member 5 two stable Member 2-owned interfaces needed for later cloud integration without coupling transport code to persistence details:

1. immutable artifact media type from upload authorization through completion; and
2. idempotent assignment of the current published task.

This change starts from `main` commit `244a8a18a5b066751026e97133af1750c49b27fe`. It does not claim that the complete Supabase composition, live RLS gate, Member 4 evaluator, or Vercel release is finished.

## Scope

### Immutable artifact media type

- Add required `content_type` to `CreateUploadCommand`, `Artifact`, and artifact references consumed by evaluation.
- Accept exactly the two canonical v1 values:
  - `text/csv`
  - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Require filename extension and canonical media type to agree.
- Include content type in local and Supabase upload authorization metadata.
- At completion, compare artifact ID, learner ID, filename, size, SHA-256, and content type with the authorized values before activation.
- A retry with identical metadata is idempotent. A retry that changes any immutable field fails without overwriting the existing object or metadata.

### Compatibility-safe persistence

- Add a nullable `content_type` database column first and backfill existing rows from their validated `.csv` or `.xlsx` filename.
- New application writes always provide a canonical non-null value.
- Readers accept legacy null rows only by deriving the canonical value from a valid filename. Unknown extensions fail closed.
- Do not add the final database `NOT NULL` contraction in this change. That can happen only after deployed readers and writers use the expanded contract.
- SQLite receives the same field and behavior so local and cloud adapter contract tests remain aligned.

### Public task assignment use case

- Add `AssignCurrentTask` in the application layer.
- Input is a learner ID; output is the current task result.
- If the learner is already `IN_TASK`, `PROCESSING`, `NEEDS_RETRY`, or completed, return the existing result without mutation.
- If the learner is `READY`, select the current published version of `clean-sales`, assign its stable task ID, and transition once to `IN_TASK` using optimistic compare-and-swap.
- Concurrent calls either return the winner's assignment or retry one read after a version conflict; they never create two active assignments.
- If no published task exists, return a stable non-retryable `task_not_found` error.
- Transport code calls this use case after onboarding; it does not write repositories or progression directly.

## Interfaces and ownership

- Domain/application/ports/persistence/migrations remain Member 2-owned.
- Member 5 consumes the application use case and generated OpenAPI result but does not duplicate assignment or media-type rules.
- Member 4 continues to own spreadsheet safety and grading. This change verifies upload identity and immutable metadata, not task-specific workbook semantics.
- Telegram and web use the same artifact and assignment contracts.

## Error behavior

- Media type/extension mismatch: `artifact_type_mismatch`, validation, non-retryable.
- Uploaded bytes or immutable metadata mismatch: `artifact_integrity_failure`, validation, non-retryable.
- Conflicting retry metadata: `idempotency_conflict`, domain conflict, non-retryable.
- Missing published task: `task_not_found`, domain, non-retryable.
- Progress compare-and-swap conflict is retried once inside the use case; a repeated conflict returns the existing stable conflict error.
- Provider messages and credentials never cross the application boundary.

## Migration and rollback

Forward order:

1. apply the nullable-column/backfill migration;
2. deploy readers that understand the field;
3. deploy writers that always populate it;
4. let Member 5 bind the new use case and contract.

Rollback removes the new application behavior while leaving the nullable column in place. No stored artifact or learner progress is deleted. The later `NOT NULL` contraction is explicitly outside this change.

## Verification

- Model tests reject missing, unknown, or extension-mismatched media types.
- SQLite and Supabase artifact contract tests cover identical retries, changed-media retries, byte/hash/size mismatches, and legacy backfill reads.
- Migration smoke tests prove empty-database application and preservation/backfill of existing artifact rows.
- Assignment tests cover READY, already assigned, no published task, concurrent calls, and repeated idempotent calls.
- Existing repository contract, application, migration, pre-commit, and full pytest suites must pass.
- Member 5 reviews the PR specifically for transport consumability and confirms removal of its local assignment workaround can happen in a later integration PR.

## Deferred work

- Complete real Supabase `UnitOfWorkFactory` composition and request-scoped client wiring.
- Live anonymous-only RLS and Storage tests requiring an isolated Supabase project.
- Member 4 evaluator binding.
- Vercel preview, browser acceptance, and production promotion.

These remain tracked by issues #26 and #27 and must stay release blockers.
