-- Cloud progression authority.
--
-- This is a forward-only compatibility migration.  The public
-- finalize_submission signature intentionally remains unchanged so deployed
-- callers can be upgraded independently of the database.

create extension if not exists "uuid-ossp";

-- Version ordering is a publication concern, not a lexical version-string
-- concern ("10" must not sort before "2").  A current marker is optional for
-- older rows; published_at is the deterministic fallback for those rows.
alter table public.task_versions
    add column if not exists is_current boolean not null default false;

create unique index if not exists task_versions_one_current_published_idx
    on public.task_versions (task_id)
    where status = 'PUBLISHED' and is_current;

create or replace function public.current_published_task_version(p_task_id text)
returns uuid
language sql
stable
security definer
set search_path = public, pg_temp
as $$
    select task_version_id
    from public.task_versions
    where task_id = p_task_id and status = 'PUBLISHED'
    order by is_current desc, published_at desc nulls last, task_version_id desc
    limit 1
$$;

revoke all on function public.current_published_task_version(text)
    from public, anon, authenticated;
grant execute on function public.current_published_task_version(text) to service_role;

-- Small, private validators keep malformed JSON from reaching a PostgreSQL
-- cast.  Every failure has the same stable validation SQLSTATE/message shape;
-- provider details are never exposed to the caller.
create or replace function public._cloud_require_object(
    p_value jsonb,
    p_label text,
    p_required text[],
    p_optional text[] default '{}'::text[]
)
returns void
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    key_name text;
begin
    if p_value is null or jsonb_typeof(p_value) is distinct from 'object' then
        raise exception 'invalid % object', p_label using errcode = '22023';
    end if;
    foreach key_name in array p_required loop
        if not (p_value ? key_name) then
            raise exception 'missing % field: %', p_label, key_name using errcode = '22023';
        end if;
    end loop;
    for key_name in select jsonb_object_keys(p_value) loop
        if not (key_name = any(array_cat(p_required, p_optional))) then
            raise exception 'unexpected % field: %', p_label, key_name using errcode = '22023';
        end if;
    end loop;
end;
$$;

create or replace function public._cloud_json_string(
    p_object jsonb,
    p_key text,
    p_label text,
    p_allow_null boolean default false
)
returns text
language plpgsql
immutable
set search_path = public, pg_temp
as $$
begin
    if p_object is null or not (p_object ? p_key) then
        raise exception 'missing % field: %', p_label, p_key using errcode = '22023';
    end if;
    if p_allow_null and jsonb_typeof(p_object -> p_key) = 'null' then
        return null;
    end if;
    if jsonb_typeof(p_object -> p_key) is distinct from 'string'
        or char_length(btrim(p_object ->> p_key)) = 0 then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end if;
    return p_object ->> p_key;
end;
$$;

create or replace function public._cloud_json_uuid(
    p_object jsonb,
    p_key text,
    p_label text
)
returns uuid
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    value_text text;
begin
    value_text := public._cloud_json_string(p_object, p_key, p_label);
    if value_text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end if;
    return value_text::uuid;
end;
$$;

create or replace function public._cloud_json_integer(
    p_object jsonb,
    p_key text,
    p_label text,
    p_min integer default null,
    p_max integer default null
)
returns integer
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    value_text text;
    value_int integer;
begin
    if p_object is null or not (p_object ? p_key)
        or jsonb_typeof(p_object -> p_key) is distinct from 'number' then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end if;
    value_text := p_object ->> p_key;
    if value_text !~ '^-?(0|[1-9][0-9]*)$' then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end if;
    begin
        value_int := value_text::integer;
    exception when others then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end;
    if (p_min is not null and value_int < p_min)
        or (p_max is not null and value_int > p_max) then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end if;
    return value_int;
end;
$$;

create or replace function public._cloud_json_boolean(
    p_object jsonb,
    p_key text,
    p_label text
)
returns boolean
language plpgsql
immutable
set search_path = public, pg_temp
as $$
begin
    if p_object is null or not (p_object ? p_key)
        or jsonb_typeof(p_object -> p_key) is distinct from 'boolean' then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end if;
    return (p_object ->> p_key)::boolean;
end;
$$;

