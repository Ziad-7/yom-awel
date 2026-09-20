# Gemini Free-Tier Operation

Gemini coaching is optional. Configure a free-tier API key only in the deployment secret store
and select the model through runtime configuration. Never commit a key or expose it to the web
client. The required product path must not enable billing or depend on paid quota.

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

