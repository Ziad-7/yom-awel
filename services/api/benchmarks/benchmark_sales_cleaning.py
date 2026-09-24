"""Benchmark sales-cleaning@1 on representative CSV and XLSX inputs; print a Markdown table.

Usage: uv run --project services/api python services/api/benchmarks/benchmark_sales_cleaning.py
Runs locally with no network service. Each input is judged against BUDGET_P95_MS, and the
script exits non-zero when any input misses it. Results are recorded in
docs/quality/evaluator-v1-report.md, not asserted in CI.
"""

import asyncio
import hashlib
import io
import random
import statistics
import string
import sys
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from openpyxl import Workbook

from yom_awel.domain.contracts import ArtifactRef, TaskVersion
from yom_awel.evaluation.clean_sales_dataset import (
    COLUMNS,
    REFERENCE_SEED,
    Row,
    generate,
    to_csv,
)
from yom_awel.evaluation.sales_cleaning import SalesCleaningEvaluator

ROOT = Path(__file__).resolve().parents[3]
EVALUATOR = SalesCleaningEvaluator.from_directory(ROOT / "task_packages" / "clean-sales" / "1")
TASK_VERSION = TaskVersion.model_validate_json(
    (ROOT / "contracts" / "fixtures" / "task-version-clean-sales.json").read_text("utf-8")
)
BUDGET_P95_MS = 5_000
RUNS = 30
MAX_ROWS = 10_000
MAX_BYTES = 5 * 1024 * 1024
# Incompressible text in every spare column brings a 10,000-row workbook close to 5 MiB.
FILLER_COLUMNS = tuple(f"note_{index}" for index in range(1, 20 - len(COLUMNS) + 1))
FILLER_LENGTH = 38


def scaled_rows(count: int) -> list[Row]:
    base = generate(REFERENCE_SEED).clean
    return [dict(base[i % len(base)], order_id=f"SO-{100_001 + i}") for i in range(count)]


def csv_bytes(rows: list[Row]) -> bytes:
    return to_csv(rows).encode()


def xlsx_bytes(rows: list[Row], filler: bool = False) -> bytes:
    rng = random.Random(REFERENCE_SEED)
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(COLUMNS + (FILLER_COLUMNS if filler else ()))
    for row in rows:
        notes = [
            "".join(rng.choices(string.ascii_letters, k=FILLER_LENGTH)) for _ in FILLER_COLUMNS
        ]
        sheet.append([row[column] for column in COLUMNS] + (notes if filler else []))
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


INPUTS: dict[str, tuple[str, Callable[[], bytes], int]] = {
    "small CSV": ("sales.csv", lambda: csv_bytes(scaled_rows(40)), 40),
    "medium CSV": ("sales.csv", lambda: csv_bytes(scaled_rows(1_000)), 1_000),
    "max rows CSV": ("sales.csv", lambda: csv_bytes(scaled_rows(MAX_ROWS)), MAX_ROWS),
    "small XLSX": ("sales.xlsx", lambda: xlsx_bytes(scaled_rows(40)), 40),
    "medium XLSX": ("sales.xlsx", lambda: xlsx_bytes(scaled_rows(1_000)), 1_000),
    "max rows XLSX": ("sales.xlsx", lambda: xlsx_bytes(scaled_rows(MAX_ROWS)), MAX_ROWS),
    "near 5 MiB XLSX": (
        "sales.xlsx",
        lambda: xlsx_bytes(scaled_rows(MAX_ROWS), filler=True),
        MAX_ROWS,
    ),
}


def artifact(filename: str, content: bytes) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=UUID(int=0),
        filename=filename,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )


def timed_run(filename: str, content: bytes) -> float:
    started = time.perf_counter()
    result = asyncio.run(EVALUATOR.evaluate(TASK_VERSION, artifact(filename, content)))
    elapsed = time.perf_counter() - started
    if not result.passed:
        raise RuntimeError(f"benchmark input {filename} must be a passing artifact")
    return elapsed * 1000


def peak_kib(filename: str, content: bytes) -> float:
    tracemalloc.start()
    timed_run(filename, content)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024


def main() -> int:
    print(f"Budget: p95 <= {BUDGET_P95_MS} ms per input, {RUNS} runs each.\n")
    print("| Input | Rows | Bytes | p50 ms | p95 ms | Peak KiB | Within budget |")
    print("|---|---:|---:|---:|---:|---:|---|")
    all_within = True
    for label, (filename, build, rows) in INPUTS.items():
        content = build()
        if len(content) > MAX_BYTES:
            raise RuntimeError(f"{label} is {len(content)} bytes, above the upload limit")
        timings = [timed_run(filename, content) for _ in range(RUNS)]
        p95 = statistics.quantiles(timings, n=20)[-1]
        within = p95 <= BUDGET_P95_MS
        all_within &= within
        print(
            f"| {label} | {rows} | {len(content)} | {statistics.median(timings):.1f} "
            f"| {p95:.1f} | {peak_kib(filename, content):.0f} | {'yes' if within else 'NO'} |"
        )
    return 0 if all_within else 1


if __name__ == "__main__":
    sys.exit(main())
