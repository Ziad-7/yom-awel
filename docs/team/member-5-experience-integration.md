# Member 5 — Web, Telegram, Integration, and Vercel

## Mission

Deliver a coherent, accessible learner experience across web and Telegram, integrate every module through the approved application interfaces, and operate the product on a zero-cost Vercel deployment without duplicating business logic.

Execution checklist: [Member 5 implementation plan](../superpowers/plans/2026-09-20-member-5-experience-integration.md)

## Owned paths

- `apps/web/**`
- `services/api/api/**`
- `services/api/src/yom_awel/transport/**`
- `tests/integration/**`
- `tests/e2e/**`
- `apps/web/vercel.json`
- `services/api/vercel.json`
- frontend and deployment lockfiles/configuration
- `.env.example` and operational runbooks

Shared ownership:

- generated API client and fixtures with Member 2;
- learner-visible copy with Member 1.

## Inputs

- user journeys, Arabic copy, and accessibility expectations from Member 1;
- use-case and OpenAPI contracts from Member 2;
- fake and real feedback providers from Member 3;
- fake and real evaluators plus upload limits from Member 4.

## Outputs

- Next.js learner experience;
- FastAPI routes and composition root;
- Telegram webhook adapter;
- signed Supabase upload/download flow;
- generated typed web API client;
- fakes for parallel frontend/integration development;
- Vercel Hobby projects and preview workflow;
- integration, browser, webhook replay, and deployment smoke tests;
- local startup and operational runbooks.

## Work packages

### 1. Parallel integration foundation

Immediately implement contract-compatible fakes for:

- learner/task state;
- evaluator pass and fail outcomes;
- feedback provider success and fallback;
- skills profile;
- retryable and non-retryable errors.

Build web and Telegram flows against these fakes while Members 2–4 implement real modules. Replace one fake at a time only after its contract suite passes.

### 2. Next.js web experience

Implement:

- Arabic RTL layout and responsive navigation;
- onboarding;
- workplace conversation/task presentation;
- private artifact download;
- signed direct upload;
- processing, success, failure, retry, and fallback states;
- attempt history and skills profile;
- accessible keyboard/focus/error behavior;
- clear indication of deterministic grade versus AI coaching.

The browser never receives Supabase service-role or Gemini credentials.

Use Supabase Auth anonymous sign-in on the Free plan so the demo needs no email, SMTP, OAuth, or paid identity provider. The browser sends a bearer access token, restores and refreshes the session, warns that logout/browser clearing makes the demo profile unrecoverable, and never uses a client learner ID as authority.

### 3. FastAPI transport

Expose versioned routes that map HTTP requests to application use cases. Validate size, content type, IDs, idempotency, authentication, and authorization at the boundary. Map stable domain errors to documented HTTP responses. Keep scoring and progression logic out of route handlers.

FastAPI verifies token issuer, audience, expiry, signature, and key ID against Supabase JWKS, then maps the verified subject to the learner external identity. CORS uses exact configured origins with credentials disabled. The browser may receive the project URL and publishable key, but never the service role or provider secrets.

### 4. Telegram adapter

Use a Vercel-hosted webhook with a verified webhook secret. Map Telegram user/update IDs into external identity and idempotency contracts. Support onboarding, current task, document submission, result, retry, and skills commands through the same use cases as web.

Telegram retries must return the original outcome without duplicate attempts. Local development may use polling, but production does not require a continuously running process.

### 5. Artifact flow

- Request signed upload authorization from FastAPI.
- Upload directly to a private Supabase bucket.
- Submit only the generated artifact ID and idempotency key to the application.
- Validate ownership and storage metadata before evaluation.
- Use short-lived signed downloads.
- Clean temporary function files and honor retention rules.

### 6. Vercel deployment

Configure two Hobby projects from the personal GitHub repository:

- web root: `apps/web`;
- API root: `services/api`.

Keep `vercel.json` inside each project root. Hobby is for the personal, non-commercial hackathon/demo only; revalidate eligibility at release and require a new hosting decision before commercial use.

Pin Node, Python, package manager, dependencies, and Vercel CLI versions. Exclude tests and fixtures from Python bundles. Configure preview/production environment variables separately. Do not enable Pro trials, paid marketplace services, or custom paid resources.

### 7. CI and previews

On pull requests:

- run formatting, linting, types, unit, contract, and focused integration tests;
- build both applications;
- deploy previews for user-facing changes;
- post preview URLs through the repository's approved integration;
- run browser smoke tests against preview;
- block promotion if free-tier, security, or contract gates fail.

### 8. Operational readiness

Document:

- local startup with no cloud dependencies;
- environment variables and which side may access them;
- Telegram webhook setup and removal;
- Vercel preview verification and rollback;
- Supabase/Gemini outage behavior;
- quota-exhaustion fallback;
- health check and redacted log inspection;
- recovery from a failed deployment.

## Acceptance criteria

- Web and Telegram invoke the same application services.
- No business scoring or progression rule exists in UI or transport code.
- The complete web journey works in Arabic RTL and with keyboard navigation.
- Telegram update replay creates one submission and attempt.
- Uploads are private, bounded to 5 MB, and referenced by generated IDs.
- All secrets remain server-side and absent from bundles/logs.
- Web anonymous sign-in, restore/refresh, logout warning, JWT verification, learner mapping, `is_anonymous` RLS, rate-limit, and CORS negative tests pass.
- The experience completes with Gemini unavailable.
- Every user-facing pull request has a verified preview.
- Both Vercel projects run within Hobby limits and require no paid feature.
- Local mode works with SQLite, local files, and deterministic feedback.
- Production promotion uses the exact verified preview artifact.

## Required tests and reviews

- Route validation and error-mapping tests.
- Generated-client contract compatibility.
- Integration tests replacing one fake at a time.
- Telegram webhook signature and replay tests.
- Browser tests for onboarding, fail, retry, pass, and profile.
- Arabic RTL, keyboard, focus, and screen-reader checks.
- Preview smoke test in an incognito browser.
- Missing-secret, Supabase-down, and Gemini-down tests.
- Python bundle-size and zero-cost configuration checks.

## Pull request responsibilities

Member 5 is required reviewer for:

- web, transport, Telegram, and integration changes;
- Vercel, CI, dependencies, runtime, and environment configuration;
- changes affecting cross-module composition;
- schema changes that alter transport or deployment behavior.

Member 5 requests affected lane-owner review whenever transport changes a consumed contract. Learner-facing changes require Member 1 approval.

## Handoffs

- To Member 1: stable preview URLs, screenshots, demo path, and verified limitations.
- To Member 2: transport requirements, auth context, idempotency observations, and contract-generation feedback.
- To Member 3: UI states for provider success/fallback and latency constraints.
- To Member 4: artifact metadata, runtime limits, and evaluation timing evidence.

## Out of scope

- Reimplementing domain rules in TypeScript or route handlers.
- Storing durable data on Vercel's local filesystem.
- Introducing a paid Vercel feature or third-party queue.
- Changing contracts without the documented approval process.
