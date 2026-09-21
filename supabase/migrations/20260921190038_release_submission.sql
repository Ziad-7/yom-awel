-- Service-only CAS lease release for evaluator failure paths.
-- External evaluation never holds a database transaction open.
create or replace function public.expire_submission(
    p_learner_id uuid,
    p_idempotency_key text,
    p_expected_version integer,
    p_lease_owner text
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    current_row public.submissions;
begin
    if p_learner_id is null
        or p_idempotency_key is null
        or char_length(p_idempotency_key) = 0
        or p_expected_version <= 0
        or p_lease_owner is null
        or char_length(p_lease_owner) = 0 then
        raise exception 'invalid submission lease release parameters' using errcode = '22023';
    end if;

    select * into current_row
    from public.submissions
    where learner_id = p_learner_id and idempotency_key = p_idempotency_key
    for update;
    if not found or current_row.status = 'COMPLETED' then
        return;
    end if;
    if current_row.version <> p_expected_version then
        raise exception 'submission reservation CAS conflict' using errcode = '40001';
    end if;
    if current_row.lease_owner <> p_lease_owner then
        raise exception 'submission reservation owner conflict' using errcode = '42501';
    end if;

    update public.submissions
    set lease_expires_at = timezone('utc', now()),
        version = current_row.version + 1,
        updated_at = timezone('utc', now())
    where reservation_id = current_row.reservation_id
      and version = p_expected_version
      and lease_owner = p_lease_owner;
    if not found then
        raise exception 'submission reservation CAS conflict' using errcode = '40001';
    end if;
end;
$$;

revoke all on function public.expire_submission(uuid, text, integer, text)
    from public, anon, authenticated;
grant execute on function public.expire_submission(uuid, text, integer, text)
    to service_role;
