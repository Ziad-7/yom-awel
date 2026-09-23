-- Deterministic pgTAP coverage for the public RLS contract.
--
-- Run this file after `supabase db reset` (or against an isolated database)
-- with a database role that can SET ROLE to anon/authenticated/service_role.
-- All fixture writes are inside one transaction and are rolled back at the
-- end, so repeated runs never touch data outside this test.

begin;
select plan(49);

-- Stable IDs make failures easy to inspect while rollback keeps the fixture
-- isolated. Two learners and two Auth subjects exercise ownership mapping.
insert into public.learners (
    learner_id, display_name, preferred_language, status, state_machine_version
) values
    ('00000000-0000-0000-0000-000000000001', 'RLS learner A', 'en', 'READY', '1'),
    ('00000000-0000-0000-0000-000000000002', 'RLS learner B', 'en', 'READY', '1');
insert into public.external_identities (
    identity_id, learner_id, provider, provider_subject, is_anonymous
)
values
    ('00000000-0000-0000-0000-000000000011',
     '00000000-0000-0000-0000-000000000001', 'web', '00000000-0000-0000-0000-0000000000a1', true),
    ('00000000-0000-0000-0000-000000000012',
     '00000000-0000-0000-0000-000000000002', 'web', '00000000-0000-0000-0000-0000000000b2', true);
insert into public.tasks (task_id, title)
values ('rls-test-task', 'RLS test task');
insert into public.task_versions (
    task_version_id, task_id, version, instructions_ar, instructions_en,
    artifact_schema, evaluator_id, evaluator_version, pass_threshold,
    skill_mappings, content_hash, status, published_at
) values
    ('00000000-0000-0000-0000-000000000101', 'rls-test-task', 'published',
     'تعليمات منشورة', 'Published instructions', '{}'::jsonb, 'evaluator', '1', 70,
     '[{"skill_id":"rls-test-skill","check_id":"clarity","weight":1}]'::jsonb,
     repeat('a', 64), 'PUBLISHED', timezone('utc', now())),
    ('00000000-0000-0000-0000-000000000102', 'rls-test-task', 'draft',
     'تعليمات مسودة', 'Draft instructions', '{}'::jsonb, 'evaluator', '1', 70,
     '[{"skill_id":"rls-test-skill","check_id":"clarity","weight":1}]'::jsonb,
     repeat('b', 64), 'DRAFT', null);
insert into public.skill_definitions (skill_id, title, description)
values ('rls-test-skill', 'RLS skill', 'RLS test skill');
insert into public.artifacts (
    artifact_id, learner_id, object_path, filename, size_bytes, sha256
) values
    ('00000000-0000-0000-0000-000000000201',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000001/00000000-0000-0000-0000-000000000201',
     'a.txt', 1, repeat('c', 64)),
    ('00000000-0000-0000-0000-000000000202',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000002/00000000-0000-0000-0000-000000000202',
     'b.txt', 1, repeat('d', 64));
insert into public.submissions (
    reservation_id, submission_id, learner_id, task_version_id, artifact_id,
    channel, idempotency_key, request_fingerprint, status, lease_expires_at,
    lease_owner
) values
    ('00000000-0000-0000-0000-000000000301',
     '00000000-0000-0000-0000-000000000311',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000101',
     '00000000-0000-0000-0000-000000000201', 'web', 'rls-a', repeat('e', 64),
     'RECEIVED', timezone('utc', now()) + interval '1 hour', 'rls-test'),
    ('00000000-0000-0000-0000-000000000302',
     '00000000-0000-0000-0000-000000000312',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000101',
     '00000000-0000-0000-0000-000000000202', 'web', 'rls-b', repeat('f', 64),
     'RECEIVED', timezone('utc', now()) + interval '1 hour', 'rls-test');
insert into public.evaluation_results (
    evaluation_id, submission_id, evaluator_id, evaluator_version,
    task_version_id, passed, score, summary_ar, summary_en, duration_ms
) values
    ('00000000-0000-0000-0000-000000000401',
     '00000000-0000-0000-0000-000000000311', 'evaluator', '1',
     '00000000-0000-0000-0000-000000000101', true, 90, 'جيد', 'Good', 1),
    ('00000000-0000-0000-0000-000000000402',
     '00000000-0000-0000-0000-000000000312', 'evaluator', '1',
     '00000000-0000-0000-0000-000000000101', false, 10, 'حاول مجددا', 'Retry', 1);
insert into public.feedback_results (
    feedback_id, submission_id, feedback_text, language, persona_id,
    prompt_version, provider, model, used_fallback, duration_ms
) values
    ('00000000-0000-0000-0000-000000000501',
     '00000000-0000-0000-0000-000000000311', 'Good', 'en', 'rls', '1', 'test', 'test', false, 1),
    ('00000000-0000-0000-0000-000000000502',
     '00000000-0000-0000-0000-000000000312', 'Retry', 'en', 'rls', '1', 'test', 'test', true, 1);
