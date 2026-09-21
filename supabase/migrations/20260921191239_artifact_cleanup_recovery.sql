-- Durable server-only queue for objects whose metadata transaction or object
-- deletion could not complete.  artifact_id intentionally has no FK because
-- this table must represent an object whose metadata row was never committed.
alter table public.artifacts drop constraint if exists artifacts_purge_status_check;
alter table public.artifacts add constraint artifacts_purge_status_check
    check (purge_status in ('ACTIVE', 'UPLOADING', 'CLAIMED', 'PURGE_FAILED', 'PURGED'));

create table public.artifact_cleanup_queue (
    cleanup_id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references public.learners(learner_id) on delete cascade,
    artifact_id uuid not null,
    object_path text not null unique,
    sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
    size_bytes bigint not null check (size_bytes between 0 and 5242880),
    reason text not null check (reason in ('METADATA_FAILED', 'DELETE_FAILED', 'UPLOAD_FAILED')),
    status text not null default 'PENDING' check (status in ('PENDING', 'RESOLVED')),
    attempts integer not null default 0 check (attempts >= 0),
    lease_owner text,
    lease_expires_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    resolved_at timestamptz,
    check (object_path = learner_id::text || '/' || artifact_id::text)
);

create index artifact_cleanup_pending_idx
    on public.artifact_cleanup_queue(status, created_at)
    where status = 'PENDING';

alter table public.artifact_cleanup_queue enable row level security;
revoke all on table public.artifact_cleanup_queue from anon, authenticated;
-- Metadata is read-only to authenticated learners; all writes remain in the
-- service-only reservation/delete RPCs below.
grant select on public.artifacts to authenticated;

