# Member 5 Experience and Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver accessible Arabic web and Telegram experiences, integrate every backend module through canonical use cases, and deploy two verified zero-cost Vercel Hobby projects.

**Architecture:** Next.js 16 renders the learner experience and consumes a generated OpenAPI client. FastAPI exposes thin transport routes and a Telegram webhook over Member 2's application services. Member 5 starts against canonical fakes, then replaces evaluator, feedback, and persistence bindings one at a time after contract approval.

**Tech Stack:** Node.js 24, Next.js 16 App Router, TypeScript, React, Playwright, Vitest, Python 3.12, FastAPI, HTTPX, python-telegram-bot webhook-compatible types, Vercel Python Functions/Hobby, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md`

## Global Constraints

- Use two Vercel Hobby projects from the same personal GitHub repository; do not require Vercel Services beta or Pro.
- Durable data and artifacts never rely on Vercel local filesystem.
- Web and Telegram invoke the same application use cases.
- Browser bundles contain no service-role, Gemini, Telegram, or database credentials.
- Uploads go directly to private Supabase Storage through short-lived authorization and are capped at 5 MB.
- Production Telegram uses webhooks; polling is local-development-only.
- Arabic RTL, keyboard navigation, accessible names, focus management, and non-color state indicators are mandatory.
- Every user-facing pull request includes a Vercel preview or locally captured equivalent until Vercel is connected.
- Local mode works without cloud accounts using SQLite, local artifacts, and deterministic feedback.

## Review Focus

- Telegram webhook replay and browser retries must preserve idempotency.
- Vercel preview and production environment variables must not cross-contaminate.
- Direct uploads must not let one learner select another learner's artifact ID or signed URL.
- Mixed RTL/LTR content, file names, scores, and technical tokens must remain readable and accessible.
- Python function bundle and execution must remain inside Hobby limits and avoid paid configuration.

---

### Task M5-1: Establish Monorepo Tooling and CI Baseline

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/package-lock.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `services/api/api/index.py`
- Create: `services/api/src/yom_awel/transport/app.py`
- Create: `.github/workflows/ci.yml`
- Create: `.env.example`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Member 2 package/contracts and repository structure from the spec.
- Produces: buildable web/API shells and one CI command surface for all lanes.

- [ ] **Step 1: Write failing smoke tests**

Create `services/api/tests/transport/test_health.py`:

```python
from fastapi.testclient import TestClient

from yom_awel.transport.app import create_app


def test_health_is_safe_and_ready() -> None:
    response = TestClient(create_app()).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Create `apps/web/src/app/page.test.tsx` asserting the Arabic product name and `dir="rtl"` shell.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
