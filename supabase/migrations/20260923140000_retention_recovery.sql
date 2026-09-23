-- Forward retention recovery hardening.
-- This migration intentionally leaves 20260921191239_artifact_cleanup_recovery.sql
-- unchanged.  Historical audit and queue rows must survive learner erasure.
begin;

-- Audit rows are historical tombstones, not ownership rows.  Keep the
-- original UUIDs after the learner/artifact rows are removed.
alter table public.retention_audit
    drop constraint if exists retention_audit_artifact_id_fkey,
    drop constraint if exists retention_audit_learner_id_fkey;
alter table public.retention_audit add column if not exists requested_learner_id uuid;
update public.retention_audit
set requested_learner_id = coalesce(
    requested_learner_id,
    learner_id,
    artifact_id,
    md5('retention-audit:' || audit_id::text)::uuid
);
-- Keep the earliest request tombstone deterministically before adding its
-- uniqueness index.  Other historical purge/reconcile audit events remain.
with duplicates as (
    select audit_id,
           row_number() over (
               partition by requested_learner_id order by created_at, audit_id
           ) as row_number
    from public.retention_audit
    where action = 'DELETE_REQUESTED'
)
delete from public.retention_audit a
using duplicates d
where a.audit_id = d.audit_id and d.row_number > 1;
alter table public.retention_audit alter column requested_learner_id set not null;
create unique index if not exists retention_audit_delete_tombstone_unique
    on public.retention_audit(requested_learner_id)
    where action = 'DELETE_REQUESTED';

-- Anonymous Auth ownership is explicit before legacy request backfill.
alter table public.external_identities
    add column if not exists is_anonymous boolean not null default false;

-- A deletion request is the durable idempotency tombstone.  Its learner FK is
-- nulled when erasure succeeds, while requested_learner_id remains unique.
alter table public.learner_deletion_requests
    add column if not exists requested_learner_id uuid,
    add column if not exists auth_user_id uuid,
    add column if not exists auth_deleted_at timestamptz,
    add column if not exists lease_owner text,
    add column if not exists lease_expires_at timestamptz;
update public.learner_deletion_requests
set requested_learner_id = coalesce(requested_learner_id, learner_id);
with duplicates as (
    select request_id,
           row_number() over (
               partition by requested_learner_id order by requested_at, request_id
           ) as row_number
    from public.learner_deletion_requests
)
delete from public.learner_deletion_requests r
using duplicates d
where r.request_id = d.request_id and d.row_number > 1;

-- Existing web identities are the anonymous zero-cost path.  Only a strict
-- UUID subject is eligible for Auth admin deletion; invalid legacy requests
-- are retained in audit history but cannot become live claims.
update public.external_identities
set is_anonymous = (provider = 'web')
where is_anonymous is distinct from (provider = 'web');
update public.learner_deletion_requests r
set auth_user_id = (
    select i.provider_subject::uuid
    from public.external_identities i
    where i.learner_id = r.requested_learner_id
      and i.is_anonymous
      and i.provider_subject ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    order by i.identity_id
    limit 1
)
where r.auth_user_id is null;
delete from public.learner_deletion_requests
where auth_user_id is null;
alter table public.learner_deletion_requests
    alter column learner_id drop not null,
    alter column auth_user_id set not null,
    alter column requested_learner_id set not null;
alter table public.learner_deletion_requests
    drop constraint if exists learner_deletion_requests_learner_id_fkey;
alter table public.learner_deletion_requests
    add constraint learner_deletion_requests_learner_id_fkey
    foreign key (learner_id) references public.learners(learner_id) on delete set null;
alter table public.learner_deletion_requests
    drop constraint if exists learner_deletion_requests_status_check;
alter table public.learner_deletion_requests
    add constraint learner_deletion_requests_status_check
    check (status in ('REQUESTED', 'CLAIMED', 'RECONCILING', 'RECONCILED', 'FAILED'));
create unique index if not exists learner_deletion_requests_requested_learner_unique
    on public.learner_deletion_requests(requested_learner_id);

-- Orphan queue rows are deliberately independent of learner lifecycle.
alter table public.artifact_cleanup_queue
    drop constraint if exists artifact_cleanup_queue_learner_id_fkey;

-- Identity mutations and deletes are denied while a deletion claim is active;
-- the erasure RPC changes the claim to RECONCILING while it holds the same
-- rows locked.

