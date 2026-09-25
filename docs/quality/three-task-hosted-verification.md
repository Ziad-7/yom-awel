# Three-task hosted verification

Release candidate source: `a957768462d628ee4728a38bb44ce99b45401ac0`
([PR #42](https://github.com/Ziad-7/yom-awel/pull/42)). API:
<https://yom-awel-api.vercel.app>. Web: <https://yom-awel-web.vercel.app>.
Both Vercel production builds and the GitHub quality, Postgres, web/contract, and
secret-scan checks passed on 2026-09-25. The protected preview builds succeeded,
but their runtime was not accessible to this Codex Vercel connection; the public
production deployment was tested directly instead.

## Automated evidence

| Gate | Result |
| --- | --- |
| Python API | 900 passed, 34 live-service tests skipped |
| Product/release quality tests | 39 passed |
| Web unit/type/lint/build and generated API contract | 19 unit tests passed; all checks passed |
| Local Playwright | 14 passed, including Arabic RTL/mobile/Axe and three-task history |
| Hosted Playwright | 8 passed against the production web/API, including clean-sales CSV/XLSX and both new tasks |
| Hosted rejection probes | Unsafe SQL: 0/100, rejected with `sql_query_rejected`. Email denying refund and response: 75/100, `passed=false`. |
| Hosted feedback probes | Valid SQL: 100/100 with deterministic fallback. Valid English email: 100/100 with Gemini. |

Direct production health returned `{"status":"ok"}` and runtime returned
`{"mode":"cloud","feedback_provider":"gemini"}`. Hosted browser tests created
throwaway anonymous learners and confirmed submission, history, language, and
progress through the same-origin web proxy. Local browser tests ran with
`FEEDBACK_MODE=fallback`, so feedback remained available without Gemini.

## Release decision and remaining boundaries

- The sole active owner confirmed non-commercial Vercel Hobby use and explicitly
  approved release in place of the inactive member sign-offs on 2026-09-25.
  The five historical member approvals remain unrecorded; they are not presented
  as teammate approvals. The code adds no paid dependency.
- Telegram is outside the web demo release; no bot token or live webhook was
  configured or tested. The hosted Postgres demo keeps uploaded artifacts until
  the dedicated `yom_awel` schema is removed after the event.
- The 34 skipped tests require an explicitly configured live-service test
  environment; the eight hosted journeys provide end-to-end evidence for the
  deployed application, but do not exercise every skipped negative case.

The application is playable on the production URLs. The release record now has
an explicit `go` decision from the sole active owner for the verified web app.
