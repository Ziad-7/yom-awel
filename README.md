# Yom Awel (يوم أول)

Yom Awel ("first day") is an Arabic-first workplace simulation. A learner joins a simulated
Egyptian company, gets a real assignment from their supervisor Tarek, submits a real file, and
receives a deterministic grade plus coaching in Egyptian Arabic or English.

## Demo flow

1. Pick **clean-sales**, **sql-report**, or **client-email**, in Arabic or English.
2. Download the task source file and read the bilingual brief and hints.
3. Submit a cleaned CSV/XLSX, a read-only SQL query, or a customer email in the task editor or as a file.
4. See four deterministic checks, bilingual feedback from Tarek, and a pass or retry result.
5. Switch tasks and revisit saved attempts and skills progress.

The presenter kit in [`demo/`](demo/README.md) has ready-made uploads for each outcome (100 in CSV
and XLSX, 75 retry, 50 retry, rejected), each graded by the real evaluator in a test.

## Architecture in five lines

- `apps/web`: Next.js web app; the browser only calls relative `/api/v1` URLs, proxied to the API.
- `services/api`: FastAPI transport over framework-free domain and application layers.
- `services/api/src/yom_awel/evaluation`: versioned sales-cleaning, SQL-report, and client-email evaluators.
- `services/api/src/yom_awel/feedback`: the Tarek persona, a Gemini adapter and a deterministic fallback.
- Persistence: SQLite and local files in local mode; hosted Postgres and private storage in cloud mode.

## How scoring works

The task package [`task_packages/clean-sales/1`](task_packages/clean-sales/1/task.json) defines
four checks worth 25 points each:

| Check | Critical | Passes when |
|---|---|---|
| `unique_orders` | yes | no duplicate or blank `order_id` |
| `standard_dates` | no | every `order_date` is `YYYY-MM-DD` |
| `valid_numeric_values` | no | positive quantity and price, `revenue = quantity * unit_price` (±0.01) |
| `complete_customer_records` | no | a valid email, or `missing_email_reason = unavailable` |

**Pass rule:** score >= 75 **and** `unique_orders` passed. A file with only the duplicates left
scores 75 and is still a retry. Files that cannot be graded (wrong type, too large, missing or
duplicate columns, fewer than 40 rows, macros, several sheets) are rejected with a coded,
bilingual reason. CSV and XLSX are read into the same table, so the format never changes the grade.
The brief and hints are pinned by SHA-256 in `task.json`.

[`sql-report`](task_packages/sql-report/1/task.json) grades a bounded, read-only `SELECT`
against the published sales file and a modified validation dataset. Its four checks cover
column names, paid regions, counts, and revenue. [`client-email`](task_packages/client-email/1/task.json)
grades the recipient and subject, case facts, refund and response commitments, and professional
closing. Both have a 75-point threshold and mandatory checks. The email rubric is a deterministic
exercise in stated facts and commitments, not a human-quality writing assessment.

## How feedback works

After grading, Tarek explains the result in the learner's language. When `GEMINI_API_KEY` is set,
the Gemini adapter writes the explanation and the output is validated against the evaluation
before it is shown. On a missing key, timeout, error, or invalid output, the deterministic
fallback templates are used instead. `FEEDBACK_MODE=fallback` forces the fallback. Feedback never
changes the score or the pass decision.

## Security posture

- No secret is committed. `detect-secrets` runs in pre-commit and `gitleaks` scans full history
  in CI. `.env.example` holds names with empty values only.
- Secrets are read from environment variables at runtime, only by the API. The web app has no
  secrets and no `NEXT_PUBLIC_` credentials.
- Uploads are untrusted: size and signature are checked before parsing, XLSX expansion is
  bounded, and macros, external links and extra sheets are rejected (tested in
  `services/api/tests/evaluation/test_artifact_validation.py`).
- API contract (verification pending with the API lane): anonymous sessions use an HttpOnly,
  SameSite=Lax cookie (Secure in cloud mode); state-changing requests require the
  `X-Yom-Awel: 1` header; CORS is limited to the web origin; SQL is parameterized; error
  responses carry codes, never stack traces.

## Quickstart (local, no secrets)

Requirements: [uv](https://docs.astral.sh/uv/), Python 3.12, Node.js with npm.

```bash
demo/run_local.sh
```

It starts the API (`APP_ENV=local`) on port 8000 and the web app on port 3000 with the
server-only `API_ORIGIN=http://127.0.0.1:8000` for its `/api` rewrite, waits for the health
checks (API, web, and the API through the web proxy), and prints the URL. To use Gemini, put `GEMINI_API_KEY=...` in a git-ignored
`.env` at the repository root; without it, feedback uses the deterministic fallback.
See [`.env.example`](.env.example) for every variable.

## Quality gate

```bash
cd services/api && uv lock --check && cd ../..
uv run --project services/api pre-commit run --all-files   # secrets, format, lint, strict mypy, pytest
uv run --project services/api python services/api/scripts/export_schemas.py && git diff --exit-code
```

## What is verified

Every public claim is tracked in the
[claim matrix](docs/product/evidence/claim-matrix.yaml) with the test or file that backs it;
claims not yet verified end to end are marked `pending` with the reason. The
[demo runbook](docs/operations/demo-runbook.md) lists known limitations and the fallback plan.

## Documentation

- [Presenter kit](demo/README.md) and [live demo runbook](docs/operations/demo-runbook.md)
- [Platform design](docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md) and
  [architecture guide](docs/architecture/README.md)
- [Scoring policy](docs/product/learning/scoring-policy.md) and
  [evaluator v1 report](docs/quality/evaluator-v1-report.md)
- [Evidence policy](docs/product/evidence/evidence-policy.md) and
  [release sign-off](docs/product/release/release-signoff.yaml)
- [Competition submission](submission/application.md)
- [Team guide](docs/team/README.md) and [collaboration protocol](docs/team/collaboration-protocol.md)
