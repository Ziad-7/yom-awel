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
`PURGED` audit record. A missing object is treated as an idempotent successful
delete. A storage failure marks `PURGE_FAILED`, writes an audit record, and
leaves the row retryable on the next bounded run. A stale claim can be
reclaimed after its lease expires; two workers cannot claim the same row at
once.

Learner deletion requests are recorded as `DELETE_REQUESTED`. The server first
reconciles application records and private objects, then records the
reconciliation audit event before removing an expired anonymous Auth identity.
Audit metadata contains IDs, action, actor, timestamps, and redacted error
details; it never stores raw artifacts or provider secrets.

The GitHub workflow runs once daily and supports manual dispatch using only a
standard public-repository runner with `contents: read`. It has no required
secrets and performs a safe no-op when no local/server cleanup backend is
configured. The recovery path is manual execution of the bounded cleanup
against the server's service-role environment; repeated failures are visible
in the workflow result. No paid scheduler, Supabase Pro feature, or hosted
migration is required.
