import asyncio
import hashlib

import pytest

from tests.evaluation.support import (
    PACKAGE,
    PACKAGE_ROOT,
    REFERENCE,
    TASK_VERSION,
    artifact_ref,
    to_xlsx,
)
from yom_awel.evaluation.clean_sales_dataset import to_csv
from yom_awel.evaluation.sales_cleaning import SalesCleaningEvaluator

RUNS = 20
DIRTY = PACKAGE_ROOT / "data" / "sales_dirty.csv"


def normalized(content: bytes, filename: str = "sales.csv") -> str:
    """Canonical result JSON without the only wall-clock field, ``duration_ms``."""

    evaluator = SalesCleaningEvaluator(PACKAGE)
    result = asyncio.run(evaluator.evaluate(TASK_VERSION, artifact_ref(content, filename)))
    return result.model_dump_json(exclude={"duration_ms"})


@pytest.mark.parametrize(
    ("content", "filename"),
    [
        (DIRTY.read_bytes(), "sales.csv"),
        (to_csv(REFERENCE.clean).encode(), "sales.csv"),
        (to_xlsx(REFERENCE.dirty), "sales.xlsx"),
        (to_xlsx(REFERENCE.clean, typed=True), "sales.xlsx"),
    ],
    ids=["dirty-csv", "clean-csv", "dirty-xlsx", "clean-xlsx"],
)
def test_repeated_runs_with_the_real_clock_are_byte_identical(
    content: bytes, filename: str
) -> None:
    first = normalized(content, filename)

    assert all(normalized(content, filename) == first for _ in range(RUNS - 1))


def test_evaluation_never_mutates_the_input_file() -> None:
    before = hashlib.sha256(DIRTY.read_bytes()).hexdigest()

    for _ in range(RUNS):
        normalized(DIRTY.read_bytes())

    assert hashlib.sha256(DIRTY.read_bytes()).hexdigest() == before