cd services/api && uv run pytest tests/transport/test_health.py -q
cd ../../apps/web && npm test
```

Expected: FAIL because shells do not exist.

- [ ] **Step 3: Create the Next.js shell**

Configure App Router, TypeScript strict mode, ESLint, test runner, Arabic `lang="ar"`, `dir="rtl"`, accessible skip link, local font fallback, and no analytics package. Commit the generated lockfile.

- [ ] **Step 4: Create FastAPI composition shell**

Implement `create_app()` with versioned router and `/api/v1/health`. Export `app = create_app()` from `services/api/api/index.py` for Vercel Python runtime discovery.

- [ ] **Step 5: Define environment contract**

List variable names and server/client scope in `.env.example` without values:

```text
APP_ENV
API_BASE_URL
NEXT_PUBLIC_API_BASE_URL
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SERVICE_ROLE_KEY
GEMINI_API_KEY
GEMINI_MODEL
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
LOCAL_DATABASE_PATH
LOCAL_ARTIFACT_ROOT
```

Only `NEXT_PUBLIC_API_BASE_URL` may be browser-exposed.

- [ ] **Step 6: Add CI jobs**

Create separate Python and web jobs. Python runs locked sync, Ruff, mypy, and pytest. Web runs `npm ci`, lint, typecheck, tests, and build. Use only standard public-repository GitHub-hosted runners.

- [ ] **Step 7: Run local baseline**

```bash
cd services/api && uv sync --locked && uv run ruff check . && uv run mypy src && uv run pytest -q
cd ../../apps/web && npm ci && npm run lint && npm run typecheck && npm test && npm run build
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add apps services/api/api services/api/src/yom_awel/transport .github/workflows/ci.yml .env.example .gitignore
git commit -m "build: establish web and API workspace"
```

### Task M5-2: Build Contract-Compatible Fakes and API Routes

**Files:**
- Create: `services/api/src/yom_awel/transport/dependencies.py`
- Create: `services/api/src/yom_awel/transport/fakes.py`
- Create: `services/api/src/yom_awel/transport/routes/learners.py`
- Create: `services/api/src/yom_awel/transport/routes/tasks.py`
- Create: `services/api/src/yom_awel/transport/routes/submissions.py`
- Create: `services/api/src/yom_awel/transport/routes/profiles.py`
- Create: `services/api/src/yom_awel/transport/errors.py`
- Test: `services/api/tests/transport/test_routes_with_fakes.py`

**Interfaces:**
- Consumes: Member 2 canonical schemas/fixtures.
- Produces: stable OpenAPI routes used by web and Telegram before real modules merge.

- [ ] **Step 1: Write route contract tests from fixtures**

Test exact response payloads for onboarding, current task, upload authorization, failed submission, passed submission, duplicate submission, and skills profile. Test validation and authorization errors use canonical `ApplicationError`.

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/transport/test_routes_with_fakes.py -q`

Expected: FAIL because routes/fakes do not exist.

- [ ] **Step 3: Implement fixture-backed use-case fakes**

Load canonical JSON through Pydantic models at startup. Select pass/fail/fallback behavior with explicit test-only dependency overrides, never request query flags enabled in production.

- [ ] **Step 4: Implement versioned routes**

Expose:

```text
POST /api/v1/learners/onboard
GET  /api/v1/tasks/current
POST /api/v1/artifacts/upload-authorization
POST /api/v1/submissions
GET  /api/v1/submissions/{submission_id}
GET  /api/v1/skills
```

Require authentication context and `Idempotency-Key` for submission mutation.

- [ ] **Step 5: Map application errors**

Map stable codes to 400, 401, 403, 404, 409, 413, 422, 429, and 503 without exposing stack traces or provider payloads.

- [ ] **Step 6: Export and snapshot OpenAPI**

Create `services/api/scripts/export_openapi.py` and commit `contracts/openapi.json`. Test rerunning creates no diff.

- [ ] **Step 7: Run and commit**

```bash
cd services/api
uv run pytest tests/transport tests/contract -q
uv run python scripts/export_openapi.py
git add src/yom_awel/transport tests/transport scripts/export_openapi.py ../../../contracts/openapi.json
git commit -m "feat: add contract-first API transport"
```

### Task M5-3: Generate Web Client and Build Arabic Learner Flow Against Fakes

**Files:**
- Create: `apps/web/src/lib/api/generated.ts`
- Create: `apps/web/src/lib/api/client.ts`
- Create: `apps/web/src/app/onboarding/page.tsx`
- Create: `apps/web/src/app/workplace/page.tsx`
- Create: `apps/web/src/app/skills/page.tsx`
- Create: `apps/web/src/components/task-card.tsx`
- Create: `apps/web/src/components/submission-panel.tsx`
- Create: `apps/web/src/components/feedback-panel.tsx`
- Create: `apps/web/src/components/skills-profile.tsx`
- Test: `apps/web/src/components/submission-panel.test.tsx`
- Test: `apps/web/tests/e2e/fake-flow.spec.ts`

**Interfaces:**
- Consumes: `contracts/openapi.json` and fake API outcomes.
- Produces: typed accessible RTL flow independent of unfinished real adapters.

- [ ] **Step 1: Add generated-client drift test**

Add `npm run api:generate` and `npm run api:check`; the check regenerates into a temporary file and fails on a diff from `generated.ts`.

- [ ] **Step 2: Write component state tests**

