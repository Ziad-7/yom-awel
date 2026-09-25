# Deploying the demo (Vercel + Supabase Postgres)

The hosted demo is two Vercel Hobby projects and one Supabase Postgres
database:

| Piece | Where | Root directory |
| --- | --- | --- |
| API (FastAPI) | Vercel project `yom-awel-api`, region `fra1` | `services/api` |
| Web (Next.js) | Vercel project `yom-awel-web`, region `fra1` | `apps/web` |
| Database | Supabase project in `eu-central-1` (Frankfurt) | schema `yom_awel` |

Supabase is used only as a managed Postgres, reached through the transaction
pooler with `DATABASE_URL`. The API issues its own learner sessions and stores
uploaded files as `bytea` in `yom_awel.artifacts` (5 MiB cap per file). The
demo does not use Supabase Auth, Storage, Row Level Security, the Data API or
the RPC migrations in `supabase/migrations`; do not apply those migrations.

`fra1` (Frankfurt) is the Vercel region nearest Supabase `eu-central-1`, so
every database round trip stays inside Frankfurt.

## 1. Create the database and the least-privilege role

1. Create a Supabase project in region **Central EU (Frankfurt),
   eu-central-1**. Keep the generated database password in your password
   manager; it belongs to the `postgres` administrator. Prefer the restricted
   role below; the temporary demo fallback is described after the SQL block.