create or replace function public._cloud_json_timestamp(
    p_object jsonb,
    p_key text,
    p_label text,
    p_allow_null boolean default false
)
returns timestamptz
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    value_text text;
    value_timestamp timestamptz;
begin
    if p_object is null or not (p_object ? p_key) then
        raise exception 'missing % field: %', p_label, p_key using errcode = '22023';
    end if;
    if p_allow_null and jsonb_typeof(p_object -> p_key) = 'null' then
        return null;
    end if;
    value_text := public._cloud_json_string(p_object, p_key, p_label);
    begin
        value_timestamp := value_text::timestamptz;
    exception when others then
        raise exception 'invalid % field: %', p_label, p_key using errcode = '22023';
    end;
    return value_timestamp;
end;
$$;

create or replace function public._cloud_validate_evaluation(
    p_value jsonb,
    p_label text default 'evaluation'
)
returns void
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    item jsonb;
begin
    perform public._cloud_require_object(
        p_value, p_label,
        array['evaluation_id', 'evaluator_id', 'evaluator_version',
              'task_version_id', 'passed', 'score', 'checks', 'errors',
              'summary_ar', 'summary_en', 'duration_ms']
    );
    perform public._cloud_json_uuid(p_value, 'evaluation_id', p_label);
    perform public._cloud_json_string(p_value, 'evaluator_id', p_label);
    perform public._cloud_json_string(p_value, 'evaluator_version', p_label);
    perform public._cloud_json_uuid(p_value, 'task_version_id', p_label);
    perform public._cloud_json_boolean(p_value, 'passed', p_label);
    perform public._cloud_json_integer(p_value, 'score', p_label, 0, 100);
    if jsonb_typeof(p_value -> 'checks') is distinct from 'array'
        or jsonb_typeof(p_value -> 'errors') is distinct from 'array' then
        raise exception 'invalid % arrays', p_label using errcode = '22023';
    end if;
    if jsonb_typeof(p_value -> 'summary_ar') is distinct from 'string'
        or jsonb_typeof(p_value -> 'summary_en') is distinct from 'string' then
        raise exception 'invalid % summary field', p_label using errcode = '22023';
    end if;
    perform public._cloud_json_integer(p_value, 'duration_ms', p_label, 0, null);
    for item in select value from jsonb_array_elements(p_value -> 'checks') loop
        perform public._cloud_require_object(
            item, p_label || '.check', array['check_id', 'passed', 'weight', 'details']
        );
        perform public._cloud_json_string(item, 'check_id', p_label || '.check');
        perform public._cloud_json_boolean(item, 'passed', p_label || '.check');
        perform public._cloud_json_integer(item, 'weight', p_label || '.check', 0, null);
        perform public._cloud_json_string(item, 'details', p_label || '.check', true);
    end loop;
    for item in select value from jsonb_array_elements(p_value -> 'errors') loop
        perform public._cloud_require_object(
            item, p_label || '.error', array['code', 'message']
        );
        perform public._cloud_json_string(item, 'code', p_label || '.error');
        -- Empty messages are valid contract values, but the field must remain a string.
        if jsonb_typeof(item -> 'message') is distinct from 'string' then
            raise exception 'invalid % field: message', p_label || '.error'
                using errcode = '22023';
        end if;
    end loop;
end;
$$;

create or replace function public._cloud_validate_feedback(
    p_value jsonb,
    p_label text default 'feedback'
)
returns void
language plpgsql
immutable
set search_path = public, pg_temp
as $$
begin
    perform public._cloud_require_object(
        p_value, p_label,
        array['feedback_id', 'feedback_text', 'language', 'persona_id',
              'prompt_version', 'provider', 'model', 'used_fallback',
              'duration_ms']
    );
    perform public._cloud_json_uuid(p_value, 'feedback_id', p_label);
    -- feedback_text may be empty, matching the canonical contract.
    if jsonb_typeof(p_value -> 'feedback_text') is distinct from 'string' then
        raise exception 'invalid % field: feedback_text', p_label using errcode = '22023';
    end if;
    if public._cloud_json_string(p_value, 'language', p_label) not in ('ar-EG', 'en') then
        raise exception 'invalid % field: language', p_label using errcode = '22023';
    end if;
    perform public._cloud_json_string(p_value, 'persona_id', p_label);
    perform public._cloud_json_string(p_value, 'prompt_version', p_label);
    perform public._cloud_json_string(p_value, 'provider', p_label);
    perform public._cloud_json_string(p_value, 'model', p_label, true);
    perform public._cloud_json_boolean(p_value, 'used_fallback', p_label);
    perform public._cloud_json_integer(p_value, 'duration_ms', p_label, 0, null);
