# Member 4 Deterministic Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build reproducible task packages and secure deterministic evaluators that provide the only authoritative grade and skill evidence.

**Architecture:** Each immutable task package declares artifact schema, planted defects, checks, weights, pass threshold, safe hints, and skill mappings. Evaluators implement the shared async port, receive artifact bytes that the application loaded after its ownership check, validate hostile inputs before parsing, and return only canonical `EvaluationResult` objects.

**Tech Stack:** Python 3.12, pandas, openpyxl, sqlite3, Pydantic 2, pytest, Hypothesis where useful, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-09-20-yom-awel-platform-design.md`

## Global Constraints

- Evaluation is deterministic and independent of Gemini or persona output.
- A task/evaluator version plus artifact hash must reproduce the same result.
- Supported uploads are at most 5 MB and must pass extension, MIME signature, expanded-size, sheet, row, and column limits.
- Learner-safe errors reveal what to fix without exposing private reference solutions.
- Spreadsheet evaluation meets the 5-second p95 target on the Vercel Hobby runtime shape.
- Student SQL never executes against Supabase, application data, or a persistent host database.
- Task scoring changes require Member 1 approval and contract changes require Member 2 approval.

## Review Focus

- Duplicate detection must use declared business keys rather than accidental whole-row comparison.
- Date normalization must distinguish invalid values from merely different accepted input formats.
- Formula cells, macros, hidden sheets, and zip expansion must not bypass input limits.
- SQL result comparison must define order, duplicates, nulls, and numeric tolerance explicitly.
- A communication task may use deterministic content requirements, but an LLM cannot be its sole pass authority.

---

### Task M4-1: Define the Versioned Task Package Format

**Files:**
- Create: `services/api/src/yom_awel/evaluation/task_package.py`
- Create: `task_packages/clean-sales/1/task.json`
- Consume without editing: `task_packages/clean-sales/1/content/brief.ar-EG.md`
- Consume without editing: `task_packages/clean-sales/1/content/brief.en.md`
- Consume without editing: `task_packages/clean-sales/1/learning-objectives.yaml`
- Create: `services/api/tests/evaluation/test_task_package.py`

**Interfaces:**
- Consumes: canonical `TaskVersion`, skill, and evaluator identifiers.
- Produces: validated immutable task metadata for Members 1–4.

- [ ] **Step 1: Write failing task-package tests**

```python
from pathlib import Path

from yom_awel.evaluation.task_package import load_task_package


def test_clean_sales_v1_is_complete_and_balanced() -> None:
    package = load_task_package(Path("../../task_packages/clean-sales/1"))
    assert package.task_id == "clean-sales"
    assert package.version == "1"
    assert package.evaluator_id == "sales-cleaning"
    assert package.evaluator_version == "1"
    assert sum(check.points for check in package.checks) == 100
    assert package.pass_threshold == 75
    assert package.max_artifact_bytes == 5 * 1024 * 1024
```

Also test unique check IDs, non-empty Arabic instructions, declared business keys, skill mappings, and content hash mismatch rejection.

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/evaluation/test_task_package.py -q`

Expected: FAIL because the task package loader/files do not exist.

- [ ] **Step 3: Define package schema**

Include task/version IDs, published status, content hash, supported extensions/MIME, byte/expanded-size limits, required columns/types, business key, allowed date inputs, target date format, missing-email rule, negative-value rule, checks/points, pass threshold, safe hints, and skill evidence weights.

- [ ] **Step 4: Write exact cleaning policy**

For `clean-sales@1` define:

- required columns: `order_id`, `customer_email`, `order_date`, `quantity`, `unit_price`, `revenue`;
- business key: `order_id`;
- target date: ISO `YYYY-MM-DD`;
- quantity: positive integer;
- unit price and revenue: non-negative decimal;
- revenue tolerance: `abs(revenue - quantity * unit_price) <= 0.01`;
- missing email: normalized empty string is allowed only when a `missing_email_reason` column contains `unavailable`;
- duplicate order IDs: keep one valid record and reject conflicting duplicates;
- pass threshold: 75 with each of four checks worth 25.

- [ ] **Step 5: Validate Member 1's learner content**

Member 1 owns and authors both briefs and the learning-objectives manifest. Member 4 validates that the task package content hashes reference those exact files and that evaluator checks map to the approved objective/check IDs. Any content change occurs in a Member 1 pull request with Member 4 review; this lane does not create a competing instruction file.

