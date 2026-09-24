"""Deterministic clean-sales dataset: clean orders plus individually addressable defects."""

import csv
import io
import json
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

GENERATOR_VERSION = "1"
LEARNER_SEED = 20260920
REFERENCE_SEED = 20260921
ORDER_COUNT = 40
COLUMNS = (
    "order_id",
    "customer_email",
    "order_date",
    "quantity",
    "unit_price",
    "revenue",
    "missing_email_reason",
)
MISSING_EMAIL_REASON = "unavailable"

DefectKind = Literal["duplicate_order", "negative_value", "nonstandard_date", "missing_email"]
DEFECT_COUNTS: Mapping[DefectKind, int] = {
    "duplicate_order": 5,
    "negative_value": 3,
    "nonstandard_date": 4,
    "missing_email": 4,
}
NEGATIVE_COLUMNS = ("quantity", "unit_price", "revenue")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
FIRST_NAMES = ("ahmed", "mona", "karim", "salma", "omar", "nour", "youssef", "hana")
LAST_NAMES = ("hassan", "fahmy", "saleh", "nabil", "adel", "ezzat")
FIRST_ORDER_DATE = date(2026, 1, 1)
CENT = Decimal("0.01")

Row = dict[str, str]


@dataclass(frozen=True)
class Defect:
    defect_id: str
    kind: DefectKind
    row: int
    column: str
    dirty_value: str


@dataclass(frozen=True)
class Dataset:
    seed: int
    clean: tuple[Row, ...]
    defects: tuple[Defect, ...]

    @property
    def dirty(self) -> tuple[Row, ...]:
        return apply_defects(self.clean, self.defects)


def generate(seed: int) -> Dataset:
    rng = random.Random(seed)
    targets = rng.sample(range(ORDER_COUNT), sum(DEFECT_COUNTS.values()))
    rows_by_kind = _partition(targets)
    clean = tuple(
        _order(rng, index, has_email=index not in rows_by_kind["missing_email"])
        for index in range(ORDER_COUNT)
    )
    defects = tuple(
        defect for kind, rows in rows_by_kind.items() for defect in _defects(kind, rows, clean)
    )
    return Dataset(seed=seed, clean=clean, defects=defects)


def apply_defects(clean: Sequence[Row], defects: Iterable[Defect]) -> tuple[Row, ...]:
    rows = [dict(row) for row in clean]
    duplicates: list[Row] = []
    for defect in defects:
        if defect.kind == "duplicate_order":
            duplicates.append(dict(clean[defect.row]))
        else:
            rows[defect.row][defect.column] = defect.dirty_value
    return tuple(rows + duplicates)


def to_csv(rows: Iterable[Row]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def defects_manifest(dataset: Dataset) -> str:
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": dataset.seed,
        "release": False,
        "defects": [asdict(defect) for defect in dataset.defects],
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _partition(targets: Sequence[int]) -> dict[DefectKind, tuple[int, ...]]:
    partition: dict[DefectKind, tuple[int, ...]] = {}
    start = 0
    for kind, count in DEFECT_COUNTS.items():
        partition[kind] = tuple(sorted(targets[start : start + count]))
        start += count
    return partition


def _order(rng: random.Random, index: int, *, has_email: bool) -> Row:
    quantity = rng.randint(1, 20)
    unit_price = (Decimal(rng.randrange(500, 50_000)) / 100).quantize(CENT)
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    ordered_on = FIRST_ORDER_DATE + timedelta(days=rng.randrange(180))
    return {
        "order_id": f"SO-{1001 + index}",
        "customer_email": f"{first}.{last}{index}@example.com" if has_email else "",
        "order_date": ordered_on.isoformat(),
        "quantity": str(quantity),
        "unit_price": str(unit_price),
        "revenue": str((unit_price * quantity).quantize(CENT)),
        "missing_email_reason": "" if has_email else MISSING_EMAIL_REASON,
    }


def _defects(kind: DefectKind, rows: Sequence[int], clean: Sequence[Row]) -> Iterable[Defect]:
    for number, row in enumerate(rows, start=1):
        column, dirty_value = _dirty_cell(kind, number, clean[row])
        yield Defect(f"{kind}_{number}", kind, row, column, dirty_value)


def _dirty_cell(kind: DefectKind, number: int, row: Row) -> tuple[str, str]:
    if kind == "duplicate_order":
        return "order_id", row["order_id"]
    if kind == "negative_value":
        column = NEGATIVE_COLUMNS[number - 1]
        return column, f"-{row[column]}"
    if kind == "nonstandard_date":
        return "order_date", _nonstandard_date(date.fromisoformat(row["order_date"]), number)
    return "missing_email_reason", ""


def _nonstandard_date(value: date, style: int) -> str:
    """Locale-independent renderings a learner must normalize to ISO 8601."""

    month = MONTHS[value.month - 1]
    styles = (
        f"{value.day:02d}/{value.month:02d}/{value.year}",
        f"{value.year}/{value.month:02d}/{value.day:02d}",
        f"{value.day:02d}-{month}-{value.year}",
        f"{month} {value.day}, {value.year}",
    )
    return styles[style - 1]
