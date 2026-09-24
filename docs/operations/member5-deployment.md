# Member5 deployment and operations

PR #22 is scoped to local integration (#28), not cloud release. Cloud release
needs the complete member2 service factory, immutable artifact MIME metadata and
task assignment (#26), the approved member4 binding and real project credentials
(#27). Member3's merged deterministic Arabic feedback is integrated now; only
evaluation remains explicitly simulated. Vercel must never use local mode.

M5-7/M5-8 are pending: this file describes the required rollout, not an executed
preview/promotion pipeline. Successful local browser evidence is uploaded by CI
on both success and failure; it is the local equivalent allowed by the M5 plan
until Vercel is connected. No immutable API/web deployment URLs are available yet.

Use two personal, non-commercial Vercel Hobby projects with roots `apps/web` and
`services/api`. Recheck Hobby eligibility and current limits before release.
Python is pinned to 3.12.11, Node to 24.13.1, npm to 11.8.0; dependency lockfiles
are committed. The verified available CLI version is `vercel@59.26.0`.

## Preview sequence

1. Configure the API with `APP_ENV=cloud`, `CLOUD_SERVICES_FACTORY`, Supabase
   server credentials, and exact CORS origins. Apply member2's reviewed migrations
   and configure the private submissions bucket and anonymous Auth.
2. Configure only the three approved `NEXT_PUBLIC_` variables in the web project.
   Provider, service-role and Telegram secrets remain on the API server.
3. Deploy the API preview first and build the web against its immutable URL.
   Add the exact web preview origin to API CORS; keep production values separate.
4. Verify anonymous sign-in, refresh, upload ownership, fail/retry/pass, skills,
   webhook replay, and Gemini outage behavior using an isolated browser profile.
5. Record both immutable URLs, Git SHA, actual Python function bundle size,
   plan eligibility, and reviews. Promote the exact tested artifact.

The API config excludes tests, scripts, virtualenvs and caches. Source size is
not proof of function bundle size; inspect the actual Vercel build output.
Enable provider abuse limits before exposing anonymous Auth. The current local
process rate limiter is not a replacement for distributed cloud rate limiting.

## Telegram

After the HTTPS API is verified, configure Telegram's webhook to
`/api/v1/telegram/webhook` with a random secret matching
`TELEGRAM_WEBHOOK_SECRET` and message updates only. Keep the bot token server-side
and redact Bot API request URLs in HTTP logs. Disconnect the old webhook before
switching environments. No live Telegram messages were sent during development.

The adapter supports private `/start`, `/task`, `/skills`, `/status`, and CSV/XLSX
submissions up to 5 MB. Messages use plain text. Replayed document updates reuse
the original stored outcome and may resend that message, but create no new attempt.

## Recovery

- Supabase failure returns a generic retryable error; never switch to local DB.
- Gemini failure uses the canonical fallback provider and a visible UI label.
- Interrupted submissions retain their original idempotency key and artifact ID.
- Expired upload authorization requires new authorization. Never log signed URLs.
- Failed deployment: restore the previous verified API/web deployment and webhook
  destination. Database recovery remains governed by member2's migration procedure.
- Local restart: retain `.local/session.key` and the database together.

References: [Vercel Python](https://vercel.com/docs/functions/runtimes/python),
[Supabase anonymous Auth](https://supabase.com/docs/guides/auth/auth-anonymous),
[Supabase JWTs](https://supabase.com/docs/guides/auth/jwts).
