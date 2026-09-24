# Member5 experience and integration

## Scope and baseline

Work is isolated on `codex/member5-experience-integration`, based on main
`054fbc4`. The abandoned member3 work is preserved only on
`codex/member3-feedback-integration`, commit `8f42622`, and was not imported here.
No member2 domain, persistence, migration, or shared port files were changed.

Execution prompt: Build member5's Arabic Next.js experience, typed FastAPI
transport, authentication, bounded private uploads, webhook translation, and
contract/integration/browser tests around the canonical application services.
Use explicit local fakes until the owning teammates merge their real providers.
Keep scoring out of routes and UI. Fail closed for unconfigured cloud services.

## Run locally

From the repository root, Python 3.12 and Node 24:

```powershell
uv sync --project services/api --locked
npm ci --prefix apps/web
uv run --project services/api uvicorn yom_awel.transport.app:create_app --factory --host 127.0.0.1 --port 8000
# In another terminal:
npm run dev --prefix apps/web
```

Open http://127.0.0.1:3000. No credentials are needed. The first API start creates
`.local/session.key` and SQLite storage. Keep the key to restore browser sessions
across restarts; it is ignored by Git. Environment variables are read from the
process; API `.env` files are not loaded implicitly. Next.js reads
`apps/web/.env.local`. See `.env.example` for scope.

The local fixture evaluator accepts only the exact downloadable success fixture;
other uploads use the canonical failure fixture. This is clearly labelled in the
UI and Telegram, and is not a replacement for member4's grader. The feedback fake
uses member2's canonical fallback fixture, not the abandoned member3 code.
Artifacts are private SQLite blobs in local mode; clients never select disk paths.

## Verified journey

1. Start an anonymous local session and onboard with a name.
2. Download the demo task, upload the dirty fixture, inspect failed checks.
3. Download the explicitly labelled success fixture and resubmit.
4. Inspect accepted evaluation and skills; reload to restore the same learner.
5. Review attempt history; duplicate submission keys replay the original outcome.
6. Logout warns that this anonymous profile cannot be recovered.

The web uses generated `contracts/openapi.json` types. Regenerate via:

```powershell
uv run --project services/api python services/api/scripts/export_openapi.py
npm run api:generate --prefix apps/web
npm run api:check --prefix apps/web
```

Authenticated API routes include `/learners/onboard`, `/learners/me`,
`/tasks/current`, `/artifacts/upload-authorization`, `/artifacts/{id}/complete`,
`/submissions`, `/submissions/{id}`, `/attempts`, and `/skills` under `/api/v1`.
Outcome lookup also requires the original `Idempotency-Key`, because the existing
member2 lookup port is scoped by learner and key. Browser retries retain that key.
Uploads require bounded metadata, a signed short-lived authorization, ownership,
and a server-verified SHA-256. Cloud uploads go directly to the returned storage
URL; bearer tokens are sent only to our API, never storage.

## Teammate integration boundaries

`transport.dependencies.Services` accepts member2's `UnitOfWorkFactory`, member4's
`Evaluator`, member3's `FeedbackProvider`, and an async task-starter callback.
Web and Telegram share that instance and the same `ProcessSubmission` service.

Two upstream functions are not available on current main:

- A complete Supabase unit-of-work composition: member2 currently exports the
  submission RPC repository and artifact abstractions, not a full cloud factory.
- A public task-assignment application service. The local-only demo starter uses
  the existing domain `transition()` and optimistic versioned repository update.

Cloud startup therefore requires `CLOUD_SERVICES_FACTORY=package.module:function`,
a server-owned factory returning real `Services` with `simulated=False`. It must
provide approved cloud repositories, task assignment, real evaluator/feedback,
and private storage. This is an integration hook, not a claim that cloud is ready.
Member2/3/4 implementations remain owned by those teammates.

Supabase JWT verification uses HTTPS JWKS, `kid`, RS256/ES256 signatures, issuer,
audience, expiration, UUID subject and authenticated role. The browser supports
anonymous Supabase sign-in, session restore/refresh and explicit logout. Local
sessions cannot authenticate in cloud. Existing anonymous-user RLS needs live
verification with the complete cloud composition. Current process-local rate
limiting is a local safeguard; cloud needs provider/distributed abuse limits.

## Tests and review

```powershell
uv run --project services/api pytest -q
uv run --project services/api ruff check services/api
uv run --project services/api mypy --config-file services/api/pyproject.toml services/api/src/yom_awel
npm run lint --prefix apps/web
npm run typecheck --prefix apps/web
npm test --prefix apps/web
npm run build --prefix apps/web
npm run test:e2e --prefix apps/web
```

Browser tests start both servers automatically. Do not run them against production.
The reviewed sources for setup are Next.js App Router installation,
Supabase anonymous sign-in/JWT documentation, and Vercel Python runtime documentation.
Local screenshots are generated under `apps/web/test-results/`.
Member1 Arabic/accessibility review and member2 auth/contract review are still
required before release; automated checks do not substitute for those approvals.

## Local verification result

- Python: 265 passed, 13 existing Supabase-dependent tests skipped.
- New transport suite: 29 passed, including JWT negatives, upload integrity,
  ownership, malformed webhook rejection, webhook replay, active submission replay
  and restart persistence.
- Web: 3 unit tests and 2 complete Playwright journeys passed.
- Axe WCAG 2 A/AA scan passed on the authenticated desktop workspace after contrast fixes.
- Ruff lint/format, strict mypy, TypeScript, ESLint, OpenAPI type drift, dependency
  lock check, and the production Next.js build passed.
- npm production dependency audit reported zero vulnerabilities.
- Web responses set anti-framing, MIME-sniffing, referrer, and browser-permission
  security headers; the browser suite verifies them.

The in-app browser bridge was unavailable; the checked-in Playwright suite provided
the browser verification and screenshots. For a small system drive, install only
the full Chromium build (`npx playwright install --no-shell chromium`) and point
TEMP/TMP at a drive with space. No live Telegram, Supabase, Gemini, or Vercel calls
were used to claim release readiness. No changes were pushed.