2. Open **SQL Editor** and run the block below as `postgres`, replacing
   `<strong-password>` with a new random password (for example the output of
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`). Do not
   commit or paste the real password anywhere else.

```sql
-- yom_awel least-privilege role
CREATE ROLE yom_awel_app WITH LOGIN PASSWORD '<strong-password>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 20;
-- Lets the administrator create a schema owned by the new role (Postgres 16+).
GRANT yom_awel_app TO postgres;
CREATE SCHEMA yom_awel AUTHORIZATION yom_awel_app;
```

Supabase's `postgres` role is not an unrestricted superuser. The SQL above is
tested in the Postgres CI container; managed-role grants and pooler login must
also be tested on the actual project. If either fails, use the dashboard's
default `postgres.<project-ref>` transaction-pooler URI for this hackathon demo.
Record the use of the administrator role as a post-hackathon least-privilege fix.
Do not apply the unrelated migrations under `supabase/migrations`.

What this grants, and nothing more:

- `yom_awel_app` can log in and owns only the `yom_awel` schema. The API
  creates its tables there on first request, idempotently and under an
  advisory lock, so no migration step is needed.
- It is not a superuser, cannot create databases, roles or schemas, cannot
  bypass RLS, and has no grants on `public`, `auth`, `storage` or any other
  schema. Postgres 15+ no longer lets `PUBLIC` create objects in `public`.
- The Supabase `anon` and `authenticated` roles have no `USAGE` on
  `yom_awel`, so the Data API cannot reach it. Do not add `yom_awel` to
  **Settings > Data API > Exposed schemas**.

`services/api/tests/persistence/test_postgres.py` runs this exact block
against Postgres 16 and then runs the adapter as that role.

## 2. Build `DATABASE_URL` for the pooler

1. In the Supabase dashboard open **Connect > Connection string > Transaction
   pooler** and copy the URI. Its user is `postgres.<project-ref>`, its host
   `aws-0-eu-central-1.pooler.supabase.com` (the `aws-N` prefix can differ;
   keep what the dashboard shows) and its port `6543`.
2. Build `DATABASE_URL` from these parts, replacing only the user and the
   password:

   | Part | Value |
   | --- | --- |
   | scheme | `postgresql://` |
   | user | `yom_awel_app.<project-ref>` (the pooler routes on the `.<project-ref>` suffix) |
   | password | the `yom_awel_app` password, percent-encoded (encode every character outside `A-Z a-z 0-9 - _ . ~`) |
   | host and port | `aws-0-eu-central-1.pooler.supabase.com:6543` |
   | database and options | `/postgres?sslmode=require` |

   Join them as scheme, user, `:`, password, `@`, host and port, then
   database and options. Paste the result straight into Vercel (step 3);
   never into a file, chat or ticket.

Keep port `6543` (transaction mode). The adapter is built for it: one
connection and one transaction per unit of work, prepared statements disabled
(`prepare_threshold=None`), `search_path`, `timezone` and `statement_timeout`
set per transaction, and a 10 second connect timeout. `sslmode` is read from
the URL. The adapter never logs the URL and its errors never contain it.

## 3. Environment variables

Set these in **Vercel > Project > Settings > Environment Variables** for the
Production environment. Never commit values; `.env.example` lists names only.

API project (`services/api`):

| Variable | Required | Value and where to get it |
| --- | --- | --- |
| `APP_ENV` | yes | `cloud` |
| `DATABASE_URL` | yes | The pooler URL built in step 2. |
| `AUTH_SECRET` | yes | At least 32 characters: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Signs the `yom_session` cookie; rotating it signs everyone out. |
| `CORS_ORIGINS` | yes | The web origin, exactly, for example `https://yom-awel-web.vercel.app` (no trailing slash). |
| `GEMINI_API_KEY` | no | Google AI Studio > **Get API key**. Without it feedback uses the deterministic Tarek fallback. |
| `GEMINI_MODEL` | no | `gemini-3.5-flash-lite` (default). Its free tier is listed on Google's pricing page; verify account access and quota. |
| `FEEDBACK_MODE` | no | `auto` (Gemini when a key is set, otherwise fallback) or `fallback` (never call Gemini). |
| `RATE_LIMIT` | no | Positive per-IP requests per minute; defaults to `120`. The browser test server uses `1000` because its sequential learners share one loopback IP. |
| `TELEGRAM_BOT_TOKEN` | no | BotFather token. Not part of the demo; leave unset. |
| `TELEGRAM_WEBHOOK_SECRET` | no | Random string for the Telegram webhook header. Not part of the demo; leave unset. |

`LOCAL_DATABASE_PATH` and `LOCAL_SECRET_PATH` apply to local mode only; do not
set them on Vercel.

Web project (`apps/web`):

| Variable | Required | Value and where to get it |
| --- | --- | --- |
| `API_ORIGIN` | yes | The API production URL from step 4, for example `https://yom-awel-api.vercel.app`. Server-only: the Next.js rewrite proxies `/api/*` to it, so the browser only calls relative `/api/v1/...` URLs. Never use a `NEXT_PUBLIC_` variable for it. |

## 4. Create the two Vercel projects (Hobby)

Do the API first, because the web project needs its URL.

1. **Add New > Project**, import `Ziad-7/yom-awel`.
2. API project: name `yom-awel-api`, **Root Directory** `services/api`,
   framework preset **FastAPI** (from `services/api/vercel.json`). Keep
   **Include files outside the root directory in the Build Step** enabled:
   the API wheel build copies `../../task_packages` into the package.
   The API must be installed non-editably so the wheel's copy is present;
   step 5 checks that the task catalog actually loaded. Add the API variables
   from step 3, then **Deploy**.
3. Web project: name `yom-awel-web`, **Root Directory** `apps/web`,
   framework preset **Next.js**. Add `API_ORIGIN`, then **Deploy**.
4. Set `CORS_ORIGINS` on the API project to the web production URL and
   redeploy the API (**Deployments > ... > Redeploy**).
5. In both projects check **Settings > Functions > Function Region** shows
   **Frankfurt, Germany (fra1)**. `vercel.json` pins it; Hobby allows one
   region per project.

## 5. Verify the deployment

Replace the hosts with your production URLs.

Use the supplied small presenter files. The evaluator accepts up to 5 MiB
locally. Hosted task details and upload authorization cap files at 4,000,000
bytes, below [Vercel Functions' 4.5 MB request-body limit](https://vercel.com/docs/functions/limitations).
The web form reads the task's advertised limit before uploading.

For an isolated HTTPS preview, run the real API browser journeys against the
deployed web URL after setting the API and web preview pair:

```sh
HOSTED_WEB_URL=https://your-web-preview.vercel.app npm run test:hosted --prefix apps/web
```

This mode starts no local servers. It creates throwaway learners and artifacts,
so use a preview database rather than production data. The web preview's
`API_ORIGIN` must point to the exact API preview being tested.

1. Health, direct and through the web proxy:

   ```sh
   curl -fsS https://yom-awel-api.vercel.app/api/v1/health
   curl -fsS https://yom-awel-web.vercel.app/api/v1/health
   ```

2. Runtime: expect `"mode":"cloud"` and the feedback provider you configured.

   ```sh
   curl -fsS https://yom-awel-web.vercel.app/api/v1/runtime
   ```

3. The task catalog loaded (the task package reached the bundle). This
   creates one throwaway learner; every state-changing call needs the
   `X-Yom-Awel: 1` header:

   ```sh
   WEB=https://yom-awel-web.vercel.app
   JAR="$(mktemp)"
   curl -fsS -c "$JAR" -b "$JAR" -X POST -H 'X-Yom-Awel: 1' "$WEB/api/v1/auth/session"
   curl -fsS -c "$JAR" -b "$JAR" -X POST -H 'X-Yom-Awel: 1' \
     -H 'Content-Type: application/json' \
     -d '{"display_name":"Deploy check","preferred_language":"en"}' \
     "$WEB/api/v1/learners/onboard"
   curl -fsS -b "$JAR" "$WEB/api/v1/tasks" | grep -q '"task_id":"clean-sales"' \
     && echo "catalog ok"
   rm -f "$JAR"
   ```

4. One full submission, in a private browser window on the web URL: choose
   Arabic, onboard, start **clean-sales**, download the dirty CSV, upload it
   unchanged (expect a score below 75 and Tarek's feedback), then upload a
   cleaned file and confirm the per-check scores, feedback and progress
   update. Repeat once in English with the XLSX download.
5. Confirm the data landed in the dedicated schema (SQL Editor):

   ```sql
   SELECT
     (SELECT count(*) FROM yom_awel.learners) AS learners,
     (SELECT count(*) FROM yom_awel.artifacts) AS artifacts,
     (SELECT count(*) FROM yom_awel.attempts) AS attempts;
   ```

6. Confirm the app is not a superuser:
   `SELECT rolsuper FROM pg_roles WHERE rolname = 'yom_awel_app';` returns
   `false`.

## 6. Rollback

- **Bad code deploy:** in the affected Vercel project open **Deployments**,
  pick the last good production deployment and choose **Instant Rollback**
  (or **Promote to Production**). API and web roll back independently; roll
  back both if the change spanned the API contract.
- **Bad configuration:** fix the variable, then **Redeploy** the latest
  deployment; variables are read at cold start.
- **Database:** the adapter only ever runs `CREATE ... IF NOT EXISTS`, so an
  older deployment runs against the current schema unchanged. Supabase free
  projects have no point-in-time recovery; to reset the demo data, run as
  `postgres`: `DROP SCHEMA yom_awel CASCADE;` followed by
  `CREATE SCHEMA yom_awel AUTHORIZATION yom_awel_app;`. This deletes every
  learner, upload and attempt.
- **Leaked credential:** `ALTER ROLE yom_awel_app PASSWORD '<new-password>';`,
  update `DATABASE_URL` in Vercel and redeploy. Rotate `AUTH_SECRET` the same
  way.

## Retention

`.github/workflows/retention.yml` and
`services/api/scripts/purge_expired_artifacts.py` target the Supabase Storage
and REST design described in `data-retention.md`, which the demo does not use.
The workflow therefore runs only on manual dispatch and is not needed for the
hosted demo. In the Postgres design uploaded files live in
`yom_awel.artifacts`; the demo keeps them until the schema is dropped after
the event.
