-- Yom Awel platform schema.  This migration is intentionally self-contained
-- and uses only Supabase's free Postgres/Auth/Storage capabilities.
create extension if not exists pgcrypto;

create table public.learners (
    learner_id uuid primary key default gen_random_uuid(),
    display_name text not null check (char_length(display_name) between 1 and 200),
    preferred_language text not null check (preferred_language in ('ar-EG', 'en')),
    status text not null check (status in ('ONBOARDING', 'READY', 'IN_TASK', 'PROCESSING', 'NEEDS_RETRY', 'TASK_COMPLETED', 'PROGRAM_COMPLETED')),
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    state_machine_version text not null check (char_length(state_machine_version) > 0)
);

create table public.external_identities (
    identity_id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references public.learners(learner_id) on delete cascade,
    provider text not null check (provider in ('telegram', 'web')),
    provider_subject text not null,
    created_at timestamptz not null default timezone('utc', now()),
    unique (provider, provider_subject),
    unique (learner_id, provider)
);

create table public.tasks (
    task_id text primary key,
    title text not null,
    created_at timestamptz not null default timezone('utc', now())
);

create table public.task_versions (
    task_version_id uuid primary key default gen_random_uuid(),
    task_id text not null references public.tasks(task_id),
    version text not null,
    instructions_ar text not null,
    instructions_en text not null,
    artifact_schema jsonb not null default '{}'::jsonb,
    evaluator_id text not null,
    evaluator_version text not null,
    pass_threshold integer not null check (pass_threshold between 0 and 100),
    skill_mappings jsonb not null default '[]'::jsonb,
    content_hash text not null check (content_hash ~ '^[a-f0-9]{64}$'),
    status text not null default 'DRAFT' check (status in ('DRAFT', 'PUBLISHED', 'RETIRED')),
    published_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    unique (task_id, version)
);

create table public.artifacts (
    artifact_id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references public.learners(learner_id) on delete cascade,
    object_path text not null unique,
    filename text not null check (char_length(filename) between 1 and 255),
    size_bytes bigint not null check (size_bytes between 0 and 5242880),
    sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
    retention_expires_at timestamptz not null default (timezone('utc', now()) + interval '30 days'),
    purge_status text not null default 'ACTIVE' check (purge_status in ('ACTIVE', 'CLAIMED', 'PURGE_FAILED', 'PURGED')),
    purge_lease_owner text,
    purge_lease_expires_at timestamptz,
    purged_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    check (object_path = learner_id::text || '/' || artifact_id::text)
);

create table public.submissions (
    reservation_id uuid primary key default gen_random_uuid(),
    submission_id uuid not null unique default gen_random_uuid(),
    learner_id uuid not null references public.learners(learner_id) on delete cascade,
    task_version_id uuid not null references public.task_versions(task_version_id),
    artifact_id uuid not null references public.artifacts(artifact_id),
    channel text not null check (channel in ('web', 'telegram')),
    idempotency_key text not null check (char_length(idempotency_key) between 1 and 255),
    request_fingerprint text not null check (request_fingerprint ~ '^[a-f0-9]{64}$'),
    status text not null check (status in ('RECEIVED', 'EVALUATING', 'COMPLETED', 'FAILED')),
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    version integer not null default 1 check (version >= 1),
    lease_expires_at timestamptz not null,
    lease_owner text,
    outcome jsonb,
    unique (learner_id, idempotency_key),
    unique (learner_id, channel, idempotency_key)
);

create table public.evaluation_results (
    evaluation_id uuid primary key default gen_random_uuid(),
    submission_id uuid not null references public.submissions(submission_id),
    evaluator_id text not null,
    evaluator_version text not null,
    task_version_id uuid not null references public.task_versions(task_version_id),
    passed boolean not null,
    score integer not null check (score between 0 and 100),
    checks jsonb not null default '[]'::jsonb,
    errors jsonb not null default '[]'::jsonb,
    summary_ar text not null,
    summary_en text not null,
    duration_ms integer not null check (duration_ms >= 0),
    recorded_at timestamptz not null default timezone('utc', now()),
    unique (submission_id)
);

create table public.feedback_results (
    feedback_id uuid primary key default gen_random_uuid(),
    submission_id uuid not null references public.submissions(submission_id),
    feedback_text text not null,
    language text not null check (language in ('ar-EG', 'en')),
    persona_id text not null,
    prompt_version text not null,
    provider text not null,
    model text,
    used_fallback boolean not null,
    duration_ms integer not null check (duration_ms >= 0),
    request_hash text,
    recorded_at timestamptz not null default timezone('utc', now()),
    unique (submission_id)
);

