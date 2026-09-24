# PR #22 review repairs and explicit release boundaries

Baseline: rebased onto main `244a8a1` (Member3 and Member1 merged). Local acceptance
is issue [#28](https://github.com/Ziad-7/yom-awel/issues/28).

| Review finding | Change and evidence | Remaining gate |
| --- | --- | --- |
| Dependency/rebase conflict | Preserve google-genai, FastAPI, HTTPX, PyJWT, Uvicorn and asyncio_mode=auto; regenerate uv.lock; run full suites | Recheck against main on merge |
| Identical English feedback | Remove FixtureFeedback and its copied JSON; compose Member3 DeterministicFeedbackProvider; HTTP/Telegram tests and browser assertions verify four Arabic sections, decision/score, fallback label | Live Gemini remains optional release integration |
| Error category/retryability lost | Consume DomainError.details metadata; map persistence/evaluation/conflict/integrity statuses; emit bounded Retry-After for retryable errors; redact provider details; document ApplicationError in OpenAPI/client | Member2 contract review |
| MIME spoofing and unsafe bytes | Sign local MIME authorization; compare PUT Content-Type; verify bytes/hash and CSV/XLSX signatures, archive paths/macros/entities/expansion bounds before local storage; reuse inspection for Telegram | Immutable domain/Storage metadata and completion contract requested from Member2 in #26 |
| Anonymous JWT policy | Require literal boolean is_anonymous=true; test missing/false/string claims; add opt-in live JWKS/RLS/Storage gates with positive controls | Live project fixture/credentials and RLS remediation in #26; live tests unexecuted |
| Incomplete cloud composition | Integrate merged Member3 now; retain fail-closed cloud hook; explicitly scope PR to local scaffold | Real evaluator, full Supabase factory and public assignment in separate contract-gated commits under #26/#27 |
| No Vercel/evidence workflow | CI uploads successful and failed browser screenshots; local screenshot equivalent applies until connected | API-first immutable preview URL, preview smoke and exact-artifact promotion are M5-7/M5-8 in #27 |
| Reviews / issue traceability | Link #28 with exact task mapping; request Member2 contract/auth and Member1 Arabic/accessibility review | Approval belongs to the reviewers; no approval claimed |

## Verification commands

```text
uv sync --project services/api --locked
uv lock --check --project services/api
uv run --project services/api pytest -q -p no:cacheprovider
uv run --project services/api ruff check services/api
uv run --project services/api ruff format --check services/api
uv run --project services/api mypy --config-file services/api/pyproject.toml services/api/src/yom_awel
uv run --project services/api python services/api/scripts/export_openapi.py
npm run api:check --prefix apps/web
npm run lint --prefix apps/web
npm run typecheck --prefix apps/web
npm test --prefix apps/web
npm run build --prefix apps/web
npm run test:e2e --prefix apps/web
```

Python: 422 passed, 15 live/cloud skips; transport subset: 51 passed, 2 live skips.
Web: 3 unit tests and 2 full browser journeys including Arabic feedback and Axe.
Static/build/contract checks pass. GitHub Actions supplies immutable run/evidence
links for each pushed revision. Browser screenshots include desktop/mobile and
both failed/passed Arabic feedback states, retained for 14 days.

This evidence is local integration evidence. Live Supabase/Auth/Storage, Telegram
delivery, Vercel bundle size, preview deployment and promotion were not exercised.
No local test outcome is substituted for those release gates.
