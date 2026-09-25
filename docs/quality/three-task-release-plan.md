# Three-task release plan

The release is ready for submission only when `clean-sales`, `sql-report`, and
`client-email` each work in Arabic and English on the deployed web app. The
existing clean-sales scoring and saved attempts must remain unchanged.

1. **Task contracts and data.** Publish versioned, hash-pinned SQL and email
   task packages with source files, briefs, hints, and four 25-point checks.
   Extend artifact validation to accept bounded UTF-8 `.sql` and `.txt`
   submissions while keeping CSV/XLSX spreadsheet protections. Route each
   task to its exact deterministic evaluator version.
2. **Application and experience.** Let a learner start and switch among the
   three tasks, preserve per-task completion and attempt history, and show
   all three as playable cards. Provide on-page editors for SQL and email,
   retain file upload, display task-specific instructions and feedback, and
   support keyboard use, Arabic RTL, and narrow screens.
3. **Verification.** Run evaluator safety and rubric tests, transport and
   persistence tests, OpenAPI drift checks, strict Python lint/type checks,
   web unit/type/lint/build checks, and real-browser journeys. Test failure,
   retry, pass, reload, and cross-task history. An independent agent reviews
   the integrated diff and repeats adversarial checks; fix actionable issues.
4. **Release.** Review the complete diff and generated contracts, deploy API
   and web previews, test the hosted three-task journeys and Gemini/fallback
   behavior, then merge and verify production. Record source SHA, deployment
   URLs, evidence, and remaining scope in release sign-off. Do not mark
   unverified integrations as complete.

The SQL evaluator executes only bounded read-only queries against an isolated
in-memory dataset. The email evaluator uses transparent, deterministic checks;
its score is not a claim of human-quality writing assessment. Telegram is a
separate integration gate if it is included in the submission scope.
