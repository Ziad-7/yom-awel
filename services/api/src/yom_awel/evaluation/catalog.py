"""Published tasks read from the task-package directory.

The package on disk is the single source for what learners see, what is seeded as a
``TaskVersion``, and which evaluator grades it.
"""

import csv
import io
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid5

from openpyxl import Workbook

from yom_awel.domain.contracts import TaskVersion
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.registry import EvaluatorRegistry
from yom_awel.evaluation.sales_cleaning import SalesCleaningEvaluator
from yom_awel.evaluation.task_package import (
    MANIFEST_NAME,
    TaskPackage,
    TaskPackageError,
    content_hash,
    load_task_package,
)

TASK_VERSION_NAMESPACE = UUID("6f1d2c1e-9a55-4c7e-8f3b-2d0c6b7a4e10")
CONTENT_FILES = {
    "brief_ar": "content/brief.ar-EG.md",
    "brief_en": "content/brief.en.md",
    "hints_ar": "content/hints.ar-EG.md",
    "hints_en": "content/hints.en.md",
}
DATASET_PATH = "data/sales_dirty.csv"
DATASET_STEM = "sales_dirty"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DatasetFormat = Literal["csv", "xlsx"]


@dataclass(frozen=True)
class CatalogTask:
    package: TaskPackage
    task_version: TaskVersion
    title_ar: str
    title_en: str
    brief_ar: str
    brief_en: str
    hints_ar: str
    hints_en: str
    dataset_csv: bytes

    @property
    def task_id(self) -> str:
        return self.package.task_id


@dataclass(frozen=True)
class Dataset:
    filename: str
    media_type: str
    content: bytes


class TaskCatalog:
    def __init__(self, tasks: Mapping[str, CatalogTask]) -> None:
        self._tasks = dict(tasks)

    @classmethod
    def load(cls, root: Path) -> "TaskCatalog":
        """Load the highest published version of every task under ``root``."""

        latest: dict[str, CatalogTask] = {}
        for manifest in sorted(root.glob(f"*/*/{MANIFEST_NAME}")):
            package = load_task_package(manifest.parent)
            if package.status != "published":
                continue
            current = latest.get(package.task_id)
            if current is None or int(package.version) > int(current.package.version):
                latest[package.task_id] = _catalog_task(package, manifest.parent)
        return cls(latest)

    def tasks(self) -> tuple[CatalogTask, ...]:
        return tuple(self._tasks[task_id] for task_id in sorted(self._tasks))

    def get(self, task_id: str) -> CatalogTask:
        try:
            return self._tasks[task_id]
        except KeyError:
            raise DomainError("not_found", "Task not found") from None

    def find_version(self, task_version_id: UUID) -> TaskVersion | None:
        return next(
            (
                task.task_version
                for task in self._tasks.values()
                if task.task_version.task_version_id == task_version_id
            ),
            None,
        )

    def evaluator_registry(self) -> EvaluatorRegistry:
        return EvaluatorRegistry(
            {
                (task.package.evaluator_id, task.package.evaluator_version): (
                    SalesCleaningEvaluator(task.package)
                )
                for task in self._tasks.values()
            }
        )


def task_version_id(package: TaskPackage) -> UUID:
    """Stable identity: the same package content always maps to the same id."""

    return uuid5(
        TASK_VERSION_NAMESPACE, f"{package.task_id}@{package.version}#{content_hash(package)}"
    )


def build_task_version(package: TaskPackage, brief_ar: str, brief_en: str) -> TaskVersion:
    return TaskVersion.model_validate(
        {
            "task_version_id": task_version_id(package),
            "task_id": package.task_id,
            "version": package.version,
            "instructions_ar": brief_ar,
            "instructions_en": brief_en,
            "artifact_schema": {
                "type": "object",
                "required": ["filename", "format"],
                "properties": {
                    "filename": {"type": "string"},
                    "format": {"enum": list(package.limits.extensions)},
                },
            },
            "evaluator_id": package.evaluator_id,
            "evaluator_version": package.evaluator_version,
            "pass_threshold": package.pass_threshold,
            "skill_mappings": [
                {"check_id": check.check_id, "skill_id": check.skill_id, "weight": check.points}
                for check in package.checks
            ],
            "content_hash": content_hash(package),
        }
    )


def dataset(task: CatalogTask, file_format: DatasetFormat) -> Dataset:
    if file_format == "csv":
        return Dataset(f"{DATASET_STEM}.csv", "text/csv; charset=utf-8", task.dataset_csv)
    return Dataset(f"{DATASET_STEM}.xlsx", XLSX_MEDIA_TYPE, csv_to_xlsx(task.dataset_csv))


def csv_to_xlsx(content: bytes) -> bytes:
    """One worksheet holding every CSV cell as text, so the download grades like the CSV."""

    book = Workbook(write_only=True)
    sheet = book.create_sheet("sales")
    for row in csv.reader(io.StringIO(content.decode("utf-8-sig"), newline="")):
        sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def heading(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    raise TaskPackageError("brief has no top-level heading")


def _catalog_task(package: TaskPackage, root: Path) -> CatalogTask:
    unpinned = sorted(set(CONTENT_FILES.values()) - {item.path for item in package.content})
    if unpinned:
        raise TaskPackageError(f"published package does not pin {', '.join(unpinned)}")
    if not (root / DATASET_PATH).is_file():
        raise TaskPackageError(f"{DATASET_PATH} is missing")
    text = {key: (root / path).read_text(encoding="utf-8") for key, path in CONTENT_FILES.items()}
    return CatalogTask(
        package=package,
        task_version=build_task_version(package, text["brief_ar"], text["brief_en"]),
        title_ar=heading(text["brief_ar"]),
        title_en=heading(text["brief_en"]),
        brief_ar=text["brief_ar"],
        brief_en=text["brief_en"],
        hints_ar=text["hints_ar"],
        hints_en=text["hints_en"],
        dataset_csv=(root / DATASET_PATH).read_bytes(),
    )