create table public.attempts (
    attempt_id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references public.learners(learner_id) on delete cascade,
    submission_id uuid not null unique references public.submissions(submission_id),
    task_version_id uuid not null references public.task_versions(task_version_id),
    attempt_number integer not null check (attempt_number >= 1),
    evaluation_id uuid not null unique references public.evaluation_results(evaluation_id),
    feedback_id uuid not null unique references public.feedback_results(feedback_id),
    evaluator_id text not null,
    evaluator_version text not null,
    prompt_version text not null,
    started_at timestamptz not null,
    completed_at timestamptz,
    unique (learner_id, task_version_id, attempt_number)
);

create table public.skill_definitions (
    skill_id text primary key,
    title text not null,
    description text not null,
    created_at timestamptz not null default timezone('utc', now())
);

create table public.skill_evidence (
    evidence_id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references public.learners(learner_id) on delete cascade,
    attempt_id uuid not null references public.attempts(attempt_id),
    task_version_id uuid not null references public.task_versions(task_version_id),
    skill_id text not null references public.skill_definitions(skill_id),
    check_id text not null,
    awarded_points integer not null check (awarded_points >= 0),
    available_points integer not null check (available_points > 0),
    recorded_at timestamptz not null default timezone('utc', now()),
    unique (attempt_id, skill_id, check_id),
    check (awarded_points <= available_points)
);

create table public.learner_progress (
    learner_id uuid primary key references public.learners(learner_id) on delete cascade,
    current_status text not null check (current_status in ('ONBOARDING', 'READY', 'IN_TASK', 'PROCESSING', 'NEEDS_RETRY', 'TASK_COMPLETED', 'PROGRAM_COMPLETED')),
    current_task_id text references public.tasks(task_id),
    version integer not null check (version >= 1),
    updated_at timestamptz not null default timezone('utc', now()),
    reset_at timestamptz
);

create table public.outbox_events (
    event_id uuid primary key default gen_random_uuid(),
    event_type text not null,
    aggregate_id uuid not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    published_at timestamptz
);

create table public.retention_audit (
    audit_id uuid primary key default gen_random_uuid(),
    artifact_id uuid references public.artifacts(artifact_id) on delete set null,
    learner_id uuid references public.learners(learner_id) on delete set null,
    action text not null check (action in ('PURGE_CLAIMED', 'PURGED', 'PURGE_FAILED', 'DELETE_REQUESTED', 'ANONYMOUS_RECONCILED')),
    actor_id text not null,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now())
);

create table public.learner_deletion_requests (
    request_id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references public.learners(learner_id) on delete cascade,
    requested_by text not null,
    requested_at timestamptz not null default timezone('utc', now()),
    reconciled_at timestamptz,
    status text not null default 'REQUESTED' check (status in ('REQUESTED', 'RECONCILED', 'FAILED'))
);

create index submissions_learner_status_idx on public.submissions(learner_id, status);
create index submissions_lease_idx on public.submissions(lease_expires_at) where status <> 'COMPLETED';
create index artifacts_retention_idx on public.artifacts(retention_expires_at, purge_status);
create index attempts_learner_task_idx on public.attempts(learner_id, task_version_id, attempt_number);
create index evidence_learner_idx on public.skill_evidence(learner_id, skill_id);
create index outbox_pending_idx on public.outbox_events(created_at) where published_at is null;

-- Published versions are immutable.  Drafts can be edited only before publication.
create or replace function public.prevent_published_task_version_mutation()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
    if old.status = 'PUBLISHED' then
        if new.task_version_id <> old.task_version_id
            or new.task_id <> old.task_id
            or new.version <> old.version
            or new.instructions_ar <> old.instructions_ar
            or new.instructions_en <> old.instructions_en
            or new.artifact_schema <> old.artifact_schema
            or new.evaluator_id <> old.evaluator_id
            or new.evaluator_version <> old.evaluator_version
            or new.pass_threshold <> old.pass_threshold
            or new.skill_mappings <> old.skill_mappings
            or new.content_hash <> old.content_hash then
            raise exception 'published task versions are immutable';
        end if;
    end if;
    return new;
end;
$$;
create trigger task_version_immutable before update on public.task_versions
for each row execute function public.prevent_published_task_version_mutation();

-- Resolve the verified Supabase Auth subject to the application learner.
create or replace function public.current_learner_id()
returns uuid
language sql
stable
security definer
set search_path = public, auth, pg_temp
as $$
    select learner_id from public.external_identities
    where provider = 'web' and provider_subject = (select auth.uid())::text
    limit 1