end;
$$;

create or replace function public._cloud_validate_attempt(
    p_value jsonb,
    p_label text default 'attempt'
)
returns void
language plpgsql
immutable
set search_path = public, pg_temp
as $$
begin
    perform public._cloud_require_object(
        p_value, p_label, array['attempt_id', 'attempt_number', 'started_at', 'completed_at']
    );
    perform public._cloud_json_uuid(p_value, 'attempt_id', p_label);
    perform public._cloud_json_integer(p_value, 'attempt_number', p_label, 1, null);
    perform public._cloud_json_timestamp(p_value, 'started_at', p_label);
    perform public._cloud_json_timestamp(p_value, 'completed_at', p_label, true);
end;
$$;

create or replace function public._cloud_validate_evidence(
    p_value jsonb,
    p_label text default 'evidence'
)
returns void
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    item jsonb;
begin
    if p_value is null or jsonb_typeof(p_value) is distinct from 'array' then
        raise exception 'invalid % array', p_label using errcode = '22023';
    end if;
    for item in select value from jsonb_array_elements(p_value) loop
        perform public._cloud_require_object(
            item, p_label || '.item',
            array['evidence_id', 'skill_id', 'check_id', 'awarded_points',
                  'available_points', 'recorded_at']
        );
        perform public._cloud_json_uuid(item, 'evidence_id', p_label || '.item');
        perform public._cloud_json_string(item, 'skill_id', p_label || '.item');
        perform public._cloud_json_string(item, 'check_id', p_label || '.item');
        if public._cloud_json_integer(item, 'awarded_points', p_label || '.item', 0, null)
            > public._cloud_json_integer(item, 'available_points', p_label || '.item', 1, null) then
            raise exception 'invalid % points', p_label || '.item' using errcode = '22023';
        end if;
        perform public._cloud_json_timestamp(item, 'recorded_at', p_label || '.item');
    end loop;
end;
$$;

create or replace function public._cloud_validate_outbox(
    p_value jsonb,
    p_label text default 'outbox'
)
returns void
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    payload jsonb;
begin
    perform public._cloud_require_object(
        p_value, p_label, array['event_id', 'event_type', 'payload']
    );
    perform public._cloud_json_uuid(p_value, 'event_id', p_label);
    if public._cloud_json_string(p_value, 'event_type', p_label) <> 'submission.processed' then
        raise exception 'invalid % event_type', p_label using errcode = '22023';
    end if;
    payload := p_value -> 'payload';
    perform public._cloud_require_object(
        payload, p_label || '.payload', array['submission_id', 'passed']
    );
    perform public._cloud_json_uuid(payload, 'submission_id', p_label || '.payload');
    perform public._cloud_json_boolean(payload, 'passed', p_label || '.payload');
end;
$$;

create or replace function public._cloud_validate_outcome(
    p_value jsonb,
    p_label text default 'outcome'
)
returns void
language plpgsql
immutable
set search_path = public, pg_temp
as $$
declare
    item jsonb;