Test idle, selected file, uploading, evaluating, failed result, fallback feedback, passed result, duplicate response, retry, and service unavailable states. Assert focus moves to the result heading and status is announced through an ARIA live region.

- [ ] **Step 3: Write RTL flow test**

Use Playwright against the fake API to onboard, open task, select a valid file fixture, receive fail, retry with pass, and open skills. Assert HTML language/direction, keyboard completion, and text alternatives.

- [ ] **Step 4: Run tests and confirm failure**

Run: `cd apps/web && npm test && npx playwright test tests/e2e/fake-flow.spec.ts`

Expected: FAIL because pages/components/client do not exist.

- [ ] **Step 5: Generate the typed client**

Generate TypeScript types from committed OpenAPI. Wrap fetch with correlation ID, learner-safe error parsing, timeout, and idempotency header support. Do not re-declare backend response interfaces manually.

- [ ] **Step 6: Implement the web journey**

Build Arabic-first pages with consistent workplace conversation, task requirements, download/upload actions, deterministic result separation from AI coaching, retry guidance, and skills evidence. Use logical CSS properties for RTL/LTR mixtures.

- [ ] **Step 7: Add accessibility behavior**

Provide labelled controls, keyboard-only operation, visible focus, live status, text status icons, error summaries, and correct direction wrappers for filenames/code/numbers.

- [ ] **Step 8: Run and commit**

```bash
cd apps/web
npm run api:check
npm run lint
npm run typecheck
npm test
npx playwright test tests/e2e/fake-flow.spec.ts
git add .
git commit -m "feat: add accessible Arabic learner experience"
```

### Task M5-4: Implement Private Signed Artifact Flow

**Files:**
- Create: `apps/web/src/lib/uploads.ts`
- Modify: `apps/web/src/components/submission-panel.tsx`
- Create: `services/api/tests/transport/test_upload_authorization.py`
- Create: `apps/web/src/lib/uploads.test.ts`

**Interfaces:**
- Consumes: Member 2 artifact-store port and upload authorization route.
- Produces: direct private upload followed by artifact-ID submission.

- [ ] **Step 1: Write backend authorization tests**

Assert authenticated ownership, supported MIME/extension, declared size `<= 5 MB`, generated object path, short expiry, one-time artifact ID, and denial for wrong learner/task.

- [ ] **Step 2: Write browser upload tests**

Mock authorization and storage endpoints. Assert browser sends file to signed URL, never receives service-role credentials, then submits artifact ID/hash/idempotency key. Test abort, expired URL, network failure, one byte over limit, and retry.

- [ ] **Step 3: Run tests and confirm failure**

Run:

```bash
cd services/api && uv run pytest tests/transport/test_upload_authorization.py -q
cd ../../apps/web && npm test -- uploads
```

Expected: FAIL because upload flow does not exist.

- [ ] **Step 4: Implement direct upload**

Calculate SHA-256 in the browser where supported, request authorization with metadata, upload directly, then call submission route. Treat signed URL as sensitive and do not log it.

- [ ] **Step 5: Enforce backend revalidation**

Before evaluation, verify artifact record ownership, content type, size, hash, bucket, object path, task version, and unused/accepted state. Client claims are never authoritative.

- [ ] **Step 6: Run and commit**

```bash
cd services/api && uv run pytest tests/transport/test_upload_authorization.py -q
cd ../../apps/web && npm test -- uploads
git add apps/web services/api/tests/transport
git commit -m "feat: add private direct artifact uploads"
```

### Task M5-5: Implement Telegram Webhook Adapter

**Files:**
- Create: `services/api/src/yom_awel/transport/telegram.py`
- Create: `services/api/src/yom_awel/transport/routes/telegram.py`
- Create: `services/api/tests/transport/test_telegram_webhook.py`
- Create: `services/api/tests/transport/fixtures/telegram_start.json`
- Create: `services/api/tests/transport/fixtures/telegram_document.json`

**Interfaces:**
- Consumes: onboarding, current-task, submission, and skills use cases.
- Produces: webhook route with channel identity/idempotency mapping and learner-safe messages.

- [ ] **Step 1: Write webhook-secret tests**

