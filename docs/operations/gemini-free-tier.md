# Gemini Free-Tier Operation

Gemini coaching is optional. Configure a free-tier API key only in the deployment secret store
and select the model through runtime configuration. Never commit a key or expose it to the web
client. The required product path must not enable billing or depend on paid quota.
The adapter accepts only `gemini-2.5-flash` or `gemini-2.5-flash-lite`, both listed with
free-tier text input/output on the [official pricing page](https://ai.google.dev/gemini-api/docs/pricing).
Recheck that listing before changing models or enabling the optional provider in deployment.

Only the bounded structured request produced by the feedback prompt builder may leave the
application boundary. It excludes learner identity, email, Telegram identifiers, raw artifacts,
filenames, object paths, signed URLs, and secrets. Learner notes are redacted, capped at 500
characters, and marked as untrusted data. Operators must disclose that data sent through the
Gemini free tier may be used by the provider to improve products.

Missing configuration, timeout, quota, network failure, safety refusal, malformed output,
non-Arabic output, or a contradiction with deterministic evaluation activates the local Arabic
fallback. These are degraded-mode events, not application-startup failures. Logs contain only a
correlation context, provider error code, duration, and fallback flag; prompt and response bodies
must never be logged.

The total provider budget is 10 seconds. At most one retry is allowed for a transient network or
quota error when its short retry delay fits inside that budget. Diagnose repeated fallback through
redacted metrics, verify the key and free quota, and keep fallback enabled while investigating.

## Composition handoff

Member 5 can call `build_feedback_provider(FeedbackConfig(...), task_context_resolver=resolver,
fake_provider=fake)` from `yom_awel.feedback.config`. Modes are `fallback` (default), `gemini`,
and `fake` (explicit injection required). Gemini with no key returns fallback without resolving
task context or constructing an SDK client. Configuration is injected; this lane does not edit
Member 5's environment loader or composition root. The key is excluded from configuration repr.

The SDK requests the parser's JSON schema; the prompt specifies its exact language, headings,
decision prefix and score format. The local parser remains authoritative even when the provider
claims schema compliance. Retry requires an explicit finite, nonnegative network/quota delay
that fits the remaining budget. SDK failures without a trusted delay fall back immediately.

Privacy limitation: pattern redaction is defense in depth, not a general PII classifier. Callers
must not put learner names, arbitrary workbook rows, or secrets in optional notes or trusted task
instructions. Omit the optional note when that cannot be guaranteed. Arbitrary evaluator detail
and error text is never forwarded; only exact approved canonical detail text and mapped guidance
are retained. No automated validator guarantees the semantic correctness of arbitrary model prose;
release examples still require Member 1's human rubric review.

