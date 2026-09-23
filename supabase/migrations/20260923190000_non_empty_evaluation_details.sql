-- Check details are required learner-safe text. 20260923180000 validated them
-- with p_allow_null = true, so the database accepted null details that the Python
-- EvaluationCheck contract rejects. Without that flag _cloud_json_string rejects
-- null, non-string, and blank values, matching EvaluationCheck.details_ar/en.

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
            item,
            p_label || '.check',
            array[
                'check_id', 'passed', 'weight', 'details_ar', 'details_en',
                'diagnostic_code'
            ]
        );
        perform public._cloud_json_string(item, 'check_id', p_label || '.check');
        perform public._cloud_json_boolean(item, 'passed', p_label || '.check');
        perform public._cloud_json_integer(item, 'weight', p_label || '.check', 0, null);
        perform public._cloud_json_string(item, 'details_ar', p_label || '.check');
        perform public._cloud_json_string(item, 'details_en', p_label || '.check');
        perform public._cloud_json_string(item, 'diagnostic_code', p_label || '.check');
    end loop;
    for item in select value from jsonb_array_elements(p_value -> 'errors') loop
        perform public._cloud_require_object(
            item, p_label || '.error', array['code', 'message']
        );
        perform public._cloud_json_string(item, 'code', p_label || '.error');
        if jsonb_typeof(item -> 'message') is distinct from 'string' then
            raise exception 'invalid % field: message', p_label || '.error'
                using errcode = '22023';
        end if;
    end loop;
end;
$$;
