-- Final Member 2 parity fixes: make reservation races replay-safe and keep
-- the learner summary row atomic with its progress row.

create or replace function public.reserve_submission(
    p_learner_id uuid,
    p_task_version_id uuid,
    p_artifact_id uuid,
    p_channel text,
    p_idempotency_key text,
    p_request_fingerprint text,
    p_lease_seconds integer,
    p_lease_owner text
)
returns public.submissions
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    current_row public.submissions;
    task_row public.task_versions;
    progress_row public.learner_progress;
begin
    if p_learner_id is null or p_task_version_id is null or p_artifact_id is null
        or p_channel is null or p_channel not in ('web', 'telegram')
        or p_idempotency_key is null or char_length(btrim(p_idempotency_key)) = 0
        or char_length(p_idempotency_key) > 255
        or p_request_fingerprint is null
        or p_request_fingerprint !~ '^[a-f0-9]{64}$'
        or p_lease_seconds is null or p_lease_seconds <= 0 or p_lease_seconds > 3600
        or p_lease_owner is not distinct from null
        or char_length(btrim(p_lease_owner)) = 0 then
        raise exception 'invalid submission reservation parameters' using errcode = '22023';
    end if;

    select * into task_row
    from public.task_versions
    where task_version_id = p_task_version_id and status = 'PUBLISHED';
    if not found then
        raise exception 'task version is not published' using errcode = '42501';
    end if;
    if not exists (select 1 from public.learners where learner_id = p_learner_id)
        or not exists (
            select 1 from public.artifacts
            where artifact_id = p_artifact_id and learner_id = p_learner_id
        ) then
        raise exception 'submission references are not valid' using errcode = '42501';
    end if;
    select * into progress_row
    from public.learner_progress
    where learner_id = p_learner_id;
    if not found then
        raise exception 'learner progress not found' using errcode = 'P0002';
    end if;
    if progress_row.current_task_id is not null
        and progress_row.current_task_id <> task_row.task_id then
        raise exception 'submission task is not learner current task' using errcode = '22023';
    end if;
    if progress_row.current_status not in ('IN_TASK', 'PROCESSING', 'NEEDS_RETRY') then
        raise exception 'learner is not eligible for task submission' using errcode = '22023';
    end if;

    select * into current_row
    from public.submissions
    where learner_id = p_learner_id and idempotency_key = p_idempotency_key
    for update;
    if found then
        if current_row.request_fingerprint <> p_request_fingerprint
            or current_row.task_version_id <> p_task_version_id
            or current_row.artifact_id <> p_artifact_id
            or current_row.channel <> p_channel then
            raise exception 'idempotency fingerprint conflict' using errcode = '23505';
        end if;
        if current_row.status = 'COMPLETED'
            or current_row.lease_expires_at > timezone('utc', now()) then
            return current_row;
        end if;
        update public.submissions set lease_owner = p_lease_owner,
            lease_expires_at = timezone('utc', now()) + make_interval(secs => p_lease_seconds),
            version = current_row.version + 1, updated_at = timezone('utc', now())
        where reservation_id = current_row.reservation_id and version = current_row.version
        returning * into current_row;
        if not found then
            raise exception 'submission reservation CAS conflict' using errcode = '40001';
        end if;
        return current_row;
    end if;

    -- Both callers can observe an absent row.  The loser of the unique index
    -- race enters this savepoint, reloads the winner, and applies the exact
    -- same replay/mismatch rules as the ordinary existing-row path.
    begin
        insert into public.submissions (
            learner_id, task_version_id, artifact_id, channel, idempotency_key,
            request_fingerprint, status, lease_expires_at, lease_owner
        ) values (
            p_learner_id, p_task_version_id, p_artifact_id, p_channel, p_idempotency_key,
            p_request_fingerprint, 'RECEIVED',
            timezone('utc', now()) + make_interval(secs => p_lease_seconds), p_lease_owner
        ) returning * into current_row;
        return current_row;
    exception when unique_violation then
        select * into current_row
        from public.submissions
        where learner_id = p_learner_id and idempotency_key = p_idempotency_key
        for update;
        if not found then
            raise exception 'submission reservation race' using errcode = '40001';
        end if;
        if current_row.request_fingerprint <> p_request_fingerprint
            or current_row.task_version_id <> p_task_version_id
            or current_row.artifact_id <> p_artifact_id
            or current_row.channel <> p_channel then
            raise exception 'idempotency fingerprint conflict' using errcode = '23505';
        end if;
        if current_row.status = 'COMPLETED'
            or current_row.lease_expires_at > timezone('utc', now()) then
            return current_row;
        end if;
        update public.submissions set lease_owner = p_lease_owner,
            lease_expires_at = timezone('utc', now()) + make_interval(secs => p_lease_seconds),
            version = current_row.version + 1, updated_at = timezone('utc', now())
        where reservation_id = current_row.reservation_id and version = current_row.version
        returning * into current_row;
        if not found then
            raise exception 'submission reservation CAS conflict' using errcode = '40001';
        end if;
        return current_row;
    end;
end;
$$;

-- A progress write is the authority for the denormalized learner summary.
-- The trigger runs in the same transaction as submission finalization and
-- admin reset, so the two status columns cannot commit divergent values.
create or replace function public.sync_learner_status_from_progress()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    update public.learners
    set status = new.current_status, updated_at = new.updated_at
    where learner_id = new.learner_id;
    return new;
end;
$$;

drop trigger if exists learner_progress_status_sync on public.learner_progress;
create trigger learner_progress_status_sync
after insert or update of current_status, updated_at on public.learner_progress
for each row execute function public.sync_learner_status_from_progress();

revoke all on function public.sync_learner_status_from_progress() from public, anon, authenticated;
grant execute on function public.sync_learner_status_from_progress() to service_role;
revoke all on function public.reserve_submission(uuid, uuid, uuid, text, text, text, integer, text)
    from public, anon, authenticated;
grant execute on function public.reserve_submission(uuid, uuid, uuid, text, text, text, integer, text)
    to service_role;
