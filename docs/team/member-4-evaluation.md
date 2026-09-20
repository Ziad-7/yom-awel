# Member 4 — Deterministic Evaluation and Task Data

## Mission

Make grading objective, secure, versioned, explainable, and reproducible so learner progression never depends on an LLM judgment.

Execution checklist: [Member 4 implementation plan](../superpowers/plans/2026-09-20-member-4-evaluation.md)

## Owned paths

- `services/api/src/yom_awel/evaluation/**`
- `task_packages/**/data/**`
- evaluator fixtures and golden outputs
- evaluator unit, security, and performance tests

Shared ownership:

- task instructions and pedagogical intent with Member 1;
- evaluator result contract with Member 2.

## Inputs

- measurable objectives and allowed transformations from Member 1;
- `TaskVersion`, artifact, and `EvaluationResult` contracts from Member 2;
- 5 MB artifact limit and Vercel runtime constraints from Member 5.

## Outputs

- reproducible task package format;
- deterministic dataset generator with fixed seed;
- learner-facing dirty artifact;
- private clean reference and expected checks;
- spreadsheet evaluator v1;
- later isolated SQL and communication evaluators through the same port;
- structured evaluation errors and summaries;
- adversarial/security fixtures;
- evaluator benchmark report.

## Work packages

### 1. Task package contract

Each immutable task version contains:

- task and version IDs;
- content hash;
- learner instructions;
- input artifact schema;
- allowed file types and limits;
- evaluator ID/version;
- exact checks and weights;
- pass threshold;
- allowed cleaning policy;
- skill evidence mapping;
- hints safe to reveal after failure;
- dataset seed and generator version.

### 2. Dataset generation

Generate deterministic dirty and clean fixtures from code. Record planted defects in a private manifest used by tests. A rerun with the same seed must produce identical content hashes.

The first spreadsheet task explicitly defines:

- required columns and types;
- row identity and duplicate semantics;
- valid date formats and target normalization;
- negative quantity/revenue policy;
- missing email policy;
- permitted row deletion or repair;
- row-count expectations;
- numeric tolerance;
- pass threshold.

Avoid phrases such as “handled appropriately” without an executable rule.

### 3. Spreadsheet evaluator

Validate before grading:

- artifact existence and ownership reference;
- extension, MIME signature, compressed and expanded size;
- workbook/sheet count;
- required columns;
- row and cell limits;
- parse errors and formula behavior.

Return one canonical check per rubric item with ID, points, pass state, learner-safe detail, and internal diagnostic code.

### 4. SQL evaluator

When scheduled after the spreadsheet vertical slice:

- use an isolated SQLite database containing only task fixtures;
- accept one read-only query;
- reject writes, attach, extensions, pragmas outside an allowlist, and multiple statements;
- set execution/progress limits;
- compare normalized result sets with explicit ordering, duplicate, null, and numeric tolerance rules;
- destroy the sandbox after evaluation.

### 5. Communication evaluator

Separate deterministic requirements such as required facts, recipient, length, and prohibited sensitive data from optional LLM style coaching. An LLM must not be the sole authority for task completion.

### 6. Performance and reproducibility

Benchmark supported files on the target runtime shape. Persist evaluator version, task version, input hash, check results, and duration so any outcome can be explained later.

## Acceptance criteria

- The dirty fixture fails and the clean reference scores 100.
- Each planted defect can be independently enabled and detected.
- Scoring totals exactly 100 and validates all boundaries.
- The same artifact and versions always produce the same result.
- Errors use stable codes and learner-safe messages.
- Malformed, spoofed, oversized, or adversarial files fail without crashing.
- Formula, date, duplicate, null, and numeric behavior is explicitly tested.
- A supported 5 MB spreadsheet meets the agreed performance budget.
- Evaluators do not access learner progression or provider APIs.
- SQL evaluation cannot modify application or host data.

## Required tests and reviews

- Golden dirty/clean tests.
- One test for every check passing and failing independently.
- Boundary tests around score threshold and file limits.
- Malformed workbook, MIME spoof, traversal, and expansion-limit tests.
- Property tests for generated datasets where useful.
- Performance benchmark recorded in CI without flaky wall-clock assertions.
- Contract tests using Member 2's fixtures.
- Rubric review and approval from Member 1.

## Pull request responsibilities

Member 4 is required reviewer for:

- evaluator algorithms;
- task data generators and fixtures;
- scoring semantics;
- evaluator security and performance;
- changes to fields consumed by feedback.

Scoring-policy changes require Member 1 approval. Contract changes require Member 2 approval. Member 3 reviews changes that alter feedback inputs.

## Handoffs

- To Member 2: evaluator port implementation behavior and stable errors.
- To Member 3: safe structured checks, business consequences, and hints.
- To Member 5: fake evaluator, supported upload types/limits, and latency expectations.
- To Member 1: documented rubric, examples, and reproducibility evidence.

## Out of scope

- Advancing learner progress.
- Generating authoritative grades with an LLM.
- Executing student SQL against Supabase or application data.
- Changing learning objectives without Member 1 approval.
