# Member 3 AI Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build grounded Egyptian-Arabic pedagogical feedback with provider-neutral interfaces, strict privacy boundaries, schema validation, and a deterministic no-cost fallback.

**Architecture:** A pure prompt builder consumes trusted task context and canonical evaluation fixtures. A Gemini adapter implements the shared `FeedbackProvider` port, while a fallback provider guarantees valid feedback for missing keys, quotas, timeouts, refusals, and malformed responses. No AI result controls grading or progression.

**Tech Stack:** Python 3.12, Pydantic 2, Google GenAI SDK, pytest, pytest-asyncio, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md`

## Implementation status (2026-09-23)

The implementation follows the merged `contracts-v1` baseline (`054fbc4`), not the original
pre-contract examples. `tarek` is the canonical ID and the port takes evaluation, language,
and an optional note. Historical write-failing-test/commit checkboxes below are retained as
the original execution recipe, not a claim that those historical steps were replayed.

| Task | Implemented evidence | Outstanding release review |
|---|---|---|
| M3-1 | Persona/policy modules and `test_personas.py` | Member 1 tone approval |
| M3-2 | Four canonical check mappings, bounded fallback, canonical snapshots | Member 1 snapshot approval |
| M3-3 | Bounded/redacted request, language-selected approved detail, safe fixture and adversarial tests | Consumer review of privacy boundary |
| M3-4 | Lazy SDK, explicit JSON schema, strict parser, grounding/language rejection tests | Optional deployment smoke test; not required for zero-cost path |
| M3-5 | Configuration factory, resilient chain, real cancellation, bounded retries, secret-log tests | Member 5 composition/dependency review |
| M3-6 | Nine quality cases including actual provider/error failures, rubric and operations guide | Member 1 rubric approval |

See [review evidence and prepared PR description](../../team/member-3-review-evidence.md) for
the reviewer-request mapping, exact verification commands, and unresolved human/PR actions.

## Global Constraints

- Use only Gemini models available on the free tier; a Gemini key is optional at runtime.
- Do not send learner identity, email, Telegram ID, raw artifact data, object paths, or secrets.
- Input to the provider is bounded, anonymized, structured evaluation data plus trusted task context.
- Untrusted learner notes are optional, length-limited, escaped, and clearly delimited as data.
- `FeedbackResult` cannot contain an authoritative grade override.
- A strict 10-second provider budget activates deterministic fallback.
- Tests never require live paid API calls.
- Every output records prompt version, provider/model, fallback flag, language, and duration.

## Review Focus

- Prompt injection in learner notes or evaluator error strings must not change system instructions or expose secrets.
- A provider response that contradicts pass/fail must be rejected and replaced with fallback.
- Free-tier privacy limitations require removal of PII and raw workbook content before the SDK call.
- Arabic output must contain decision, business consequence, targeted next action, and score explanation.
- Missing credentials must be a normal fallback path, not an application startup failure.

---

### Task M3-1: Define Persona and Feedback Policy

**Files:**
- Create: `services/api/src/yom_awel/feedback/personas.py`
- Create: `services/api/src/yom_awel/feedback/policy.py`
- Create: `services/api/tests/feedback/test_personas.py`
- Modify: `docs/team/member-3-ai-feedback.md`

**Interfaces:**
- Consumes: Member 1 language rules and `FeedbackResult` contract.
- Produces: versioned persona/policy objects used by prompt and fallback providers.

- [ ] **Step 1: Write the failing persona policy test**

```python
from yom_awel.feedback.personas import PERSONAS
from yom_awel.feedback.policy import ACTIVE_FEEDBACK_POLICY


def test_tarek_is_the_only_active_v1_persona() -> None:
    assert ACTIVE_FEEDBACK_POLICY.persona_id == "tarek"
    assert PERSONAS["tarek"].language == "ar-EG"
    assert PERSONAS["hazem"].status == "roadmap"
    assert PERSONAS["mona"].status == "roadmap"