create or replace function public.prevent_identity_mutation_during_deletion()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    target_learner uuid := coalesce(new.learner_id, old.learner_id);
begin
    if exists (
        select 1 from public.learner_deletion_requests r
        where r.requested_learner_id = target_learner
          and r.status in ('REQUESTED', 'CLAIMED')
    ) then
        raise exception 'learner deletion claim is active' using errcode = '55006';
    end if;
    if tg_op = 'UPDATE' and (
        new.provider is distinct from old.provider
        or new.provider_subject is distinct from old.provider_subject
        or new.is_anonymous is distinct from old.is_anonymous
        or new.learner_id is distinct from old.learner_id
    ) then
        if exists (
            select 1 from public.learner_deletion_requests r
            where r.requested_learner_id = target_learner
              and r.status in ('REQUESTED', 'CLAIMED')
        ) then
            raise exception 'identity change blocked during deletion claim' using errcode = '55006';
        end if;
    end if;
    return case when tg_op = 'DELETE' then old else new end;
end;
$$;

drop trigger if exists external_identity_deletion_guard on public.external_identities;
create trigger external_identity_deletion_guard
before update or delete on public.external_identities
for each row execute function public.prevent_identity_mutation_during_deletion();

create or replace function public.request_learner_deletion(
    p_learner_id uuid,
    p_requested_by text
)
returns public.learner_deletion_requests
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    result_row public.learner_deletion_requests;
    identity_row public.external_identities;
begin
    select * into result_row
    from public.learner_deletion_requests
    where requested_learner_id = p_learner_id
    for update;
    if found then
        return result_row;
    end if;
    perform 1 from public.learners where learner_id = p_learner_id for update;
    if not found then raise exception 'learner not found' using errcode = 'P0002'; end if;
    -- The learner lock serializes request creators.  Re-check after waiting so
    -- a concurrent caller returns the durable request instead of racing it.
    select * into result_row
    from public.learner_deletion_requests
    where requested_learner_id = p_learner_id
    for update;
    if found then
        return result_row;
    end if;
    perform 1 from public.external_identities
    where learner_id = p_learner_id for update;
    select * into identity_row from public.external_identities
    where learner_id = p_learner_id and is_anonymous
    limit 1 for update;
    if not found
       or identity_row.provider <> 'web'
       or identity_row.provider_subject !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
        raise exception 'anonymous Auth identity required' using errcode = '22023';
    end if;
    insert into public.learner_deletion_requests(
        learner_id, requested_learner_id, auth_user_id, requested_by, status
    ) values (
        p_learner_id, p_learner_id, identity_row.provider_subject::uuid,
        p_requested_by, 'REQUESTED'
    ) on conflict (requested_learner_id) do update
        set requested_learner_id = excluded.requested_learner_id
    returning * into result_row;
    insert into public.retention_audit(
        requested_learner_id, artifact_id, learner_id, action, actor_id, details
    ) values (
        p_learner_id, null, p_learner_id, 'DELETE_REQUESTED', p_requested_by, '{}'::jsonb
    ) on conflict (requested_learner_id) where action = 'DELETE_REQUESTED' do nothing;
    return result_row;
end;
$$;