insert into public.attempts (
    attempt_id, learner_id, submission_id, task_version_id, attempt_number,
    evaluation_id, feedback_id, evaluator_id, evaluator_version, prompt_version,
    started_at
) values
    ('00000000-0000-0000-0000-000000000601',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000311',
     '00000000-0000-0000-0000-000000000101', 1,
     '00000000-0000-0000-0000-000000000401',
     '00000000-0000-0000-0000-000000000501', 'evaluator', '1', '1', timezone('utc', now())),
    ('00000000-0000-0000-0000-000000000602',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000312',
     '00000000-0000-0000-0000-000000000101', 1,
     '00000000-0000-0000-0000-000000000402',
     '00000000-0000-0000-0000-000000000502', 'evaluator', '1', '1', timezone('utc', now()));
insert into public.skill_evidence (
    evidence_id, learner_id, attempt_id, task_version_id, skill_id, check_id,
    awarded_points, available_points
) values
    ('00000000-0000-0000-0000-000000000701',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000601',
     '00000000-0000-0000-0000-000000000101', 'rls-test-skill', 'clarity', 1, 1),
    ('00000000-0000-0000-0000-000000000702',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000602',
     '00000000-0000-0000-0000-000000000101', 'rls-test-skill', 'clarity', 0, 1);
insert into public.learner_progress (learner_id, current_status, version)
values
    ('00000000-0000-0000-0000-000000000001', 'READY', 1),
    ('00000000-0000-0000-0000-000000000002', 'READY', 1);
insert into public.outbox_events (event_id, event_type, aggregate_id)
values
    ('00000000-0000-0000-0000-000000000801', 'rls.test', '00000000-0000-0000-0000-000000000001'),
    ('00000000-0000-0000-0000-000000000802', 'rls.test', '00000000-0000-0000-0000-000000000002');
