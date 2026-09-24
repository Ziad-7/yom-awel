"""Regenerate the clean-sales@1 learner artifact and the synthetic test-only fixtures.

Usage: uv run --project services/api python task_packages/clean-sales/1/data/generate.py [OUT]
OUT defaults to the repository root.
"""

import sys
from pathlib import Path

from yom_awel.evaluation.clean_sales_dataset import (
    LEARNER_SEED,
    REFERENCE_SEED,
    defects_manifest,
    generate,
    to_csv,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
LEARNER_ARTIFACT = Path("task_packages/clean-sales/1/data/sales_dirty.csv")
TEST_FIXTURES = Path("services/api/tests/evaluation/fixtures")


def write(root: Path, relative: Path, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def main(root: Path) -> None:
    write(root, LEARNER_ARTIFACT, to_csv(generate(LEARNER_SEED).dirty))
    reference = generate(REFERENCE_SEED)
    write(root, TEST_FIXTURES / "clean_sales_reference.csv", to_csv(reference.clean))
    write(root, TEST_FIXTURES / "clean_sales_defects.json", defects_manifest(reference))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT)