create or replace function public.erase_learner_application_data(
    p_learner_id uuid,
    p_actor_id text
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    request_row public.learner_deletion_requests;
begin
    select * into request_row
    from public.learner_deletion_requests
    where requested_learner_id = p_learner_id
    for update;
    if not found then raise exception 'learner deletion request not found' using errcode = 'P0002'; end if;
    perform 1 from public.external_identities where learner_id = p_learner_id for update;
    if exists (
        select 1 from public.artifacts
        where learner_id = p_learner_id and purge_status <> 'PURGED'
    ) or exists (
        select 1 from public.artifact_cleanup_queue
        where learner_id = p_learner_id and status <> 'RESOLVED'
    ) then
        raise exception 'learner artifacts are not reconciled' using errcode = '55006';
    end if;

    -- Insert the tombstone before deleting any learner-owned application row.
    insert into public.retention_audit(
        requested_learner_id, artifact_id, learner_id, action, actor_id, details
    ) values (
        p_learner_id, null, p_learner_id, 'ANONYMOUS_RECONCILED', p_actor_id,
        jsonb_build_object('erasure', 'started')
    );
    update public.learner_deletion_requests
    set status = 'RECONCILING', lease_owner = null, lease_expires_at = null
    where request_id = request_row.request_id;

    -- Preserve this order: every dependent application row is erased before
    -- the learner, while queue rows and audit tombstones remain historical.
    delete from public.skill_evidence where learner_id = p_learner_id;
    delete from public.attempts where learner_id = p_learner_id;
    delete from public.evaluation_results e
    where exists (
        select 1 from public.submissions s
        where s.submission_id = e.submission_id and s.learner_id = p_learner_id
    );
    delete from public.feedback_results f
    where exists (
        select 1 from public.submissions s
        where s.submission_id = f.submission_id and s.learner_id = p_learner_id
    );
    delete from public.submissions where learner_id = p_learner_id;
    delete from public.outbox_events where aggregate_id = p_learner_id;
    delete from public.artifacts where learner_id = p_learner_id;
    delete from public.learners where learner_id = p_learner_id;
    update public.learner_deletion_requests
    set status = 'RECONCILED', reconciled_at = timezone('utc', now()), learner_id = null
    where request_id = request_row.request_id;
    return true;
end;
$$;

create or replace function public.claim_learner_deletion_requests(
    p_lease_owner text,
    p_limit integer
)
returns table(request_id uuid, learner_id uuid, auth_user_id uuid)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    return query
    with candidates as (
        select r.request_id
        from public.learner_deletion_requests r
        where r.status in ('REQUESTED', 'FAILED', 'RECONCILED')
          and r.auth_user_id is not null
          and r.auth_deleted_at is null
          and (r.lease_expires_at is null or r.lease_expires_at <= timezone('utc', now()))
        order by r.requested_at, r.request_id
        limit greatest(p_limit, 0) for update skip locked
    )
    update public.learner_deletion_requests r
    set status = 'CLAIMED', lease_owner = p_lease_owner,
        lease_expires_at = timezone('utc', now()) + interval '5 minutes'
    from candidates c where r.request_id = c.request_id
    returning r.request_id, r.requested_learner_id, r.auth_user_id;
end;
$$;

create or replace function public.finalize_learner_deletion_request(
    p_request_id uuid,
    p_lease_owner text,
    p_success boolean
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    update public.learner_deletion_requests
    set status = case when p_success then 'RECONCILED' else 'FAILED' end,
        lease_owner = null, lease_expires_at = null,
        reconciled_at = case when p_success then timezone('utc', now()) else null end,
        auth_deleted_at = case when p_success then timezone('utc', now()) else auth_deleted_at end
    where request_id = p_request_id and lease_owner = p_lease_owner;
end;
$$;

-- The original function predates requested_learner_id; replace its audit
-- insert so normal purge finalization remains valid after the column is NOT NULL.
create or replace function public.finalize_artifact_purge(
    p_artifact_id uuid, p_lease_owner text, p_deleted boolean,
    p_details jsonb default '{}'::jsonb
)
returns public.artifacts
language plpgsql security definer set search_path = public, pg_temp
as $$
declare result_row public.artifacts;
begin
    update public.artifacts set purge_status = case when p_deleted then 'PURGED' else 'PURGE_FAILED' end,
        purge_lease_owner = null, purge_lease_expires_at = null,
        purged_at = case when p_deleted then timezone('utc', now()) else null end
    where artifact_id = p_artifact_id and purge_status = 'CLAIMED'
      and purge_lease_owner = p_lease_owner
      and purge_lease_expires_at > timezone('utc', now())
    returning * into result_row;
    if not found then raise exception 'artifact purge lease conflict' using errcode = '40001'; end if;
    insert into public.retention_audit(
        requested_learner_id, artifact_id, learner_id, action, actor_id, details
    ) values (
        result_row.learner_id, result_row.artifact_id, result_row.learner_id,
        case when p_deleted then 'PURGED' else 'PURGE_FAILED' end,
        p_lease_owner, p_details
    );
    return result_row;
end;
$$;

revoke all on function public.request_learner_deletion(uuid, text) from public, anon, authenticated;
revoke all on function public.erase_learner_application_data(uuid, text) from public, anon, authenticated;
revoke all on function public.claim_learner_deletion_requests(text, integer) from public, anon, authenticated;
revoke all on function public.finalize_learner_deletion_request(uuid, text, boolean) from public, anon, authenticated;
grant execute on function public.request_learner_deletion(uuid, text) to service_role;
grant execute on function public.erase_learner_application_data(uuid, text) to service_role;
grant execute on function public.claim_learner_deletion_requests(text, integer) to service_role;
grant execute on function public.finalize_learner_deletion_request(uuid, text, boolean) to service_role;
commit;
