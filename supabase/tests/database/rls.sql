-- Local/static RLS assertions for the platform migration.
-- Execute against a local Supabase database with two authenticated JWTs.  No
-- hosted project or service-role credential is required by this repository.

-- The migration must expose RLS on every application table.
select c.relname, c.relrowsecurity
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in (
    'learners', 'external_identities', 'tasks', 'task_versions', 'artifacts',
    'submissions', 'evaluation_results', 'feedback_results', 'attempts',
    'skill_definitions', 'skill_evidence', 'learner_progress', 'outbox_events',
    'retention_audit', 'learner_deletion_requests'
  );

-- Ownership policy checks (replace UUIDs with seeded local rows).
begin;
select set_config('request.jwt.claim.sub', '<learner-a-auth-uid>', true);
select set_config('request.jwt.claim.role', 'authenticated', true);
-- Learner A can read its own learner/progress/artifact rows.
select count(*) from public.learners where learner_id = public.current_learner_id();
select count(*) from public.learner_progress where learner_id = public.current_learner_id();
select count(*) from public.artifacts where learner_id = public.current_learner_id();
-- Learner A cannot see Learner B's rows.
select count(*) = 0 from public.learners where learner_id = '<learner-b-id>'::uuid;
select count(*) = 0 from public.artifacts where learner_id = '<learner-b-id>'::uuid;
rollback;

-- Anonymous and direct client mutation checks are deny-by-default.
begin;
select set_config('request.jwt.claim.role', 'anon', true);
select count(*) = 0 from public.learners;
select count(*) = 0 from public.submissions;
rollback;

-- UPDATE must enforce both visibility and ownership.  A direct cross-user
-- update must affect zero rows, never silently move an artifact.
begin;
select set_config('request.jwt.claim.sub', '<learner-a-auth-uid>', true);
select set_config('request.jwt.claim.role', 'authenticated', true);
update public.artifacts
set learner_id = '<learner-b-id>'::uuid
where artifact_id = '<learner-b-artifact-id>'::uuid;
rollback;

-- Storage is private and has no authenticated client policies. Upload,
-- download, and delete are backend-only signed operations.
select count(*) = 0 as no_client_storage_policies
from pg_policies
where schemaname = 'storage' and tablename = 'objects'
  and roles @> array['authenticated'::name];
