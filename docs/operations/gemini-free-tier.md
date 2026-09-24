# Gemini Free-Tier Operation

Gemini coaching is optional. Configure a free-tier API key only in the deployment secret store
and select the model through runtime configuration. Never commit a key or expose it to the web
client. The required product path must not enable billing or depend on paid quota.
The adapter accepts only `gemini-3.5-flash-lite` (the default) or `gemini-3.5-flash`.
On 2026-09-24 the 2.5 models answered 404 "no longer available to new users" for a new key,
while both 3.5 models answered 200; `gemini-3.5-flash` also returned 503 "high demand" at times.
Free-tier eligibility of the 3.5 models was not verified: check the
[official pricing page](https://ai.google.dev/gemini-api/docs/pricing) before deployment.
When Gemini fails or is slow, the deterministic Tarek feedback is served instead.

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

`FeedbackConfig`, `GeminiAdapter`, and `ResilientFeedbackProvider` apply the same timeout
validation at construction: NaN, positive/negative infinity, zero, and negative values raise
`ValueError` with `timeout_seconds must be a finite positive number`. Finite positive values
above 10 seconds are capped at 10; smaller positive values are preserved. This is a configuration
error, not a provider failure: correct it before starting the application. Missing API credentials
remain a normal fallback path when the timeout configuration is valid (issue #24).

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
are retained. Check IDs, diagnostic codes and error codes use explicit finite allow-lists;
unknown values become constant placeholders, even when syntactically valid. New evaluator
codes require a reviewed allow-list addition before being forwarded.

Learner-visible model text must exactly match the local approved rendering for the evaluation,
apart from whitespace. The same renderer serves fallback, provider prompt and output validation.
Correct hidden check references cannot authorize invented consequences, advice, prefixes or
suffixes. Any deviation triggers fallback, including from an injected primary provider. This
intentionally disables free-form model coaching in v1: Gemini cannot rewrite the approved
copy, and the required path gains no dependency on its availability. Member 1 still reviews
the approved templates for tone, factual relevance and solution non-disclosure.

