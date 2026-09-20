# Member 3 — AI Personas and Pedagogical Feedback

## Mission

Provide useful, safe, culturally authentic coaching grounded in deterministic evidence, while ensuring the product remains functional when the free Gemini service is unavailable.

Execution checklist: [Member 3 implementation plan](../superpowers/plans/2026-09-20-member-3-ai-feedback.md)

## Owned paths

- `services/api/src/yom_awel/feedback/**`
- AI prompt and persona fixtures
- AI quality and provider-failure tests
- prompt/model configuration documentation

Shared ownership:

- learner-visible Arabic feedback with Member 1;
- `FeedbackResult` contract with Member 2.

## Inputs

- canonical `EvaluationResult` and `FeedbackResult` contracts;
- task title, business context, learning objectives, and safe hints;
- Member 1's Arabic tone and pedagogical rubric;
- provider configuration and timeout budget.

Inputs exclude raw learner files, PII, Telegram IDs, email addresses, storage paths, secrets, and unrestricted database records.

## Outputs

- persona specifications for Eng. Tarek, Hazem, and Mona;
- provider-neutral `FeedbackProvider` implementation;
- Gemini free-tier adapter;
- structured prompt builder;
- output parser and schema validator;
- deterministic Arabic fallback provider;
- prompt versions and evaluation dataset;
- tests for content grounding, injection, timeouts, quotas, and malformed responses.

## Work packages

### 1. Persona specification

For every persona, document:

- workplace role and authority;
- tone and vocabulary;
- allowed behaviors;
- prohibited behaviors;
- relationship to the learner;
- situations in which the persona speaks;
- examples and counterexamples.

Only personas wired into a verified user journey may be described as active product functionality.

### 2. Feedback schema

Return validated `FeedbackResult` containing:

- feedback text;
- language;
- persona ID;
- prompt version;
- provider/model metadata;
- fallback flag;
- duration.

Do not add authoritative pass/fail or score fields. The deterministic evaluation remains the source of truth.

### 3. Prompt construction

Build prompts from:

- trusted persona instructions;
- trusted task context;
- structured evaluator checks and errors;
- fixed output schema;
- optional learner note clearly delimited as untrusted data.

Instruct the model to explain the business consequence, give a targeted next step, avoid revealing reference solutions, and never override the grade.

### 4. Privacy and safety

- Remove or pseudonymize learner identity.
- Do not send raw artifacts or full rows.
- Cap error/check counts and text length.
- Escape and delimit untrusted text.
- Validate output length, language, structure, and prohibited content.
- Redact provider request/response logs.
- Document that Gemini free-tier data may be used by the provider to improve products.

### 5. Provider resilience

Use strict timeouts and bounded retry only for retryable failures. Handle:

- missing API key;
- quota and rate-limit errors;
- network timeout;
- provider outage;
- safety refusal;
- malformed or non-Arabic response;
- schema validation failure.

Every path returns a valid deterministic fallback response tied to evaluator output.

### 6. Feedback quality evaluation

Maintain fixtures covering pass, near-pass, multiple failures, ambiguous learner note, prompt injection, and provider failure. Score outputs against:

- grounding in evaluator facts;
- correctness of decision language;
- business relevance;
- actionable guidance;
- Egyptian Arabic quality;
- non-disclosure of solutions;
- safety and professionalism.

## Acceptance criteria

- Feedback never contradicts deterministic pass/fail or score.
- Provider input contains no learner PII or raw artifact content.
- Missing key, timeout, quota, refusal, or malformed response returns fallback.
- Fallback contains decision, business consequence, targeted guidance, and score explanation.
- Prompt and persona versions are recorded on every feedback result.
- Prompt injection fixtures cannot alter system behavior or request secrets.
- Eng. Tarek feedback meets Member 1's language rubric.
- Hazem and Mona remain roadmap-only until their flows are integrated and tested.
- Tests do not require live paid API calls.

## Required tests and reviews

- Unit tests for prompt construction with redaction.
- Parser/schema tests for valid and invalid provider output.
- Timeout, quota, missing-key, and refusal tests.
- Snapshot tests for deterministic fallback text.
- Prompt-injection adversarial tests.
- Quality fixture review with Member 1.
- Contract tests using Member 2's canonical fixtures.

## Pull request responsibilities

Member 3 is required reviewer for:

- persona definitions;
- prompts and provider configuration;
- feedback schema consumers;
- learner-facing AI behavior;
- AI privacy and failure-mode changes.

Member 3 requests Member 1 approval for learner-facing behavior and Member 2 approval for contract changes.

## Handoffs

- To Member 2: final provider/fallback behavior and errors.
- To Member 5: deterministic fake provider, latency states, and learner-safe failure messages.
- To Member 1: reviewed Arabic examples, limitations, and claim evidence.
- To Member 4: the exact evaluator fields needed for meaningful explanations.

## Out of scope

- Determining grades or progression.
- Persisting attempts directly.
- Sending raw learner artifacts to the model.
- Making paid models or a billing account mandatory.
