# sales-cleaning@1 Evaluator Report

Evidence for #11 (M4-5): reproducibility and performance of `sales-cleaning@1` for `clean-sales@1`.

This report records local test evidence only. It makes no claim of release or deployment
readiness. Member 1's release decision stays `no-go` until the Member 4 and Member 5
integration and end-to-end acceptance are complete.

## Tested commit

- Evaluator code: `8cbde5b` (`feat(evaluation): add deterministic sales-cleaning evaluator v1`), on `main` at `244a8a1` plus the `openpyxl` dependency commit `c8753bc`.
- The commit that adds this report changes only tests, the benchmark script and this file, so the graded code is the code at `8cbde5b`.

## Status

| Area | Result |
|---|---|
| Reproducibility | Met. 20 runs with the real clock give byte-identical result JSON after excluding `duration_ms`, for CSV and XLSX, dirty and clean. |
| Input immutability | Met. The learner file hash is unchanged after 20 evaluations. |
| Unknown task or evaluator version | Met. `task_version_mismatch` and `unknown_evaluator` are raised with no fallback (tests in `test_sales_cleaning.py`). |
| CSV performance | Met locally against the declared budget. Not measured on Vercel. |
| XLSX performance | Met locally against the declared budget. The worst case has about 1.6x headroom. Not measured on Vercel. |

## Reproducibility evidence

- `services/api/tests/evaluation/test_reproducibility.py`
  - `test_repeated_runs_with_the_real_clock_are_byte_identical[dirty-csv, clean-csv, dirty-xlsx, clean-xlsx]`
  - `test_evaluation_never_mutates_the_input_file`
- `services/api/tests/evaluation/test_sales_cleaning.py`
  - `test_same_artifact_and_versions_always_produce_the_same_result`
  - `test_xlsx_and_csv_of_the_same_table_grade_identically[text-cells, typed-cells]`
  - `test_rejects_a_task_version_the_package_does_not_describe[5]`
  - `test_registry_never_falls_back_to_another_version[2]`

An outcome is explained later from the persisted `evaluator_id`, `evaluator_version`, `task_version_id`, the artifact `sha256`, and the check results. The same inputs always reproduce the same checks.

## Performance measurement

Command:

```text
uv run --project services/api python services/api/benchmarks/benchmark_sales_cleaning.py
```

- **Budget:** p95 at most 5,000 ms per input, declared as `BUDGET_P95_MS` in the script. The script exits non-zero when any input misses it.
- **Machine:** 4 vCPU Linux x86_64 container, CPython 3.12.3, no network service.
- **Method:** 30 runs per input, measured on 2026-09-24.
- **Inputs:** every input is a passing artifact built by repeating the synthetic reference rows with unique order IDs. The near-5 MiB workbook fills the 13 spare columns (up to the 20-column limit) with incompressible synthetic text.

| Input | Rows | Bytes | p50 ms | p95 ms | Peak KiB | Within budget |
|---|---:|---:|---:|---:|---:|---|
| small CSV | 40 | 2615 | 0.7 | 1.9 | 47 | yes |
| medium CSV | 1000 | 63359 | 12.9 | 18.3 | 621 | yes |
| max rows CSV | 10000 | 632834 | 127.6 | 145.2 | 6744 | yes |
| small XLSX | 40 | 6861 | 8.9 | 18.0 | 561 | yes |
| medium XLSX | 1000 | 36960 | 106.0 | 128.6 | 924 | yes |
| max rows XLSX | 10000 | 314702 | 1065.4 | 1178.3 | 6666 | yes |
| near 5 MiB XLSX | 10000 | 4833071 | 3016.1 | 3177.1 | 19661 | yes |

Timing covers validation, parsing and grading, which is everything inside `evaluate`.

## Findings

1. **The row limit caps CSV size.** `clean-sales@1` allows at most 10,000 data rows, so the largest valid CSV is about 0.63 MB. A larger CSV is rejected with `expanded_size_exceeded` before grading.
2. **XLSX parsing dominates.** Profiling the near-5 MiB workbook shows almost all time in openpyxl's worksheet XML parser; grading takes under 5% of the run.
3. **Cost grows linearly.** Time and memory grow in proportion to cells read. There is no quadratic path: duplicate detection is a single `Counter` pass, and the reader never looks past one row and one column beyond each limit.
4. **Headroom.** CSV has more than 30x headroom. The worst XLSX case has about 1.6x headroom locally; a slower serverless CPU could exceed the budget for that contrived input.

## Open items

- [ ] Re-run on the Vercel Hobby Python runtime once Member 5 wires the evaluator into a preview deployment. Record the region and memory size. If the worst XLSX case misses the budget there, decide with Member 1 whether to lower `max_columns` or `max_bytes` for v1.
- [ ] Member 1 to confirm the 10,000-row limit is the intended product limit.

Thresholds are judged here, not asserted in CI, so per-commit tests never fail on wall-clock noise.