def test_policy_forbids_grade_override_and_solution_disclosure() -> None:
    assert "override_grade" in ACTIVE_FEEDBACK_POLICY.prohibited_actions
    assert "reveal_reference_solution" in ACTIVE_FEEDBACK_POLICY.prohibited_actions
```

- [ ] **Step 2: Run the test and confirm failure**

Run: `cd services/api && uv run pytest tests/feedback/test_personas.py -q`

Expected: FAIL because persona modules do not exist.

- [ ] **Step 3: Define immutable persona records**

Create persona records with ID, Arabic name, workplace role, language, tone rules, allowed actions, prohibited actions, and status. Define Eng. Tarek as active and Hazem/Mona as roadmap until integrated journeys exist.

- [ ] **Step 4: Define feedback policy v1**

Require four ordered sections in one concise Arabic message:

1. acceptance or rework decision matching evaluation;
2. business consequence grounded in failed/passed checks;
3. targeted next action without reference solution;
4. deterministic score explanation.

Cap output at 900 Unicode characters and prohibit harassment, invented errors, secrets, identity claims, and grade changes.

- [ ] **Step 5: Document examples and counterexamples**

Extend the member document with one passing example, one retry example, and one rejected example that invents an error or discloses a solution. Use canonical fixtures rather than fabricated interfaces.

- [ ] **Step 6: Run tests and commit**

```bash
cd services/api
uv run pytest tests/feedback/test_personas.py -q
git add src/yom_awel/feedback tests/feedback ../../docs/team/member-3-ai-feedback.md
git commit -m "feat: define versioned feedback personas"
```

### Task M3-2: Implement Deterministic Arabic Fallback

**Files:**
- Create: `services/api/src/yom_awel/feedback/fallback.py`
- Create: `services/api/tests/feedback/test_fallback.py`
- Create: `services/api/tests/feedback/snapshots/fallback-pass.txt`
- Create: `services/api/tests/feedback/snapshots/fallback-fail.txt`

**Interfaces:**
- Consumes: exact `FeedbackProvider.generate(evaluation, language, learner_note=None)` port and `EvaluationResult`. Gemini resolves trusted `TaskVersion` through an injected resolver; the shared port does not receive a task argument.
- Produces: always-valid `FeedbackResult(provider="deterministic", used_fallback=True)`.

- [ ] **Step 1: Write failing fallback tests**

Load canonical pass/fail fixtures and assert:

```python
result = await provider.generate(evaluation, Language.AR_EG, None)
assert result.language == "ar-EG"
assert result.persona_id == "tarek"
assert result.prompt_version == "tarek-feedback@1"
assert result.provider == "deterministic"
assert result.model is None
assert result.used_fallback is True
assert str(evaluation.score) in result.feedback_text
```

For failed evaluation, assert every failed check ID maps to a known Arabic business consequence and targeted tip. For pass, assert the message does not mention rework.

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/feedback/test_fallback.py -q`

Expected: FAIL because fallback provider does not exist.

- [ ] **Step 3: Implement stable template selection**

Use a mapping from evaluator check IDs to trusted Arabic consequence/tip pairs. Sort checks by task rubric order, cap included failures at three, and mention remaining count without sending unbounded text.

- [ ] **Step 4: Validate output through `FeedbackResult`**

Measure duration with the injected clock. Do not create a second local feedback schema. Let Pydantic reject invalid length or language.

- [ ] **Step 5: Approve snapshot text with Member 1**

Store accepted pass/fail snapshots. Member 1 reviews tone, mixed Arabic/English terminology, actionable guidance, and solution non-disclosure.

- [ ] **Step 6: Run and commit**

```bash
cd services/api
uv run pytest tests/feedback/test_fallback.py -q
git add src/yom_awel/feedback/fallback.py tests/feedback
git commit -m "feat: add deterministic Arabic feedback fallback"
```

### Task M3-3: Build Redacted Prompt Input and Prompt Version