$$;

-- Reservation RPC: all validation and lease ownership checks happen in one
-- short transaction.  Only the server role can call it.
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
begin
    if p_lease_seconds <= 0 or p_lease_owner is null or char_length(p_lease_owner) = 0 then
        raise exception 'invalid lease' using errcode = '22023';
    end if;
    if not exists (select 1 from public.learners where learner_id = p_learner_id)
        or not exists (select 1 from public.task_versions where task_version_id = p_task_version_id)
        or not exists (select 1 from public.artifacts where artifact_id = p_artifact_id and learner_id = p_learner_id) then
        raise exception 'submission references are not valid' using errcode = '42501';
    end if;
    select * into current_row from public.submissions
    where learner_id = p_learner_id and idempotency_key = p_idempotency_key
    for update;
    if found then
        if current_row.request_fingerprint <> p_request_fingerprint then
            raise exception 'idempotency fingerprint conflict' using errcode = '23505';
        end if;
        if current_row.status = 'COMPLETED' or current_row.lease_expires_at > timezone('utc', now()) then
            return current_row;
        end if;
        update public.submissions set lease_owner = p_lease_owner,
            lease_expires_at = timezone('utc', now()) + make_interval(secs => p_lease_seconds),
            version = current_row.version + 1, updated_at = timezone('utc', now())
        where reservation_id = current_row.reservation_id and version = current_row.version
        returning * into current_row;
        return current_row;
    end if;
    insert into public.submissions (
        learner_id, task_version_id, artifact_id, channel, idempotency_key,
        request_fingerprint, status, lease_expires_at, lease_owner
    ) values (
        p_learner_id, p_task_version_id, p_artifact_id, p_channel, p_idempotency_key,
        p_request_fingerprint, 'RECEIVED', timezone('utc', now()) + make_interval(secs => p_lease_seconds), p_lease_owner
    ) returning * into current_row;
    return current_row;
end;
$$;

-- Finalization RPC receives already-validated immutable payloads from the
-- server and applies all audit/progression writes under one CAS transaction.
create or replace function public.finalize_submission(
    p_reservation_id uuid,
    p_expected_version integer,
    p_lease_owner text,
    p_evaluation jsonb,
    p_feedback jsonb,
    p_attempt jsonb,
    p_evidence jsonb,
    p_progress_status text,
    p_progress_expected_version integer,
    p_outbox jsonb,
    p_outcome jsonb
)
returns public.submissions
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    current_row public.submissions;
    progress_updated integer;