begin
    perform public._cloud_require_object(
        p_value, p_label,
        array['submission_id', 'attempt_id', 'attempt_number', 'evaluation',
              'feedback', 'learner_status', 'task_status', 'skills']
    );
    perform public._cloud_json_uuid(p_value, 'submission_id', p_label);
    perform public._cloud_json_uuid(p_value, 'attempt_id', p_label);
    perform public._cloud_json_integer(p_value, 'attempt_number', p_label, 1, null);
    -- SubmissionOutcome is the public contract: evaluation/feedback IDs are
    -- generated persistence fields and are intentionally absent from its
    -- nested values.  Validate that public shape by injecting only a private
    -- validation sentinel, then compare to the caller records with IDs removed.
    if jsonb_typeof(p_value -> 'evaluation') is distinct from 'object'
        or jsonb_typeof(p_value -> 'feedback') is distinct from 'object'
        or (p_value -> 'evaluation') ? 'evaluation_id'
        or (p_value -> 'feedback') ? 'feedback_id' then
        raise exception 'invalid % nested persistence field', p_label using errcode = '22023';
    end if;
    perform public._cloud_validate_evaluation(
        jsonb_build_object('evaluation_id', '00000000-0000-4000-8000-000000000000'::uuid)
            || (p_value -> 'evaluation'), p_label || '.evaluation'
    );
    perform public._cloud_validate_feedback(
        jsonb_build_object('feedback_id', '00000000-0000-4000-8000-000000000000'::uuid)
            || (p_value -> 'feedback'), p_label || '.feedback'
    );
    if public._cloud_json_string(p_value, 'learner_status', p_label) not in (
        'ONBOARDING', 'READY', 'IN_TASK', 'PROCESSING', 'NEEDS_RETRY',
        'TASK_COMPLETED', 'PROGRAM_COMPLETED'
    ) then
        raise exception 'invalid % field: learner_status', p_label using errcode = '22023';
    end if;
    if public._cloud_json_string(p_value, 'task_status', p_label)
        not in ('AVAILABLE', 'ACTIVE', 'COMPLETED') then
        raise exception 'invalid % field: task_status', p_label using errcode = '22023';
    end if;
    if jsonb_typeof(p_value -> 'skills') is distinct from 'array' then
        raise exception 'invalid % field: skills', p_label using errcode = '22023';
    end if;
    for item in select value from jsonb_array_elements(p_value -> 'skills') loop
        perform public._cloud_require_object(item, p_label || '.skill', array['skill_id', 'score']);
        perform public._cloud_json_string(item, 'skill_id', p_label || '.skill');
        perform public._cloud_json_integer(item, 'score', p_label || '.skill', 0, 100);
    end loop;
end;
$$;

-- Only the service role may call these implementation helpers.  They are
-- deliberately not part of the application API.
do $$
declare
    function_name text;
begin
    foreach function_name in array array[
        '_cloud_require_object(jsonb,text,text[],text[])',
        '_cloud_json_string(jsonb,text,text,boolean)',
        '_cloud_json_uuid(jsonb,text,text)',
        '_cloud_json_integer(jsonb,text,text,integer,integer)',
        '_cloud_json_boolean(jsonb,text,text)',
        '_cloud_json_timestamp(jsonb,text,text,boolean)',
        '_cloud_validate_evaluation(jsonb,text)',
        '_cloud_validate_feedback(jsonb,text)',
        '_cloud_validate_attempt(jsonb,text)',
        '_cloud_validate_evidence(jsonb,text)',
        '_cloud_validate_outbox(jsonb,text)',
        '_cloud_validate_outcome(jsonb,text)'
    ] loop
        execute format('revoke all on function public.%s from public, anon, authenticated', function_name);
        execute format('grant execute on function public.%s to service_role', function_name);
    end loop;
end;
$$;

-- A forward replacement also tightens reservation validation.  It preserves
-- the old return type/signature and idempotency behavior.
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
    task_status text;
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
    select status into task_status
    from public.task_versions
    where task_version_id = p_task_version_id;
    if task_status is distinct from 'PUBLISHED' then
        raise exception 'task version is not published' using errcode = '42501';
    end if;
    if not exists (select 1 from public.learners where learner_id = p_learner_id)
        or not exists (
            select 1 from public.artifacts
            where artifact_id = p_artifact_id and learner_id = p_learner_id
        ) then
        raise exception 'submission references are not valid' using errcode = '42501';
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
        update public.submissions
        set lease_owner = p_lease_owner,
            lease_expires_at = timezone('utc', now()) + make_interval(secs => p_lease_seconds),
            version = current_row.version + 1,
            updated_at = timezone('utc', now())
        where reservation_id = current_row.reservation_id
          and version = current_row.version
        returning * into current_row;
        if not found then
            raise exception 'submission reservation CAS conflict' using errcode = '40001';
        end if;
        return current_row;
    end if;
    insert into public.submissions (
        learner_id, task_version_id, artifact_id, channel, idempotency_key,
        request_fingerprint, status, lease_expires_at, lease_owner
    ) values (
        p_learner_id, p_task_version_id, p_artifact_id, p_channel, p_idempotency_key,
        p_request_fingerprint, 'RECEIVED',
        timezone('utc', now()) + make_interval(secs => p_lease_seconds), p_lease_owner
    ) returning * into current_row;
    return current_row;