insert into public.retention_audit (
    audit_id, requested_learner_id, learner_id, action, actor_id
)
values
    ('00000000-0000-0000-0000-000000000901',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000001', 'PURGED', 'rls'),
    ('00000000-0000-0000-0000-000000000902',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000002', 'PURGED', 'rls');
insert into public.learner_deletion_requests (
    request_id, learner_id, requested_learner_id, auth_user_id, requested_by
)
values
    ('00000000-0000-0000-0000-000000001001',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-0000000000a1', 'rls'),
    ('00000000-0000-0000-0000-000000001002',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-0000000000b2', 'rls');
insert into public.artifact_cleanup_queue (
    cleanup_id, learner_id, artifact_id, object_path, sha256, size_bytes, reason
) values
    ('00000000-0000-0000-0000-000000001101',
     '00000000-0000-0000-0000-000000000001',
     '00000000-0000-0000-0000-000000000201',
     '00000000-0000-0000-0000-000000000001/00000000-0000-0000-0000-000000000201',
     repeat('c', 64), 1, 'UPLOAD_FAILED'),
    ('00000000-0000-0000-0000-000000001102',
     '00000000-0000-0000-0000-000000000002',
     '00000000-0000-0000-0000-000000000202',
     '00000000-0000-0000-0000-000000000002/00000000-0000-0000-0000-000000000202',
     repeat('d', 64), 1, 'UPLOAD_FAILED');

-- All public application tables are RLS enabled, including the recovery queue.
select ok(
    (select count(*) = 16 and bool_and(c.relrowsecurity)
     from pg_class c
     join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind = 'r'),
    'all public application tables have RLS enabled'
);

select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000a1', true);
select set_config('request.jwt.claim.role', 'authenticated', true);
set local role authenticated;

select is((select count(*)::integer from public.learners), 1, 'owner reads own learner');
select is((select count(*)::integer from public.external_identities), 1, 'owner reads own identity');
select is((select count(*)::integer from public.artifacts), 1, 'owner reads own artifact');
select is((select count(*)::integer from public.submissions), 1, 'owner reads own submission');
select is((select count(*)::integer from public.evaluation_results), 1, 'owner reads own evaluation');
select is((select count(*)::integer from public.feedback_results), 1, 'owner reads own feedback');
select is((select count(*)::integer from public.attempts), 1, 'owner reads own attempt');
select is((select count(*)::integer from public.skill_evidence), 1, 'owner reads own evidence');
select is((select count(*)::integer from public.learner_progress), 1, 'owner reads own progress');
select is((select count(*)::integer from public.learner_deletion_requests), 1, 'owner reads own deletion request');

select is((select count(*)::integer from public.learners
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another learner');
select is((select count(*)::integer from public.external_identities
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another identity');
select is((select count(*)::integer from public.artifacts
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another artifact');
select is((select count(*)::integer from public.submissions
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another submission');
select is((select count(*)::integer from public.evaluation_results
           where submission_id = '00000000-0000-0000-0000-000000000312'), 0,
          'owner cannot read another evaluation');
select is((select count(*)::integer from public.feedback_results
           where submission_id = '00000000-0000-0000-0000-000000000312'), 0,
          'owner cannot read another feedback');
select is((select count(*)::integer from public.attempts
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another attempt');
select is((select count(*)::integer from public.skill_evidence
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another evidence row');
select is((select count(*)::integer from public.learner_progress
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another progress row');
select is((select count(*)::integer from public.learner_deletion_requests
           where learner_id = '00000000-0000-0000-0000-000000000002'), 0,
          'owner cannot read another deletion request');

select is((select count(*)::integer from public.tasks where task_id = 'rls-test-task'), 1,
          'authenticated clients read shared tasks');
select is((select count(*)::integer from public.task_versions where status = 'PUBLISHED'), 1,
          'authenticated clients read published task versions');
select is((select count(*)::integer from public.task_versions where status = 'DRAFT'), 0,
          'authenticated clients cannot read draft task versions');
select is((select count(*)::integer from public.skill_definitions where skill_id = 'rls-test-skill'), 1,
          'authenticated clients read shared skills');

reset role;

-- Anonymous roles have no table privileges; PostgREST therefore exposes zero
-- rows instead of relying on a permissive policy that could leak metadata.
select ok(not has_table_privilege('anon', 'public.learners', 'SELECT'),
          'anon cannot select learners');
select ok(not has_table_privilege('anon', 'public.tasks', 'SELECT'),
          'anon cannot select shared catalogs');
select ok(not has_table_privilege('anon', 'public.artifacts', 'SELECT'),
          'anon cannot select artifacts');

select ok(not has_table_privilege('authenticated', 'public.learners', 'INSERT'),
          'authenticated cannot insert learner rows');
select ok(not has_table_privilege('authenticated', 'public.artifacts', 'UPDATE'),
          'authenticated cannot update artifact rows');
select ok(not has_table_privilege('authenticated', 'public.artifacts', 'DELETE'),
          'authenticated cannot delete artifact rows');
select ok(not has_table_privilege('anon', 'public.learners', 'INSERT'),
          'anon cannot insert learner rows');
select ok(not has_table_privilege('anon', 'public.tasks', 'UPDATE'),
          'anon cannot update catalog rows');

set local role authenticated;
select throws_ok(
    $$update public.artifacts
      set learner_id = '00000000-0000-0000-0000-000000000002'::uuid
      where artifact_id = '00000000-0000-0000-0000-000000000201'::uuid$$,
    '42501',
    'permission denied for table artifacts',
    'authenticated cross-owner mutation is denied'
);
reset role;

select ok(has_function_privilege('authenticated', 'public.current_learner_id()', 'EXECUTE'),
          'authenticated may resolve current learner');
select ok(not has_function_privilege('anon', 'public.current_learner_id()', 'EXECUTE'),
          'anon cannot resolve current learner');
select ok(not has_function_privilege('service_role', 'public.current_learner_id()', 'EXECUTE'),
          'service role does not receive client learner helper');

select ok(
    not exists (
        select 1 from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public'
          and p.prosecdef
          and p.proname <> 'current_learner_id'
          and has_function_privilege('authenticated', p.oid, 'EXECUTE')
    ),
    'authenticated cannot execute service RPCs'
);
select ok(
    not exists (
        select 1 from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public'
          and p.prosecdef
          and p.proname <> 'current_learner_id'
          and has_function_privilege('anon', p.oid, 'EXECUTE')
    ),
    'anon cannot execute service RPCs'
);
select ok(
    (select count(*) from pg_proc p
     join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.prosecdef and p.proname <> 'current_learner_id'
       and has_function_privilege('service_role', p.oid, 'EXECUTE'))
    = (select count(*) from pg_proc p
       join pg_namespace n on n.oid = p.pronamespace
       where n.nspname = 'public' and p.prosecdef and p.proname <> 'current_learner_id'),
    'service role may execute every service RPC'
);

select is((select public from storage.buckets where id = 'submissions'), false,
          'submissions storage bucket is private');
select ok((select not rolbypassrls from pg_roles where rolname = 'authenticated'),
          'authenticated cannot bypass storage RLS');
select ok((select not rolbypassrls from pg_roles where rolname = 'anon'),
          'anon cannot bypass storage RLS');
select is((select count(*)::integer from pg_policies
           where schemaname = 'storage' and tablename = 'objects'
             and (roles @> array['anon'::name] or roles @> array['authenticated'::name])), 0,
          'storage has no client policies');

select ok(has_table_privilege('service_role', 'public.learners', 'SELECT'),
          'service role can administer application tables');
select ok(has_table_privilege('service_role', 'public.learners', 'INSERT'),
          'service role can write application tables');
select ok(has_table_privilege('service_role', 'storage.objects', 'SELECT'),
          'service role can administer private storage');
select ok(not has_table_privilege('authenticated', 'public.artifact_cleanup_queue', 'SELECT'),
          'authenticated cannot read cleanup queue');
select is((select count(*)::integer from pg_policies
           where schemaname = 'public' and tablename = 'artifact_cleanup_queue'), 0,
          'cleanup queue has no client policy');

select * from finish();
rollback;