begin
    select * into current_row from public.submissions
    where reservation_id = p_reservation_id for update;
    if not found then raise exception 'submission reservation not found' using errcode = 'P0002'; end if;
    if current_row.version <> p_expected_version
        or current_row.status = 'COMPLETED' then
        raise exception 'submission reservation CAS conflict' using errcode = '40001';
    end if;
    if current_row.lease_owner <> p_lease_owner then
        raise exception 'submission reservation owner conflict' using errcode = '42501';
    end if;
    if current_row.lease_expires_at <= timezone('utc', now()) then
        raise exception 'submission reservation lease expired' using errcode = '40001';
    end if;
    if (p_outcome ->> 'submission_id')::uuid <> current_row.submission_id then
        raise exception 'submission mismatch' using errcode = '22023';
    end if;

    insert into public.evaluation_results (
        evaluation_id, submission_id, evaluator_id, evaluator_version, task_version_id,
        passed, score, checks, errors, summary_ar, summary_en, duration_ms
    ) values (
        (p_evaluation ->> 'evaluation_id')::uuid, current_row.submission_id,
        p_evaluation ->> 'evaluator_id', p_evaluation ->> 'evaluator_version',
        (p_evaluation ->> 'task_version_id')::uuid, (p_evaluation ->> 'passed')::boolean,
        (p_evaluation ->> 'score')::integer, coalesce(p_evaluation -> 'checks', '[]'::jsonb),
        coalesce(p_evaluation -> 'errors', '[]'::jsonb), p_evaluation ->> 'summary_ar',
        p_evaluation ->> 'summary_en', (p_evaluation ->> 'duration_ms')::integer
    );
    insert into public.feedback_results (
        feedback_id, submission_id, feedback_text, language, persona_id, prompt_version,
        provider, model, used_fallback, duration_ms, request_hash
    ) values (
        (p_feedback ->> 'feedback_id')::uuid, current_row.submission_id,
        p_feedback ->> 'feedback_text', p_feedback ->> 'language', p_feedback ->> 'persona_id',
        p_feedback ->> 'prompt_version', p_feedback ->> 'provider', p_feedback ->> 'model',
        (p_feedback ->> 'used_fallback')::boolean, (p_feedback ->> 'duration_ms')::integer,
        p_feedback ->> 'request_hash'
    );
    insert into public.attempts (
        attempt_id, learner_id, submission_id, task_version_id, attempt_number,
        evaluation_id, feedback_id, evaluator_id, evaluator_version, prompt_version,
        started_at, completed_at
    ) values (
        (p_attempt ->> 'attempt_id')::uuid, current_row.learner_id, current_row.submission_id,
        current_row.task_version_id, (p_attempt ->> 'attempt_number')::integer,
        (p_evaluation ->> 'evaluation_id')::uuid, (p_feedback ->> 'feedback_id')::uuid,
        p_evaluation ->> 'evaluator_id', p_evaluation ->> 'evaluator_version',
        p_feedback ->> 'prompt_version', (p_attempt ->> 'started_at')::timestamptz,
        (p_attempt ->> 'completed_at')::timestamptz
    );
    insert into public.skill_evidence (
        evidence_id, learner_id, attempt_id, task_version_id, skill_id, check_id,
        awarded_points, available_points, recorded_at
    ) select (item ->> 'evidence_id')::uuid, current_row.learner_id,
        (p_attempt ->> 'attempt_id')::uuid, current_row.task_version_id,
        item ->> 'skill_id', item ->> 'check_id', (item ->> 'awarded_points')::integer,
        (item ->> 'available_points')::integer, (item ->> 'recorded_at')::timestamptz
    from jsonb_array_elements(coalesce(p_evidence, '[]'::jsonb)) item;

    update public.learner_progress set current_status = p_progress_status,
        version = p_progress_expected_version + 1, updated_at = timezone('utc', now())
    where learner_id = current_row.learner_id and version = p_progress_expected_version;
    get diagnostics progress_updated = row_count;
    if progress_updated <> 1 then
        raise exception 'learner progress CAS conflict' using errcode = '40001';
    end if;
    insert into public.outbox_events(event_id, event_type, aggregate_id, payload)
    values ((p_outbox ->> 'event_id')::uuid, p_outbox ->> 'event_type', current_row.learner_id,
        coalesce(p_outbox -> 'payload', '{}'::jsonb));
    update public.submissions set status = 'COMPLETED', outcome = p_outcome,
        version = current_row.version + 1, updated_at = timezone('utc', now())
    where reservation_id = current_row.reservation_id and version = p_expected_version
    returning * into current_row;
    if not found then raise exception 'submission finalization CAS conflict' using errcode = '40001'; end if;
    return current_row;
end;
$$;

-- Retention claim/finalize functions are service-only and lease protected.
create or replace function public.claim_expired_artifacts(p_limit integer, p_lease_owner text, p_lease_seconds integer)
returns setof public.artifacts
language plpgsql security definer set search_path = public, pg_temp
as $$
begin
    if p_limit <= 0 or p_lease_seconds <= 0 or p_lease_owner is null or char_length(p_lease_owner) = 0 then
        raise exception 'invalid retention lease parameters' using errcode = '22023';
    end if;
    return query
    with candidates as (
        select artifact_id from public.artifacts
        where retention_expires_at <= timezone('utc', now())
          and (purge_status = 'ACTIVE' or purge_status = 'PURGE_FAILED'
            or (purge_status = 'CLAIMED' and purge_lease_expires_at <= timezone('utc', now())))
        order by retention_expires_at, artifact_id limit greatest(p_limit, 0)
        for update skip locked
    )
    update public.artifacts a set purge_status = 'CLAIMED', purge_lease_owner = p_lease_owner,
        purge_lease_expires_at = timezone('utc', now()) + make_interval(secs => p_lease_seconds)
    from candidates c where a.artifact_id = c.artifact_id returning a.*;
end;
$$;

create or replace function public.finalize_artifact_purge(p_artifact_id uuid, p_lease_owner text, p_deleted boolean, p_details jsonb default '{}'::jsonb)
returns public.artifacts
language plpgsql security definer set search_path = public, pg_temp
as $$
declare result_row public.artifacts;
begin
    update public.artifacts set purge_status = case when p_deleted then 'PURGED' else 'PURGE_FAILED' end,
        purge_lease_owner = null, purge_lease_expires_at = null,
        purged_at = case when p_deleted then timezone('utc', now()) else null end
    where artifact_id = p_artifact_id and purge_status = 'CLAIMED' and purge_lease_owner = p_lease_owner
      and purge_lease_expires_at > timezone('utc', now())
    returning * into result_row;
    if not found then raise exception 'artifact purge lease conflict' using errcode = '40001'; end if;
    insert into public.retention_audit(artifact_id, learner_id, action, actor_id, details)
    values (result_row.artifact_id, result_row.learner_id,
        case when p_deleted then 'PURGED' else 'PURGE_FAILED' end,
        p_lease_owner, p_details);
    return result_row;
