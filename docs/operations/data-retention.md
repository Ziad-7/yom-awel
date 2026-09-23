# Artifact retention and deletion

Raw submission artifacts are retained for 30 days from upload. Evaluation,
feedback, attempt, skill-evidence, and outbox metadata remain for audit after
the raw file is removed. Retention is configured in the migration and may only
be changed through a reviewed migration/configuration change.

The `submissions` bucket is private. Browsers never receive table or storage
DML privileges and there are no client storage policies for upload, update, or
delete. The backend performs ownership checks and creates short-lived signed
upload/download operations using generated `learner UUID / artifact UUID`
paths; service-role credentials remain server-only.

The server claims expired artifact rows with a short lease, deletes the object
from the private `submissions` bucket, then marks the row `PURGED` and writes a
`PURGED` audit record. The orphan cleanup queue is drained first so failed
metadata/object transactions are reconciled before normal expiry. A missing
object (HTTP 404) is treated as an idempotent successful delete. A storage
failure marks `PURGE_FAILED`, writes an audit record, and leaves the row
retryable on the next bounded run. A stale claim can be reclaimed after its
lease expires; two workers cannot claim the same row at once.

Learner deletion requests are unique and idempotent by the requested learner
UUID. The server locks the request and external-identity rows, blocks identity
provider/subject/anonymity changes during an active claim, and refuses erasure
while an artifact or orphan queue entry is unresolved. It inserts the audit
tombstone before erasing `skill_evidence`, `attempts`, evaluation/feedback,
submissions, learner-owned outbox events, artifacts, and finally the learner.
Queue entries and tombstones are intentionally retained. Auth admin deletion is
the final step and treats an already-missing user as success. Audit metadata
contains only historical UUIDs, action, actor, timestamps, and redacted error
details; it never stores raw artifacts, learner content, or provider secrets.

The GitHub workflow runs once daily and supports manual dispatch using only a
standard public-repository runner with `contents: read` and immutable action
SHAs. It uses encrypted `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
secrets, performs a safe no-op when they are absent, and never requires a paid
runner, scheduler, or Supabase Pro feature. A UUID worker owner and bounded
batch/lease prevent unbounded work; the workflow is serialized with a
concurrency group. A non-zero result is the alert for repeated failures.

Ownership is with the API/platform operator. Evidence for each run is the
workflow result plus `retention_audit` rows (claim, purge success/failure,
deletion request, and reconciliation). Manual recovery is:

```bash
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
  uv run --project services/api python services/api/scripts/purge_expired_artifacts.py \
  --cleanup-queue --limit 100
```

Run it again after correcting storage/provider failures; leases and idempotent
404 handling make retries safe. Retention is configurable only through a
reviewed migration/configuration change and is never silently extended.