Assert missing or wrong `X-Telegram-Bot-Api-Secret-Token` returns 401 without processing. Correct secret accepts known update fixtures.

- [ ] **Step 2: Write command/document tests**

Test `/start`, `/task`, `/skills`, supported document, unsupported document, missing caption/note, and evaluator fallback. Mock outbound Telegram calls.

- [ ] **Step 3: Write replay test**

Post the identical document update twice. Assert the same channel event/idempotency key reaches application service and only the original outcome is sent as authoritative.

- [ ] **Step 4: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/transport/test_telegram_webhook.py -q`

Expected: FAIL because adapter does not exist.

- [ ] **Step 5: Implement update translation**

Map Telegram user ID to external identity without treating display name as authority. Derive idempotency from bot ID, update ID, file unique ID, learner, and active task. Download within limits to a generated temporary path, store through artifact port, and always clean temporary files.

- [ ] **Step 6: Implement response mapping**

Use reviewed Arabic messages from Member 1. Send receipt acknowledgement, deterministic result, AI/fallback coaching label, retry action, and skills command. Escape Telegram formatting and never include internal errors.

- [ ] **Step 7: Run and commit**

```bash
cd services/api
uv run pytest tests/transport/test_telegram_webhook.py -q
git add src/yom_awel/transport tests/transport
git commit -m "feat: add idempotent Telegram webhook"
```

### Task M5-6: Replace Fakes with Real Application Adapters

**Files:**
- Modify: `services/api/src/yom_awel/transport/dependencies.py`
- Create: `services/api/src/yom_awel/transport/settings.py`
- Create: `tests/integration/test_submission_evaluator.py`
- Create: `tests/integration/test_submission_feedback.py`
- Create: `tests/integration/test_submission_transaction.py`
- Create: `tests/integration/test_telegram_replay.py`

**Interfaces:**
- Consumes: approved Member 2–4 implementations.
- Produces: configured local/cloud composition root with unchanged HTTP contracts.

- [ ] **Step 1: Add settings validation tests**

Test local mode requires no cloud key, cloud mode validates Supabase server variables, missing Gemini key selects fallback, and no `NEXT_PUBLIC_` server secret exists.

- [ ] **Step 2: Integrate evaluator only**

Bind Member 4's registry while leaving memory persistence and feedback fake. Run contract, evaluator, transport, and evaluator integration tests.

- [ ] **Step 3: Commit evaluator integration**

```bash
git add services/api/src/yom_awel/transport/dependencies.py tests/integration/test_submission_evaluator.py
git commit -m "feat: integrate deterministic evaluation"
```

- [ ] **Step 4: Integrate feedback only**

Bind Member 3's resilient provider chain. Test generated and no-key fallback outcomes without contract drift.

- [ ] **Step 5: Commit feedback integration**

```bash
git add services/api/src/yom_awel/transport/dependencies.py tests/integration/test_submission_feedback.py
git commit -m "feat: integrate resilient feedback"
```

- [ ] **Step 6: Integrate persistence**

Bind SQLite/local adapters for local mode and Supabase adapters for cloud mode. Test atomic attempt/progress updates, duplicate request, rollback, ownership, and restart persistence.

- [ ] **Step 7: Commit persistence integration**

```bash
git add services/api/src/yom_awel/transport tests/integration
git commit -m "feat: integrate persistent learning workflow"
```

- [ ] **Step 8: Run complete integrated suite**

```bash
cd services/api
uv run pytest tests ../../../tests/integration -q
uv run mypy src
uv run ruff check .
```

Expected: all pass with cloud credentials absent.

### Task M5-7: Configure Zero-Cost Vercel Deployments and Previews

**Files:**
- Create: `vercel.json`
- Create: `.github/workflows/preview.yml`
- Create: `docs/operations/vercel-deployment.md`
- Create: `docs/operations/vercel-preview-checklist.md`
- Create: `tests/security/test_zero_cost_config.py`

**Interfaces:**
- Consumes: buildable web/API apps and Hobby plan constraints.
- Produces: separate preview/production projects, reproducible deployment, and no-paid-service guard.

- [ ] **Step 1: Write zero-cost configuration test**

Assert config does not request Pro-only memory/duration, paid analytics, paid marketplace integration, Vercel Services beta, custom paid domain, or organization-only Hobby-incompatible Git ownership.

- [ ] **Step 2: Write build/bundle checks**

Build API and report Python uncompressed bundle below 500 MB after excluding tests, fixtures, task private references, and submission assets. Build web with no server secrets in generated client chunks.

- [ ] **Step 3: Run checks and confirm failure**

Run: `python -m pytest tests/security/test_zero_cost_config.py -q`

Expected: FAIL because deployment configuration does not exist.

- [ ] **Step 4: Configure two Vercel project roots**

Document API root `services/api` and web root `apps/web`. Pin Python 3.12, Node 24, package manager, build commands, function inclusion/exclusion, regions, and a maximum duration within Hobby limits. Do not rely on durable `/tmp` content after invocation.

- [ ] **Step 5: Configure preview workflow**

Use pinned Vercel CLI. Build/test before deployment. Deploy API preview first, pass its immutable URL to the web preview, then run Playwright smoke tests. Store tokens/project IDs only in GitHub secrets.

- [ ] **Step 6: Document setup and rollback**

Explain personal repository connection, environment separation, Telegram webhook switching, preview promotion, production rollback, free-limit symptoms, and how to disable cloud mode and run locally.

- [ ] **Step 7: Run and commit**

```bash
python -m pytest tests/security/test_zero_cost_config.py -q
git add vercel.json .github/workflows/preview.yml docs/operations tests/security/test_zero_cost_config.py
git commit -m "ci: add zero-cost Vercel preview workflow"
```

### Task M5-8: Complete End-to-End and Accessibility Verification

**Files:**
- Create: `apps/web/tests/e2e/release-flow.spec.ts`
- Create: `apps/web/tests/e2e/accessibility.spec.ts`
- Create: `tests/e2e/test_telegram_release_flow.py`
- Create: `docs/quality/accessibility-report.md`
- Create: `docs/operations/release-smoke-test.md`

**Interfaces:**
- Consumes: integrated local and preview systems.
- Produces: release evidence for Member 1's claim audit.

- [ ] **Step 1: Write web release flow**

Against preview: onboard a fresh learner, download task, upload dirty fixture, verify deterministic failure and fallback label, upload clean fixture, verify pass, then verify skill evidence/profile.

- [ ] **Step 2: Write accessibility tests**

Test page language/direction, keyboard-only completion, focus after async result, labelled file input, live status, text pass/fail indicator, heading order, contrast audit, and LTR isolation for technical tokens.

- [ ] **Step 3: Write Telegram release flow**

Use recorded Telegram updates and mocked outbound API to verify start, task, dirty document, retry, clean document, skills, duplicate update, and fallback behavior.

- [ ] **Step 4: Run local end-to-end suite**

```bash
cd apps/web && npx playwright test
cd ../.. && python -m pytest tests/e2e -q
```

Expected: all pass in local fallback mode.

- [ ] **Step 5: Run preview smoke suite**

Run Playwright with the immutable preview URL in incognito-equivalent isolated context. Verify API health and redacted runtime logs.

- [ ] **Step 6: Document evidence and commit**

```bash
git add apps/web/tests/e2e tests/e2e docs/quality/accessibility-report.md docs/operations/release-smoke-test.md
git commit -m "test: verify complete learner experiences"
```

## Member 5 Completion Gate

- Web/API builds, lint, types, unit, integration, and browser tests pass.
- OpenAPI generation has no drift.
- Web and Telegram use the same real application services.
- Uploads are private, bounded, ownership-checked, and non-durable locally.
- Telegram replay is idempotent.
- Arabic RTL/accessibility report passes Member 1 review.
- Vercel configuration passes zero-cost and bundle checks.
- Immutable API and web preview URLs pass full smoke tests.
- Member 2 approves contract/auth/persistence integration.
- No paid Vercel or third-party feature is required.
