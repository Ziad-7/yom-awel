-- Generated with `supabase migration new rls_hardening` and reviewed against
-- the local Supabase roles.  This is a forward-only privilege hardening
-- migration; the schema and ownership policies remain in the earlier
-- migrations.

-- Every application table stays RLS protected.  The cleanup queue was added
-- by the recovery migration and is deliberately included here as well.
do $$
declare
    table_name text;
begin
    foreach table_name in array array[
        'learners', 'external_identities', 'tasks', 'task_versions', 'artifacts',
        'submissions', 'evaluation_results', 'feedback_results', 'attempts',
        'skill_definitions', 'skill_evidence', 'learner_progress', 'outbox_events',
        'retention_audit', 'learner_deletion_requests', 'artifact_cleanup_queue'
    ] loop
        execute format('alter table public.%I enable row level security', table_name);
        execute format(
            'revoke all on table public.%I from public, anon, authenticated',
            table_name
        );
        execute format(
            'grant all on table public.%I to service_role',
            table_name
        );
        execute format(
            'revoke insert, update, delete, truncate, references, trigger on table public.%I from anon, authenticated',
            table_name
        );
    end loop;
end;
$$;

grant usage on schema public to authenticated, service_role;

-- Authenticated learners may read only their own rows.  The corresponding
-- ownership policies use current_learner_id(); no client role receives a
-- write privilege.  Catalogs are shared but task versions expose published
-- content only through the policy defined by the schema migration.
grant select on public.learners,
    public.external_identities,
    public.artifacts,
    public.submissions,
    public.evaluation_results,
    public.feedback_results,
    public.attempts,
    public.skill_evidence,
    public.learner_progress,
    public.learner_deletion_requests,
    public.tasks,
    public.task_versions,
    public.skill_definitions
    to authenticated;

-- These internal tables remain inaccessible even to an authenticated client:
-- they contain queue state, retention details, and event payloads.
revoke all on table public.outbox_events,
    public.retention_audit,
    public.artifact_cleanup_queue
    from public, anon, authenticated;

-- Storage is private and backend-only.  There are intentionally no client
-- policies on storage.objects; signed operations use service_role instead.
alter table storage.objects enable row level security;
revoke all on table storage.objects from public, anon, authenticated;
grant all on table storage.objects to service_role;

-- current_learner_id is the only client-callable helper.  It resolves the
-- authenticated JWT subject and is not a service RPC.
revoke all on function public.current_learner_id() from public, anon, service_role;
grant execute on function public.current_learner_id() to authenticated;
revoke all on function public.prevent_published_task_version_mutation() from public, anon, authenticated, service_role;
grant execute on function public.prevent_published_task_version_mutation() to service_role;

-- All current public functions other than current_learner_id are server
-- workflows (including reservation, finalization, release, and cleanup
-- functions).  Revoke the default PUBLIC EXECUTE grant and allow only the
-- server role.  Using pg_proc keeps this forward migration complete when the
-- recovery migration adds another service RPC.
do $$
declare
    function_signature text;
begin
    for function_signature in
        select p.oid::regprocedure::text
        from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public'
          and p.prosecdef
          and p.proname <> 'current_learner_id'
    loop
        execute format(
            'revoke all on function %s from public, anon, authenticated, service_role',
            function_signature
        );
        execute format(
            'grant execute on function %s to service_role',
            function_signature
        );
    end loop;
end;
$$;