end;
$$;

-- The database derives every authoritative field below.  Caller JSON is only
-- accepted after strict shape/type validation and equality checks against the
-- persisted task-version mappings, evaluation checks, progress, and outcome.
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
    progress_row public.learner_progress;
    task_row public.task_versions;
    derived_status text;
    derived_task_status text;
    expected_attempt_number integer;
    supplied_attempt_number integer;
    expected_evidence jsonb;
    supplied_evidence_normalized jsonb;
    expected_skills jsonb;
    mapping jsonb;
    mapping_skill_id text;
    mapping_check_id text;
    mapping_weight integer;
    passed boolean;
    completed_at timestamptz;
    progress_updated integer;
begin
    -- Scalar parameters are checked before any JSON casts or row writes.
    if p_reservation_id is null
        or p_expected_version is null or p_expected_version <= 0
        or p_lease_owner is not distinct from null
        or char_length(btrim(p_lease_owner)) = 0
        or p_progress_expected_version is null or p_progress_expected_version <= 0
        or p_progress_status is null
        or p_progress_status not in (
            'ONBOARDING', 'READY', 'IN_TASK', 'PROCESSING', 'NEEDS_RETRY',
            'TASK_COMPLETED', 'PROGRAM_COMPLETED'
        ) then
        raise exception 'invalid submission finalization parameters' using errcode = '22023';
    end if;

    perform public._cloud_validate_evaluation(p_evaluation);
    perform public._cloud_validate_feedback(p_feedback);
    perform public._cloud_validate_attempt(p_attempt);
    perform public._cloud_validate_evidence(p_evidence);
    perform public._cloud_validate_outbox(p_outbox);
    perform public._cloud_validate_outcome(p_outcome);

    -- The nested outcome is not an authority and must be an exact echo of the
    -- validated records sent to this call.
    if p_outcome -> 'evaluation' <> (p_evaluation - 'evaluation_id')
        or p_outcome -> 'feedback' <> (p_feedback - 'feedback_id') then
        raise exception 'outcome record mismatch' using errcode = '22023';
    end if;

    select * into current_row
    from public.submissions
    where reservation_id = p_reservation_id
    for update;
    if not found then
        raise exception 'submission reservation not found' using errcode = 'P0002';
    end if;
    if current_row.version <> p_expected_version or current_row.status = 'COMPLETED' then
        raise exception 'submission reservation CAS conflict' using errcode = '40001';
    end if;
    if current_row.lease_owner is distinct from p_lease_owner then
        raise exception 'submission reservation owner conflict' using errcode = '42501';
    end if;
    if current_row.lease_expires_at <= timezone('utc', now()) then
        raise exception 'submission reservation lease expired' using errcode = '40001';
    end if;

    select * into task_row
    from public.task_versions
    where task_version_id = current_row.task_version_id
      and status = 'PUBLISHED'
    for share;
    if not found then
        raise exception 'task version is not published' using errcode = '42501';
    end if;

    if public._cloud_json_uuid(p_evaluation, 'task_version_id', 'evaluation')
            <> current_row.task_version_id
        or public._cloud_json_string(p_evaluation, 'evaluator_id', 'evaluation')
            <> task_row.evaluator_id
        or public._cloud_json_string(p_evaluation, 'evaluator_version', 'evaluation')
            <> task_row.evaluator_version then
        raise exception 'evaluation task version mismatch' using errcode = '22023';
    end if;
    passed := public._cloud_json_boolean(p_evaluation, 'passed', 'evaluation');

    -- Mapping rows are persisted task-version data, never caller evidence.
    if jsonb_typeof(task_row.skill_mappings) is distinct from 'array' then
        raise exception 'published task version has invalid skill mappings'
            using errcode = '22023';
    end if;
    for mapping in select value from jsonb_array_elements(task_row.skill_mappings) loop
        perform public._cloud_require_object(
            mapping, 'task_version.skill_mapping', array['skill_id', 'check_id', 'weight']
        );
        mapping_skill_id := public._cloud_json_string(mapping, 'skill_id', 'task_version.skill_mapping');
        mapping_check_id := public._cloud_json_string(mapping, 'check_id', 'task_version.skill_mapping');
        mapping_weight := public._cloud_json_integer(mapping, 'weight', 'task_version.skill_mapping', 0, null);
        if not exists (select 1 from public.skill_definitions where skill_id = mapping_skill_id) then
            raise exception 'task version mapping references unknown skill' using errcode = '22023';
        end if;
        if exists (
            select 1 from jsonb_array_elements(task_row.skill_mappings) x
            where x.value ->> 'skill_id' = mapping_skill_id
              and x.value ->> 'check_id' = mapping_check_id
            group by x.value ->> 'skill_id', x.value ->> 'check_id'
            having count(*) > 1
        ) then
            raise exception 'task version has duplicate skill mapping' using errcode = '22023';
        end if;
    end loop;

    completed_at := public._cloud_json_timestamp(p_attempt, 'completed_at', 'attempt', true);
    if completed_at is null and passed and jsonb_array_length(p_evidence) > 0 then
        raise exception 'passed evidence requires completed_at' using errcode = '22023';
    end if;

    -- Evidence must be the deterministic projection of persisted mappings and
    -- passed evaluation checks.  Its IDs match the canonical UUIDv5 scheme;
    -- arbitrary client-provided evidence cannot be smuggled into the audit.
    select coalesce(
        jsonb_agg(
            jsonb_build_object(
                'evidence_id', uuid_generate_v5(
                    '6ba7b812-9dad-11d1-80b4-00c04fd430c8'::uuid,
                    (public._cloud_json_uuid(p_attempt, 'attempt_id', 'attempt'))::text
                    || ':' || current_row.task_version_id::text || ':'
                    || (mapping.value ->> 'skill_id') || ':' || (mapping.value ->> 'check_id')
                ),
                'skill_id', mapping.value ->> 'skill_id',
                'check_id', mapping.value ->> 'check_id',
                'awarded_points', (mapping.value ->> 'weight')::integer,
                'available_points', (mapping.value ->> 'weight')::integer,
                'recorded_at', coalesce(completed_at, timezone('utc', now()))
            ) - 'recorded_at' order by mapping.value ->> 'skill_id', mapping.value ->> 'check_id'
        ) filter (where passed_check.value ->> 'passed' = 'true'
            and passed_check.value ->> 'check_id' = mapping.value ->> 'check_id'
            and (mapping.value ->> 'weight')::integer > 0),
        '[]'::jsonb
    ) into expected_evidence
    from jsonb_array_elements(task_row.skill_mappings) mapping
    cross join lateral jsonb_array_elements(p_evaluation -> 'checks') passed_check;
    select coalesce(
        jsonb_agg(item - 'recorded_at' order by item ->> 'skill_id', item ->> 'check_id'),
        '[]'::jsonb
    ) into supplied_evidence_normalized
    from jsonb_array_elements(p_evidence) item;
    if completed_at is not null and exists (
        select 1
        from jsonb_array_elements(p_evidence) item
        where (item ->> 'recorded_at')::timestamptz <> completed_at
    ) then
        raise exception 'skill evidence timestamp does not match attempt' using errcode = '22023';
    end if;
    if supplied_evidence_normalized <> expected_evidence then
        raise exception 'skill evidence does not match persisted mappings' using errcode = '22023';
    end if;

    -- Lock the progress row before deriving attempt number and progression.
    -- A second successful submission for this learner therefore loses the
    -- progress CAS and rolls back every audit/evidence/outbox write.
    select * into progress_row
    from public.learner_progress
    where learner_id = current_row.learner_id
    for update;
    if not found then
        raise exception 'learner progress not found' using errcode = 'P0002';
    end if;
    if progress_row.version <> p_progress_expected_version then
        raise exception 'learner progress CAS conflict' using errcode = '40001';
    end if;
    if progress_row.current_task_id is not null
        and progress_row.current_task_id <> task_row.task_id then
        raise exception 'submission task is not learner current task' using errcode = '22023';
    end if;

    if passed then
        if progress_row.current_status not in ('IN_TASK', 'PROCESSING', 'NEEDS_RETRY') then
            raise exception 'invalid progression state for passed evaluation' using errcode = '22023';
        end if;
        derived_status := 'TASK_COMPLETED';
        derived_task_status := 'COMPLETED';
    else
        if progress_row.current_status not in ('IN_TASK', 'PROCESSING', 'NEEDS_RETRY') then
            raise exception 'invalid progression state for failed evaluation' using errcode = '22023';
        end if;
        derived_status := 'NEEDS_RETRY';
        derived_task_status := 'ACTIVE';
    end if;
    if p_progress_status <> derived_status then
        raise exception 'progression status is not evaluation-derived' using errcode = '22023';
    end if;

    supplied_attempt_number := public._cloud_json_integer(p_attempt, 'attempt_number', 'attempt', 1, null);
    select coalesce(max(attempt_number), 0) + 1 into expected_attempt_number
    from public.attempts
    where learner_id = current_row.learner_id
      and task_version_id = current_row.task_version_id;
    if supplied_attempt_number <> expected_attempt_number then
        raise exception 'attempt number is not persisted-derived' using errcode = '22023';
    end if;

    -- Skills are also database-derived.  Existing persisted evidence plus the
    -- canonical new evidence must exactly equal the submitted outcome.
    with all_scores as (
        select skill_id, awarded_points
        from public.skill_evidence
        where learner_id = current_row.learner_id
        union all
        select mapping.value ->> 'skill_id', (mapping.value ->> 'weight')::integer
        from jsonb_array_elements(task_row.skill_mappings) mapping
        where passed
          and exists (
              select 1 from jsonb_array_elements(p_evaluation -> 'checks') check_value
              where check_value.value ->> 'check_id' = mapping.value ->> 'check_id'
                and check_value.value ->> 'passed' = 'true'
          )
          and (mapping.value ->> 'weight')::integer > 0
    ), totals as (
        select skill_id, least(100, greatest(0, sum(awarded_points)))::integer as score
        from all_scores
        group by skill_id
    )
    select coalesce(
        jsonb_agg(jsonb_build_object('skill_id', skill_id, 'score', score) order by skill_id),
        '[]'::jsonb
    ) into expected_skills
    from totals;
    if p_outcome -> 'skills' <> expected_skills then
        raise exception 'outcome skills are not persisted-derived' using errcode = '22023';
    end if;

    if public._cloud_json_uuid(p_outcome, 'submission_id', 'outcome') <> current_row.submission_id
        or public._cloud_json_uuid(p_outcome, 'attempt_id', 'outcome')
            <> public._cloud_json_uuid(p_attempt, 'attempt_id', 'attempt')
        or public._cloud_json_integer(p_outcome, 'attempt_number', 'outcome', 1, null)
            <> supplied_attempt_number
        or public._cloud_json_string(p_outcome, 'learner_status', 'outcome') <> derived_status
        or public._cloud_json_string(p_outcome, 'task_status', 'outcome') <> derived_task_status then
        raise exception 'outcome does not match persisted authority' using errcode = '22023';
    end if;

    if public._cloud_json_uuid(p_outbox -> 'payload', 'submission_id', 'outbox.payload')
            <> current_row.submission_id
        or public._cloud_json_boolean(p_outbox -> 'payload', 'passed', 'outbox.payload') <> passed then
        raise exception 'outbox does not match persisted authority' using errcode = '22023';
    end if;

    -- All validation is complete.  These writes are one atomic transaction;
    -- any later CAS/constraint failure rolls back every preceding insert.
    insert into public.evaluation_results (
        evaluation_id, submission_id, evaluator_id, evaluator_version, task_version_id,
        passed, score, checks, errors, summary_ar, summary_en, duration_ms
    ) values (
        (p_evaluation ->> 'evaluation_id')::uuid, current_row.submission_id,
        p_evaluation ->> 'evaluator_id', p_evaluation ->> 'evaluator_version',
        (p_evaluation ->> 'task_version_id')::uuid, (p_evaluation ->> 'passed')::boolean,
        (p_evaluation ->> 'score')::integer, p_evaluation -> 'checks',
        p_evaluation -> 'errors', p_evaluation ->> 'summary_ar',
        p_evaluation ->> 'summary_en', (p_evaluation ->> 'duration_ms')::integer
    );
    insert into public.feedback_results (
        feedback_id, submission_id, feedback_text, language, persona_id, prompt_version,
        provider, model, used_fallback, duration_ms
    ) values (
        (p_feedback ->> 'feedback_id')::uuid, current_row.submission_id,
        p_feedback ->> 'feedback_text', p_feedback ->> 'language', p_feedback ->> 'persona_id',
        p_feedback ->> 'prompt_version', p_feedback ->> 'provider', p_feedback ->> 'model',
        (p_feedback ->> 'used_fallback')::boolean, (p_feedback ->> 'duration_ms')::integer
    );
    insert into public.attempts (
        attempt_id, learner_id, submission_id, task_version_id, attempt_number,
        evaluation_id, feedback_id, evaluator_id, evaluator_version, prompt_version,
        started_at, completed_at
    ) values (
        (p_attempt ->> 'attempt_id')::uuid, current_row.learner_id, current_row.submission_id,
        current_row.task_version_id, supplied_attempt_number,
        (p_evaluation ->> 'evaluation_id')::uuid, (p_feedback ->> 'feedback_id')::uuid,
        p_evaluation ->> 'evaluator_id', p_evaluation ->> 'evaluator_version',
        p_feedback ->> 'prompt_version', (p_attempt ->> 'started_at')::timestamptz,
        (p_attempt ->> 'completed_at')::timestamptz
    );
    insert into public.skill_evidence (
        evidence_id, learner_id, attempt_id, task_version_id, skill_id, check_id,
        awarded_points, available_points, recorded_at
    ) select
        (item ->> 'evidence_id')::uuid, current_row.learner_id,
        (p_attempt ->> 'attempt_id')::uuid, current_row.task_version_id,
        item ->> 'skill_id', item ->> 'check_id',
        (item ->> 'awarded_points')::integer, (item ->> 'available_points')::integer,
        (item ->> 'recorded_at')::timestamptz
    from jsonb_array_elements(p_evidence) item;
    update public.learner_progress
    set current_status = derived_status,
        version = progress_row.version + 1,
        updated_at = timezone('utc', now())
    where learner_id = current_row.learner_id
      and version = p_progress_expected_version;
    get diagnostics progress_updated = row_count;
    if progress_updated <> 1 then
        raise exception 'learner progress CAS conflict' using errcode = '40001';
    end if;
    insert into public.outbox_events(event_id, event_type, aggregate_id, payload)
    values (
        (p_outbox ->> 'event_id')::uuid, 'submission.processed', current_row.learner_id,
        jsonb_build_object('submission_id', current_row.submission_id, 'passed', passed)
    );
    update public.submissions
    set status = 'COMPLETED', outcome = p_outcome,
        lease_owner = null, lease_expires_at = timezone('utc', now()),
        version = current_row.version + 1, updated_at = timezone('utc', now())
    where reservation_id = current_row.reservation_id
      and version = p_expected_version
      and lease_owner is not distinct from p_lease_owner
      and status <> 'COMPLETED'
      and lease_expires_at > timezone('utc', now())
    returning * into current_row;
    if not found then
        raise exception 'submission finalization CAS conflict' using errcode = '40001';
    end if;
    return current_row;
end;
$$;

revoke all on function public.reserve_submission(uuid, uuid, uuid, text, text, text, integer, text)
    from public, anon, authenticated;
revoke all on function public.finalize_submission(uuid, integer, text, jsonb, jsonb, jsonb, jsonb, text, integer, jsonb, jsonb)
    from public, anon, authenticated;
grant execute on function public.reserve_submission(uuid, uuid, uuid, text, text, text, integer, text)
    to service_role;
grant execute on function public.finalize_submission(uuid, integer, text, jsonb, jsonb, jsonb, jsonb, text, integer, jsonb, jsonb)
    to service_role;
