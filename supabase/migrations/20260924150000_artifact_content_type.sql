-- Preserve immutable artifact media types without invalidating existing rows.
alter table public.artifacts add column if not exists content_type text;

update public.artifacts
set content_type = case
  when lower(filename) like '%.csv' then 'text/csv'
  when lower(filename) like '%.xlsx' then 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
end
where content_type is null;

alter table public.artifacts add constraint artifacts_content_type_check
check (content_type is null or content_type in (
  'text/csv',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
));

-- Keep reserve_artifact for rollback compatibility; new callers bind content type.
drop function if exists public.reserve_artifact_v2(uuid, uuid, text, text, text, bigint, text, text, integer);
create or replace function public.reserve_artifact_v2(
    p_learner_id uuid,
    p_artifact_id uuid,
    p_object_path text,
    p_filename text,
    p_content_type text,
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
    expected_content_type text;
begin
    expected_content_type := case
        when lower(p_filename) like '%.csv' then 'text/csv'
        when lower(p_filename) like '%.xlsx' then 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else null
    end;
    if p_learner_id is null or p_artifact_id is null
        or p_object_path <> p_learner_id::text || '/' || p_artifact_id::text
        or p_filename is null or char_length(p_filename) not between 1 and 255
        or p_content_type is distinct from expected_content_type
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
            or current_row.content_type is distinct from p_content_type
            or current_row.size_bytes <> p_size_bytes
            or current_row.sha256 <> p_sha256 then
            raise exception 'artifact identity conflict' using errcode = '23505';
        end if;
        return jsonb_build_object('created', false, 'artifact', to_jsonb(current_row));
    end if;

    insert into public.artifacts(
        artifact_id, learner_id, object_path, filename, content_type, size_bytes, sha256,
        purge_status, purge_lease_owner, purge_lease_expires_at
    ) values (
        p_artifact_id, p_learner_id, p_object_path, p_filename, p_content_type, p_size_bytes, p_sha256,
        'UPLOADING', p_upload_owner,
        timezone('utc', now()) + make_interval(secs => p_upload_lease_seconds)
    ) returning * into current_row;
    return jsonb_build_object('created', true, 'artifact', to_jsonb(current_row));
end;
$$;

revoke all on function public.reserve_artifact_v2(uuid, uuid, text, text, text, bigint, text, text, integer)
    from public, anon, authenticated;
grant execute on function public.reserve_artifact_v2(uuid, uuid, text, text, text, bigint, text, text, integer)
    to service_role;