create or replace function public.enqueue_artifact_cleanup(
    p_learner_id uuid,
    p_artifact_id uuid,
    p_object_path text,
    p_sha256 text,
    p_size_bytes bigint,
    p_reason text
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    cleanup_id uuid;
begin
    if p_learner_id is null or p_artifact_id is null
        or p_object_path <> p_learner_id::text || '/' || p_artifact_id::text
        or p_sha256 is null or p_sha256 !~ '^[a-f0-9]{64}$'
        or p_size_bytes < 0 or p_size_bytes > 5242880
        or p_reason not in ('METADATA_FAILED', 'DELETE_FAILED', 'UPLOAD_FAILED') then
        raise exception 'invalid artifact cleanup payload' using errcode = '22023';
    end if;
    insert into public.artifact_cleanup_queue(
        learner_id, artifact_id, object_path, sha256, size_bytes, reason
    ) values (
        p_learner_id, p_artifact_id, p_object_path, p_sha256, p_size_bytes, p_reason
    ) on conflict (object_path) do update set
        status = 'PENDING', resolved_at = null, reason = excluded.reason,
        attempts = public.artifact_cleanup_queue.attempts + 1
    returning artifact_cleanup_queue.cleanup_id into cleanup_id;
    return cleanup_id;
end;
$$;

create or replace function public.resolve_artifact_cleanup(
    p_learner_id uuid,
    p_artifact_id uuid
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    update public.artifact_cleanup_queue
    set status = 'RESOLVED', resolved_at = timezone('utc', now())
    where learner_id = p_learner_id and artifact_id = p_artifact_id;
    -- A reservation that never reached ACTIVE must not remain dangling after
    -- its object has been reconciled.  Successful uploads are ACTIVE and are
    -- intentionally left untouched here.
    update public.artifacts
    set purge_status = 'PURGED', purged_at = timezone('utc', now()),
        purge_lease_owner = null, purge_lease_expires_at = null
    where learner_id = p_learner_id and artifact_id = p_artifact_id
      and purge_status = 'UPLOADING';
end;
$$;

create or replace function public.tombstone_artifact(
    p_learner_id uuid,
    p_artifact_id uuid
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    update public.artifacts
    set purge_status = 'PURGED', purged_at = timezone('utc', now()),
        purge_lease_owner = null, purge_lease_expires_at = null
    where learner_id = p_learner_id and artifact_id = p_artifact_id
      and purge_status <> 'PURGED';
end;
$$;

-- Finalization is owner/lease CAS protected; a stale worker cannot resolve a
-- row reclaimed by another worker after its lease expires.
create or replace function public.finalize_artifact_cleanup(
    p_cleanup_id uuid,
    p_lease_owner text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    changed integer;
begin
    if p_cleanup_id is null or p_lease_owner is null or char_length(p_lease_owner) = 0 then
        raise exception 'invalid artifact cleanup finalization payload' using errcode = '22023';
    end if;
    update public.artifact_cleanup_queue
    set status = 'RESOLVED', resolved_at = timezone('utc', now()),
        lease_owner = null, lease_expires_at = null
    where cleanup_id = p_cleanup_id and status = 'PENDING'
      and lease_owner = p_lease_owner
      and lease_expires_at > timezone('utc', now());
    get diagnostics changed = row_count;
    if changed <> 1 then
        raise exception 'artifact cleanup lease conflict' using errcode = '40001';
    end if;
    update public.artifacts a
    set purge_status = 'PURGED', purged_at = timezone('utc', now()),
        purge_lease_owner = null, purge_lease_expires_at = null
    from public.artifact_cleanup_queue q
    where q.cleanup_id = p_cleanup_id and a.learner_id = q.learner_id
      and a.artifact_id = q.artifact_id and a.purge_status = 'UPLOADING';
end;
$$;

-- Reserve metadata before storage mutation. A retry with the same generated
-- identity is idempotent only when immutable ownership/hash metadata matches.
drop function if exists public.reserve_artifact(uuid, uuid, text, text, bigint, text);
create or replace function public.reserve_artifact(
    p_learner_id uuid,
    p_artifact_id uuid,
    p_object_path text,
    p_filename text,
    p_size_bytes bigint,
    p_sha256 text,
    p_upload_owner text,
    p_upload_lease_seconds integer
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    current_row public.artifacts;
begin
    if p_learner_id is null or p_artifact_id is null
        or p_object_path <> p_learner_id::text || '/' || p_artifact_id::text
        or p_filename is null or char_length(p_filename) not between 1 and 255
        or p_size_bytes < 0 or p_size_bytes > 5242880
        or p_sha256 is null or p_sha256 !~ '^[a-f0-9]{64}$'
        or p_upload_owner is null or char_length(p_upload_owner) = 0
        or p_upload_lease_seconds is null or p_upload_lease_seconds <= 0
        or p_upload_lease_seconds > 900 then
        raise exception 'invalid artifact reservation payload' using errcode = '22023';
    end if;
    select * into current_row
    from public.artifacts where artifact_id = p_artifact_id for update;
    if found then
        if current_row.learner_id <> p_learner_id
            or current_row.object_path <> p_object_path
            or current_row.filename <> p_filename
            or current_row.size_bytes <> p_size_bytes
            or current_row.sha256 <> p_sha256 then
            raise exception 'artifact identity conflict' using errcode = '23505';
        end if;
        -- Any existing row, including an unfinished UPLOADING reservation,
        -- belongs to the first caller.  A retry must not mutate storage a
        -- second time; the cleanup queue reconciles unfinished metadata.
        return jsonb_build_object('created', false, 'artifact', to_jsonb(current_row));
    end if;
    insert into public.artifacts(
        artifact_id, learner_id, object_path, filename, size_bytes, sha256,
        purge_status, purge_lease_owner, purge_lease_expires_at
    ) values (
        p_artifact_id, p_learner_id, p_object_path, p_filename, p_size_bytes, p_sha256,
        'UPLOADING', p_upload_owner,
        timezone('utc', now()) + make_interval(secs => p_upload_lease_seconds)
    ) returning * into current_row;
    return jsonb_build_object('created', true, 'artifact', to_jsonb(current_row));
end;
$$;

drop function if exists public.activate_artifact(uuid, uuid);
create or replace function public.activate_artifact(
    p_learner_id uuid,
    p_artifact_id uuid,
    p_upload_owner text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    changed integer;
begin
    if p_upload_owner is null or char_length(p_upload_owner) = 0 then
        raise exception 'invalid artifact upload owner' using errcode = '22023';
    end if;
    update public.artifacts set purge_status = 'ACTIVE',
        purge_lease_owner = null, purge_lease_expires_at = null
    where learner_id = p_learner_id and artifact_id = p_artifact_id
      and purge_status = 'UPLOADING'
      and purge_lease_owner = p_upload_owner
      and purge_lease_expires_at > timezone('utc', now());
    get diagnostics changed = row_count;
    if changed <> 1 then
        raise exception 'artifact upload lease conflict' using errcode = '40001';
    end if;
end;
$$;

-- One transaction protects delete races: queue the object and tombstone its
-- metadata before the caller mutates private storage.
create or replace function public.prepare_artifact_delete(
    p_learner_id uuid,
    p_artifact_id uuid,
    p_object_path text,
    p_sha256 text,
    p_size_bytes bigint,
    p_reason text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    if p_object_path <> p_learner_id::text || '/' || p_artifact_id::text then
        raise exception 'invalid artifact delete path' using errcode = '22023';
    end if;
    if not exists (
        select 1 from public.artifacts
        where learner_id = p_learner_id and artifact_id = p_artifact_id
          and purge_status <> 'PURGED'
    ) then
        return;
    end if;
    perform public.enqueue_artifact_cleanup(
        p_learner_id, p_artifact_id, p_object_path, p_sha256, p_size_bytes, p_reason
    );
    update public.artifacts
    set purge_status = 'PURGED', purged_at = timezone('utc', now()),
        purge_lease_owner = null, purge_lease_expires_at = null
    where learner_id = p_learner_id and artifact_id = p_artifact_id;
end;
$$;

create or replace function public.claim_artifact_cleanup(
    p_limit integer,
    p_lease_owner text,
    p_lease_seconds integer
)
returns setof public.artifact_cleanup_queue
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    if p_limit <= 0 or p_lease_seconds <= 0
        or p_lease_owner is null or char_length(p_lease_owner) = 0 then
        raise exception 'invalid artifact cleanup lease parameters' using errcode = '22023';
    end if;

    -- A queue row created before metadata commit is safe to delete. A row
    -- whose metadata is active is resolved instead of deleting a live object.
    update public.artifact_cleanup_queue q
    set status = 'RESOLVED', resolved_at = timezone('utc', now())
    where q.status = 'PENDING'
      and exists (
          select 1 from public.artifacts a
          where a.artifact_id = q.artifact_id and a.purge_status = 'ACTIVE'
      );

    return query
    with candidates as (
        select q.cleanup_id
        from public.artifact_cleanup_queue q
        where q.status = 'PENDING'
          and (q.lease_expires_at is null or q.lease_expires_at <= timezone('utc', now()))
          and not exists (
              select 1 from public.artifacts a
              where a.artifact_id = q.artifact_id
                and a.purge_status = 'UPLOADING'
                and a.purge_lease_expires_at > timezone('utc', now())
          )
        order by q.created_at, q.cleanup_id
        for update skip locked
        limit p_limit
    )
    update public.artifact_cleanup_queue q
    set lease_owner = p_lease_owner,
        lease_expires_at = timezone('utc', now()) + make_interval(secs => p_lease_seconds),
        attempts = q.attempts + 1
    from candidates
    where q.cleanup_id = candidates.cleanup_id
    returning q.*;
end;
$$;

create or replace function public.release_artifact_cleanup(
    p_cleanup_id uuid,
    p_lease_owner text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    update public.artifact_cleanup_queue
    set lease_owner = null, lease_expires_at = null
    where cleanup_id = p_cleanup_id and status = 'PENDING'
      and lease_owner = p_lease_owner;
end;
$$;

revoke all on function public.enqueue_artifact_cleanup(uuid, uuid, text, text, bigint, text)
    from public, anon, authenticated;
revoke all on function public.resolve_artifact_cleanup(uuid, uuid)
    from public, anon, authenticated;
revoke all on function public.tombstone_artifact(uuid, uuid)
    from public, anon, authenticated;
revoke all on function public.finalize_artifact_cleanup(uuid, text)
    from public, anon, authenticated;
revoke all on function public.reserve_artifact(uuid, uuid, text, text, bigint, text, text, integer)
    from public, anon, authenticated;
revoke all on function public.prepare_artifact_delete(uuid, uuid, text, text, bigint, text)
    from public, anon, authenticated;
revoke all on function public.activate_artifact(uuid, uuid, text)
    from public, anon, authenticated;
revoke all on function public.claim_artifact_cleanup(integer, text, integer)
    from public, anon, authenticated;
revoke all on function public.release_artifact_cleanup(uuid, text)
    from public, anon, authenticated;
grant execute on function public.enqueue_artifact_cleanup(uuid, uuid, text, text, bigint, text)
    to service_role;
grant execute on function public.resolve_artifact_cleanup(uuid, uuid)
    to service_role;
grant execute on function public.tombstone_artifact(uuid, uuid)
    to service_role;
grant execute on function public.finalize_artifact_cleanup(uuid, text)
    to service_role;
grant execute on function public.reserve_artifact(uuid, uuid, text, text, bigint, text, text, integer)
    to service_role;
grant execute on function public.prepare_artifact_delete(uuid, uuid, text, text, bigint, text)
    to service_role;
grant execute on function public.activate_artifact(uuid, uuid, text)
    to service_role;
grant execute on function public.claim_artifact_cleanup(integer, text, integer)
    to service_role;
grant execute on function public.release_artifact_cleanup(uuid, text)
    to service_role;