end;
$$;

-- RLS and explicit grants.  No anonymous role receives table or function
-- access; server workflows use service_role after repeating authorization.
do $$
declare table_name text;
begin
    foreach table_name in array array[
        'learners', 'external_identities', 'tasks', 'task_versions', 'artifacts',
        'submissions', 'evaluation_results', 'feedback_results', 'attempts',
        'skill_definitions', 'skill_evidence', 'learner_progress', 'outbox_events',
        'retention_audit', 'learner_deletion_requests'
    ] loop
        execute format('alter table public.%I enable row level security', table_name);
        execute format('revoke all on table public.%I from anon, authenticated', table_name);
        execute format('grant all on table public.%I to service_role', table_name);
    end loop;
end;
$$;
grant usage on schema public to authenticated, service_role;
grant select on public.tasks, public.task_versions, public.skill_definitions to authenticated;

create policy learners_select_own on public.learners for select to authenticated
using (learner_id = (select public.current_learner_id()));
create policy identities_select_own on public.external_identities for select to authenticated
using (learner_id = (select public.current_learner_id()));
create policy task_versions_published_read on public.task_versions for select to authenticated
using (status = 'PUBLISHED');
create policy tasks_read on public.tasks for select to authenticated using (true);
create policy skill_definitions_read on public.skill_definitions for select to authenticated using (true);
create policy artifacts_select_own on public.artifacts for select to authenticated
using (learner_id = (select public.current_learner_id()));
create policy submissions_select_own on public.submissions for select to authenticated
using (learner_id = (select public.current_learner_id()));
create policy evaluation_select_own on public.evaluation_results for select to authenticated
using (exists (select 1 from public.submissions s where s.submission_id = evaluation_results.submission_id and s.learner_id = (select public.current_learner_id())));
create policy feedback_select_own on public.feedback_results for select to authenticated
using (exists (select 1 from public.submissions s where s.submission_id = feedback_results.submission_id and s.learner_id = (select public.current_learner_id())));
create policy attempts_select_own on public.attempts for select to authenticated
using (learner_id = (select public.current_learner_id()));
create policy evidence_select_own on public.skill_evidence for select to authenticated
using (learner_id = (select public.current_learner_id()));
create policy progress_select_own on public.learner_progress for select to authenticated
using (learner_id = (select public.current_learner_id()));
create policy outbox_no_client_access on public.outbox_events for select to authenticated using (false);
create policy retention_no_client_access on public.retention_audit for select to authenticated using (false);
create policy deletion_select_own on public.learner_deletion_requests for select to authenticated
using (learner_id = (select public.current_learner_id()));

-- Storage objects are private and can only use generated learner/artifact IDs.
insert into storage.buckets (id, name, public, file_size_limit)
values ('submissions', 'submissions', false, 5242880)
on conflict (id) do update set public = false, file_size_limit = 5242880;
revoke all on table storage.objects from anon, authenticated;
-- No browser storage policies: uploads/downloads/deletes use backend-created
-- signed operations after server-side ownership checks.

revoke all on function public.reserve_submission(uuid, uuid, uuid, text, text, text, integer, text) from public, anon, authenticated;
revoke all on function public.finalize_submission(uuid, integer, text, jsonb, jsonb, jsonb, jsonb, text, integer, jsonb, jsonb) from public, anon, authenticated;
revoke all on function public.claim_expired_artifacts(integer, text, integer) from public, anon, authenticated;
revoke all on function public.finalize_artifact_purge(uuid, text, boolean, jsonb) from public, anon, authenticated;
revoke all on function public.current_learner_id() from public, anon;
grant execute on function public.current_learner_id() to authenticated, service_role;
grant execute on function public.reserve_submission(uuid, uuid, uuid, text, text, text, integer, text) to service_role;
grant execute on function public.finalize_submission(uuid, integer, text, jsonb, jsonb, jsonb, jsonb, text, integer, jsonb, jsonb) to service_role;
grant execute on function public.claim_expired_artifacts(integer, text, integer) to service_role;
grant execute on function public.finalize_artifact_purge(uuid, text, boolean, jsonb) to service_role;