- [ ] **Step 6: Implement loader and content hashing**

Load JSON and Markdown, validate with Pydantic, calculate stable content hash, and reject mutation after publication.

- [ ] **Step 7: Run and commit**

```bash
cd services/api
uv run pytest tests/evaluation/test_task_package.py -q
git add src/yom_awel/evaluation/task_package.py tests/evaluation/test_task_package.py ../../task_packages/clean-sales/1/task.json
git commit -m "feat: define clean-sales task package v1"
```

### Task M4-2: Generate Reproducible Dirty and Clean Fixtures

**Files:**
- Create: `task_packages/clean-sales/1/data/generate.py`
- Create: `task_packages/clean-sales/1/data/sales_dirty.csv`
- Create: `services/api/tests/evaluation/fixtures/clean_sales_reference.csv`
- Create: `services/api/tests/evaluation/fixtures/clean_sales_defects.json`
- Create: `services/api/tests/evaluation/test_dataset_generation.py`

**Interfaces:**
- Consumes: task package schema and fixed seed `20260920`.
- Produces: public learner artifact plus clearly labelled synthetic test-only reference/defect fixtures that differ from release learner rows.

- [ ] **Step 1: Write reproducibility test**

Generate twice into two temporary directories and assert matching SHA-256 hashes for the learner artifact and synthetic test-only reference/defect fixtures.

- [ ] **Step 2: Write defect-count tests**

Assert the manifest contains five duplicate IDs, three negative-value defects, four non-standard/invalid dates, and four missing-email cases with individually addressable defect IDs.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/evaluation/test_dataset_generation.py -q`

Expected: FAIL because generator and fixtures do not exist.

- [ ] **Step 4: Implement deterministic generator**

Use an injected `random.Random(20260920)`, fixed names/domains/products, fixed decimal quantization, and fixed dates. Never use current time or unordered set iteration.

- [ ] **Step 5: Separate learner data from public test fixtures**

Commit the dirty learner artifact as the instructional demo input. Generate a different synthetic dataset for the public clean-reference and defect tests; label it non-release and exclude the entire test fixture directory from the Vercel bundle. The production evaluator checks declared rules rather than matching learner rows to a committed answer key. This first milestone makes no anti-cheating or secure-assessment claim; a private item bank requires a later design.

- [ ] **Step 6: Verify hashes and commit**

```bash
python task_packages/clean-sales/1/data/generate.py
cd services/api
uv run pytest tests/evaluation/test_dataset_generation.py -q
git add ../../task_packages/clean-sales/1/data tests/evaluation/fixtures tests/evaluation/test_dataset_generation.py
git commit -m "test: add reproducible clean-sales fixtures"
```

### Task M4-3: Implement Safe Artifact Inspection

**Files:**
- Create: `services/api/src/yom_awel/evaluation/artifact_validation.py`
- Create: `services/api/tests/evaluation/test_artifact_validation.py`
- Create: `services/api/tests/evaluation/fixtures/malformed.xlsx`
- Create: `services/api/tests/evaluation/fixtures/oversized-metadata.xlsx`

**Interfaces:**
- Consumes: `ArtifactRef`, the artifact `content: bytes` passed through the evaluator port, and task-package limits.
- Produces: validated local artifact handle or canonical evaluation validation error.

- [ ] **Step 1: Write extension/MIME mismatch tests**

Test CSV named `.xlsx`, ZIP workbook named `.csv`, unsupported extension, missing file, and MIME mismatch. Each returns a stable code without parser traceback.

- [ ] **Step 2: Write resource-boundary tests**

Test exactly 5 MB metadata acceptance, one byte over rejection, excessive ZIP expanded-size estimate, too many sheets, too many rows/columns, encrypted workbook, and macro-enabled file rejection.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/evaluation/test_artifact_validation.py -q`

Expected: FAIL because artifact validation does not exist.

- [ ] **Step 4: Implement signature-first inspection**

Inspect magic/signature and ZIP central directory before openpyxl/pandas parsing. Enforce configured limits and close every file/ZIP handle through context managers.

- [ ] **Step 5: Normalize validation errors**