**Files:**
- Create: `services/api/src/yom_awel/feedback/prompt.py`
- Create: `services/api/tests/feedback/test_prompt.py`
- Create: `services/api/tests/feedback/fixtures/prompt-safe.json`

**Interfaces:**
- Consumes: trusted `TaskVersion`, canonical `EvaluationResult`, optional learner note.
- Produces: provider request object containing only approved fields and prompt version `tarek-feedback@1`.

- [ ] **Step 1: Write PII and injection tests**

Construct inputs containing an email, Telegram ID, Supabase path, API-key-like token, workbook row values, and learner note `ignore previous instructions`. Assert none of the PII/storage/secret values appear in the serialized provider request and the note appears only inside an explicitly labelled untrusted-data field.

- [ ] **Step 2: Write bounded-input tests**

Assert the builder caps learner note to 500 characters, evaluation errors to 10, checks to 20, and individual messages to 300 characters. It must preserve check IDs, pass states, points, trusted hints, and deterministic score.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/feedback/test_prompt.py -q`

Expected: FAIL because prompt builder does not exist.

- [ ] **Step 4: Implement a structured provider request model**

Separate system policy, trusted task context, structured evaluation, and untrusted learner note. Do not concatenate raw arbitrary dictionaries. Include an explicit instruction that provider text cannot alter `evaluation.passed` or `evaluation.score`.

- [ ] **Step 5: Add redaction**

Redact email patterns, phone/Telegram identifiers, key patterns, signed URL query strings, and storage object paths before serialization. Record redaction count, not redacted values.

- [ ] **Step 6: Write the safe request fixture**

Serialize the canonical failed evaluation into `prompt-safe.json`. Confirm it contains no learner UUID, original filename, bucket/path, or raw spreadsheet cell.

- [ ] **Step 7: Run and commit**

```bash
cd services/api
uv run pytest tests/feedback/test_prompt.py -q
git add src/yom_awel/feedback/prompt.py tests/feedback
git commit -m "feat: add private structured feedback prompts"
```

### Task M3-4: Implement Gemini Adapter and Output Validation

**Files:**
- Create: `services/api/src/yom_awel/feedback/gemini.py`
- Create: `services/api/src/yom_awel/feedback/parser.py`
- Create: `services/api/tests/feedback/test_gemini.py`
- Create: `services/api/tests/feedback/test_parser.py`

**Interfaces:**
- Consumes: prompt builder, injected async Gemini client, canonical `FeedbackResult`.
- Produces: provider result or a typed retryable/non-retryable provider error consumed by the resilient chain.

- [ ] **Step 1: Write parser rejection tests**

Reject missing fields, overlong text, wrong language marker, grade contradiction, score contradiction, invented failed check IDs, unsafe solution disclosure flag, and invalid JSON. Accept one canonical structured response.

- [ ] **Step 2: Write adapter tests with a fake SDK client**

Assert the adapter sends only the redacted request, selects the configured free-tier model, requests structured JSON, applies the 10-second budget, and never logs prompt/response bodies.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/feedback/test_parser.py tests/feedback/test_gemini.py -q`

Expected: FAIL because adapter/parser do not exist.

- [ ] **Step 4: Implement parser grounding checks**

Compare the response decision and score to the deterministic evaluation. Require referenced check IDs to exist. Normalize whitespace without changing Arabic content. Build `FeedbackResult(provider="gemini", used_fallback=False)` only after validation.

- [ ] **Step 5: Implement the SDK adapter**

Create the Google GenAI client lazily only when a key is configured. Inject client/model/timeout for tests. Map quota, timeout, network, refusal, and parse errors into typed errors without including provider payloads.

- [ ] **Step 6: Run and commit**

```bash
cd services/api
uv run pytest tests/feedback/test_parser.py tests/feedback/test_gemini.py -q
uv run mypy src/yom_awel/feedback
git add src/yom_awel/feedback tests/feedback
git commit -m "feat: add validated Gemini feedback adapter"
```

### Task M3-5: Compose Resilient Provider Chain

