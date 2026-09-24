import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from yom_awel.evaluation.clean_sales_dataset import (
    COLUMNS,
    DEFECT_COUNTS,
    GENERATOR_VERSION,
    LEARNER_SEED,
    MISSING_EMAIL_REASON,
    ORDER_COUNT,
    REFERENCE_SEED,
    Defect,
    Row,
    apply_defects,
    defects_manifest,
    generate,
    to_csv,
)
from yom_awel.evaluation.task_package import MANIFEST_NAME, parse_task_package

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "task_packages" / "clean-sales" / "1"
GENERATOR = PACKAGE / "data" / "generate.py"
OUTPUTS = (
    Path("task_packages/clean-sales/1/data/sales_dirty.csv"),
    Path("services/api/tests/evaluation/fixtures/clean_sales_reference.csv"),
    Path("services/api/tests/evaluation/fixtures/clean_sales_defects.json"),
)
LEARNER = generate(LEARNER_SEED)
REFERENCE = generate(REFERENCE_SEED)


def run_generator(out: Path) -> dict[Path, str]:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "services" / "api" / "src")}
    subprocess.run([sys.executable, str(GENERATOR), str(out)], check=True, env=environment)
    return {path: hashlib.sha256((out / path).read_bytes()).hexdigest() for path in OUTPUTS}


def is_iso_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def follows_policy(row: Row) -> bool:
    quantity, price, revenue = (Decimal(row[c]) for c in ("quantity", "unit_price", "revenue"))
    has_contact = bool(row["customer_email"]) or (
        row["missing_email_reason"] == MISSING_EMAIL_REASON
    )
    return (
        is_iso_date(row["order_date"])
        and quantity > 0
        and quantity == quantity.to_integral_value()
        and price >= 0
        and abs(revenue - quantity * price) <= Decimal("0.01")
        and has_contact
    )


def test_generator_is_byte_for_byte_reproducible(tmp_path: Path) -> None:
    assert run_generator(tmp_path / "first") == run_generator(tmp_path / "second")


def test_committed_outputs_match_regeneration(tmp_path: Path) -> None:
    run_generator(tmp_path)
    for path in OUTPUTS:
        assert (ROOT / path).read_bytes() == (tmp_path / path).read_bytes(), path


def test_manifest_plants_the_declared_defect_counts_with_unique_ids() -> None:
    kinds = Counter(defect.kind for defect in REFERENCE.defects)
    ids = [defect.defect_id for defect in REFERENCE.defects]

    assert kinds == Counter(DEFECT_COUNTS)
    assert len(set(ids)) == len(ids) == 16
    assert len({defect.row for defect in REFERENCE.defects}) == 16


def test_manifest_is_labelled_non_release() -> None:
    manifest = json.loads(defects_manifest(REFERENCE))

    assert manifest["release"] is False
    assert manifest["seed"] == REFERENCE_SEED


def test_clean_reference_follows_every_policy_rule() -> None:
    order_ids = [row["order_id"] for row in REFERENCE.clean]

    assert len(REFERENCE.clean) == ORDER_COUNT
    assert len(set(order_ids)) == ORDER_COUNT
    assert all(follows_policy(row) for row in REFERENCE.clean)


@pytest.mark.parametrize("defect", REFERENCE.defects, ids=lambda defect: defect.defect_id)
def test_each_defect_can_be_enabled_alone(defect: Defect) -> None:
    dirty = apply_defects(REFERENCE.clean, [defect])
    changed = [i for i, row in enumerate(dirty[:ORDER_COUNT]) if row != REFERENCE.clean[i]]

    if defect.kind == "duplicate_order":
        assert changed == []
        assert dirty[ORDER_COUNT:] == (REFERENCE.clean[defect.row],)
    else:
        assert len(dirty) == ORDER_COUNT
        assert changed == [defect.row]
        assert not follows_policy(dirty[defect.row])


def test_dirty_learner_artifact_has_every_defect() -> None:
    dirty = LEARNER.dirty
    order_ids = Counter(row["order_id"] for row in dirty)

    assert len(dirty) == ORDER_COUNT + DEFECT_COUNTS["duplicate_order"]
    assert sum(count - 1 for count in order_ids.values()) == DEFECT_COUNTS["duplicate_order"]
    assert sum(not follows_policy(row) for row in dirty) == 11


def test_learner_rows_are_distinct_from_test_reference_rows() -> None:
    learner = {tuple(row.values()) for row in LEARNER.clean}
    reference = {tuple(row.values()) for row in REFERENCE.clean}

    assert learner.isdisjoint(reference)


def test_csv_has_the_canonical_header_and_unix_newlines() -> None:
    text = to_csv(REFERENCE.clean)

    assert text.splitlines()[0] == ",".join(COLUMNS)
    assert "\r" not in text


def test_task_package_declares_this_generator() -> None:
    package = parse_task_package((PACKAGE / MANIFEST_NAME).read_text(encoding="utf-8"))

    assert package.dataset_seed == LEARNER_SEED
    assert package.generator_version == GENERATOR_VERSION
    assert package.policy.required_columns == COLUMNS
    assert package.policy.min_rows == ORDER_COUNT
    assert package.policy.missing_email_reason_value == MISSING_EMAIL_REASON