Return codes such as `artifact_too_large`, `unsupported_type`, `mime_mismatch`, `expanded_size_exceeded`, `sheet_limit_exceeded`, and `artifact_unreadable` with reviewed Arabic/English messages.

- [ ] **Step 6: Run security-focused tests and commit**

```bash
cd services/api
uv run pytest tests/evaluation/test_artifact_validation.py -q
git add src/yom_awel/evaluation/artifact_validation.py tests/evaluation
git commit -m "feat: validate untrusted evaluation artifacts"
```

### Task M4-4: Implement Spreadsheet Evaluator v1

**Files:**
- Create: `services/api/src/yom_awel/evaluation/sales_cleaning.py`
- Create: `services/api/src/yom_awel/evaluation/registry.py`
- Create: `services/api/tests/evaluation/test_sales_cleaning.py`
- Create: `services/api/tests/evaluation/test_sales_cleaning_boundaries.py`

**Interfaces:**
- Consumes: exact `Evaluator.evaluate(task_version, artifact, content)` port (contract change #5), validated artifact, task package.
- Produces: `EvaluationResult(evaluator_id="sales-cleaning", evaluator_version="1")`.

- [ ] **Step 1: Write golden pass/fail tests**

Load dirty and clean reference artifacts. Assert dirty fails with expected check IDs and clean passes with score 100 and no errors.

- [ ] **Step 2: Write independent-check tests**

Create one artifact per isolated failure:

- duplicate order ID;
- invalid/non-ISO date;
- non-positive quantity or negative money;
- missing email without reason or revenue mismatch.

Assert only the intended 25-point check fails.

- [ ] **Step 3: Write schema/boundary tests**

Test missing/extra column policy, reordered columns, empty dataset, duplicate conflict, decimal rounding at `0.01`, invalid date, timezone text, formula cells, and row order independence.

- [ ] **Step 4: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/evaluation/test_sales_cleaning.py tests/evaluation/test_sales_cleaning_boundaries.py -q`

Expected: FAIL because evaluator does not exist.

- [ ] **Step 5: Implement parsing into a normalized internal table**

Normalize column names exactly once, preserve raw values for diagnostics, parse dates with the declared allowlist, use decimal arithmetic for money, and avoid silently coercing invalid values into success.

- [ ] **Step 6: Implement four deterministic checks**

Return check IDs:

```text
unique_orders
standard_dates
valid_numeric_values
complete_customer_records
```

Each check awards 25 or 0 points, includes safe Arabic/English detail, and maps to declared skill evidence. `passed` is `score >= 75` after all checks execute.

- [ ] **Step 7: Register the evaluator**

Use an explicit `(evaluator_id, version)` registry. Reject an unknown evaluator/version; never fall back to a latest version silently.

- [ ] **Step 8: Run full evaluator tests and commit**

```bash
cd services/api
uv run pytest tests/evaluation -q
uv run mypy src/yom_awel/evaluation
uv run ruff check src/yom_awel/evaluation tests/evaluation
git add src/yom_awel/evaluation tests/evaluation
git commit -m "feat: add deterministic sales cleaning evaluator"
```

### Task M4-5: Prove Performance and Reproducibility

**Files:**
- Create: `services/api/tests/evaluation/test_reproducibility.py`
- Create: `services/api/benchmarks/benchmark_sales_cleaning.py`
- Create: `docs/quality/evaluator-v1-report.md`

**Interfaces:**
- Consumes: task/evaluator versions and representative artifact sizes.
- Produces: release evidence for repeatability and Vercel Hobby feasibility.

- [ ] **Step 1: Write repeated-run test**

Evaluate the same artifact 20 times and compare results after excluding `duration_ms`. Assert exact equality and no mutation of input files.

- [ ] **Step 2: Write version mismatch tests**

Assert unknown task/evaluator versions fail with stable configuration errors and do not use a newer registered evaluator.

- [ ] **Step 3: Create representative benchmarks**

Generate small, medium, and 5 MB maximum supported workbooks. Record parse/evaluation time and peak memory on the CI/runtime class. Keep benchmark thresholds in the report, not as flaky per-commit unit assertions.

- [ ] **Step 4: Run tests and benchmark**

```bash
cd services/api
uv run pytest tests/evaluation/test_reproducibility.py -q
uv run python benchmarks/benchmark_sales_cleaning.py
```

Expected: reproducibility passes; report shows whether 5-second p95 target is met.

- [ ] **Step 5: Document results and commit**

```bash
git add services/api/tests/evaluation/test_reproducibility.py services/api/benchmarks docs/quality/evaluator-v1-report.md
git commit -m "test: verify evaluator reproducibility and budget"
```

## Later Milestone — Requires Separate Product Approval

Tasks M4-6 and M4-7 are not part of the initial spreadsheet release completion gate. Start them only after the spreadsheet vertical slice is released and Members 1, 2, and 5 approve matching product journeys, contracts, interface work, and end-to-end acceptance scope.

### Task M4-6: Add Isolated SQL Evaluation

**Files:**
- Create: `task_packages/customer-sql/1/task.json`
- Create: `task_packages/customer-sql/1/data/schema.sql`
- Create: `task_packages/customer-sql/1/data/seed.sql`
- Create: `services/api/src/yom_awel/evaluation/sql_query.py`
- Create: `services/api/tests/evaluation/test_sql_query.py`
- Create: `services/api/tests/evaluation/test_sql_security.py`

**Interfaces:**
- Consumes: same evaluator port and canonical result schema.
- Produces: read-only SQL evaluator registered as `sql-query@1`.

- [ ] **Step 1: Write query-semantic tests**

Test correct query, row-order variation when order is unspecified, duplicate preservation, null comparison, decimal tolerance, syntax error, and wrong result.

- [ ] **Step 2: Write security tests**

Reject write statements, multiple statements, `ATTACH`, disallowed pragmas, extensions, recursive resource abuse, and statements exceeding progress/time limits.

- [ ] **Step 3: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/evaluation/test_sql_query.py tests/evaluation/test_sql_security.py -q`

Expected: FAIL because SQL task/evaluator do not exist.

- [ ] **Step 4: Implement per-request in-memory sandbox**

Create a new SQLite connection from trusted schema/seed, set authorizer and progress handler, execute exactly one read-only statement, normalize results by declared task semantics, then close and discard the database.

- [ ] **Step 5: Register and run tests**

Run: `cd services/api && uv run pytest tests/evaluation/test_sql_query.py tests/evaluation/test_sql_security.py -q`

Expected: all pass and application/Supabase data is never reachable.

- [ ] **Step 6: Commit**

```bash
git add task_packages/customer-sql services/api/src/yom_awel/evaluation services/api/tests/evaluation
git commit -m "feat: add isolated SQL task evaluation"
```

### Task M4-7: Add Deterministic Communication Requirements

**Files:**
- Create: `task_packages/client-email/1/task.json`
- Create: `services/api/src/yom_awel/evaluation/client_email.py`
- Create: `services/api/tests/evaluation/test_client_email.py`

**Interfaces:**
- Consumes: evaluator port and task-package content rules.
- Produces: deterministic content-completeness result; Member 3 may coach style but cannot determine pass alone.

- [ ] **Step 1: Write content-rule tests**

Test required subject, recipient name, incident fact, corrective action, deadline, prohibited sensitive data, minimum/maximum length, and empty content.

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd services/api && uv run pytest tests/evaluation/test_client_email.py -q`

Expected: FAIL because evaluator does not exist.

- [ ] **Step 3: Implement deterministic checks**

Use explicit normalized phrase/fact matching derived from the task package. Do not claim comprehensive style evaluation. Map passed checks to business-communication skill evidence.

- [ ] **Step 4: Run and commit**

```bash
cd services/api
uv run pytest tests/evaluation/test_client_email.py -q
git add ../../task_packages/client-email src/yom_awel/evaluation/client_email.py tests/evaluation/test_client_email.py
git commit -m "feat: add deterministic client email requirements"
```

## Member 4 Completion Gate

- Task packages are immutable, validated, and approved by Member 1.
- Dirty/clean fixtures regenerate identically and golden tests pass.
- Spreadsheet validation resists malformed and resource-abusive artifacts.
- Spreadsheet score and check semantics are deterministic and versioned.
- Performance report addresses the 5-second p95 target.
- SQL and communication evaluators remain out of the initial completion gate; when their later milestone is approved, its SQL sandbox must not reach application data and communication criteria must remain deterministic.
- Member 2 approves port/contract compatibility.
- Member 3 confirms feedback receives sufficient safe structured detail.