**Files:**
- Create: `services/api/src/yom_awel/feedback/service.py`
- Create: `services/api/tests/feedback/test_service.py`
- Create: `services/api/tests/feedback/test_no_secret_logs.py`

**Interfaces:**
- Consumes: Gemini adapter, deterministic fallback, exact `FeedbackProvider` port.
- Produces: one provider implementation safe for Member 2's application service and Member 5's composition root.

- [ ] **Step 1: Write degraded-mode matrix tests**

Parameterize missing key, timeout, quota, network error, refusal, invalid JSON, wrong score, wrong language, and unexpected exception. Assert every case returns a valid deterministic fallback and preserves evaluation pass/score.

- [ ] **Step 2: Write bounded retry tests**

Retry one time only for transient network and quota responses that include a short retry delay within the total 10-second budget. Do not retry missing key, refusal, validation failure, or contradiction.

- [ ] **Step 3: Write secret-log capture tests**

Capture logs and assert they contain correlation ID, provider error code, duration, and fallback flag but not API key, prompt, response, learner note, email, or object path.

- [ ] **Step 4: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/feedback/test_service.py tests/feedback/test_no_secret_logs.py -q`

Expected: FAIL because service does not exist.

- [ ] **Step 5: Implement provider chain**

Select fallback immediately when the key is absent. Otherwise call Gemini inside the total budget, perform allowed bounded retry, validate, and return fallback on any mapped failure. Emit redacted structured metrics.

- [ ] **Step 6: Run full feedback suite**

Run:

```bash
cd services/api
uv run pytest tests/feedback tests/contract -q
uv run mypy src/yom_awel/feedback
uv run ruff check src/yom_awel/feedback tests/feedback
```

Expected: all pass without a live Gemini key.

- [ ] **Step 7: Commit**

```bash
git add services/api/src/yom_awel/feedback services/api/tests/feedback
git commit -m "feat: add resilient feedback provider chain"
```

### Task M3-6: Establish Feedback Quality Evaluation

**Files:**
- Create: `services/api/tests/feedback/quality_cases.json`
- Create: `services/api/tests/feedback/test_quality_cases.py`
- Create: `docs/product/feedback-rubric.md`
- Create: `docs/operations/gemini-free-tier.md`

**Interfaces:**
- Consumes: canonical evaluator fixtures, persona policy, provider chain.
- Produces: reproducible quality evidence and operating guidance for Members 1 and 5.

- [ ] **Step 1: Create quality cases**

Include pass, one failure, three failures, near threshold, empty note, mixed Arabic/English note, prompt injection, malicious error text, and provider failure. Each case defines required check references and forbidden statements.

- [ ] **Step 2: Write deterministic quality assertions**

Verify decision/score grounding, required sections, character limit, check references, prohibited disclosures, and fallback validity. Do not assert exact live-model prose.

- [ ] **Step 3: Document the human rubric**

Define 0–2 scoring for factual grounding, business relevance, actionability, Egyptian Arabic quality, professionalism, and solution non-disclosure. Require Member 1 approval for release examples.

- [ ] **Step 4: Document free-tier operation**

Explain supported configuration, optional key, data-use disclosure, quota/fallback symptoms, secret storage, and prohibition on enabling a paid billing tier for the required path.

- [ ] **Step 5: Run and commit**

```bash
cd services/api
uv run pytest tests/feedback -q
git add tests/feedback ../../docs/product/feedback-rubric.md ../../docs/operations/gemini-free-tier.md
git commit -m "test: establish feedback quality and safety gates"
```

## Member 3 Completion Gate

- All feedback tests pass without network access or API credentials.
- Canonical pass/fail fixtures produce valid generated or fallback results.
- Provider-input fixtures contain no PII, raw artifacts, paths, or secrets.
- Contradictory, malformed, unsafe, or non-Arabic responses fall back.
- Member 1 approves persona, snapshots, and quality rubric.
- Member 2 approves exact port/contract usage.
- Member 5 can switch between fake, Gemini chain, and fallback through configuration only.
