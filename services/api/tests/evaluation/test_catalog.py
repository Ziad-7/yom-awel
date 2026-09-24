import asyncio
import json
import shutil
from pathlib import Path

import pytest

from tests.evaluation.support import TASK_VERSION, artifact_ref
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.catalog import TaskCatalog, csv_to_xlsx, dataset, heading, task_version_id
from yom_awel.evaluation.clean_sales_dataset import LEARNER_SEED, generate, to_csv
from yom_awel.evaluation.task_package import MANIFEST_NAME, TaskPackageError, content_hash

ROOT = Path(__file__).resolve().parents[4] / "task_packages"
CATALOG = TaskCatalog.load(ROOT)
TASK = CATALOG.get("clean-sales")


def copy_package(tmp_path: Path, version: str, **manifest_changes: object) -> Path:
    target = tmp_path / "clean-sales" / version
    shutil.copytree(ROOT / "clean-sales" / "1", target)
    manifest = json.loads((target / MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest.update({"version": version, **manifest_changes})
    (target / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False), "utf-8")
    return target


def test_catalog_builds_the_task_version_from_the_published_package():
    version = TASK.task_version

    assert [task.task_id for task in CATALOG.tasks()] == ["clean-sales"]
    assert (version.task_id, version.version, version.pass_threshold) == ("clean-sales", "1", 75)
    assert (version.evaluator_id, version.evaluator_version) == ("sales-cleaning", "1")
    assert version.content_hash == content_hash(TASK.package)
    assert version.task_version_id == task_version_id(TASK.package)
    assert version.instructions_ar == TASK.brief_ar
    assert version.instructions_en == TASK.brief_en
    assert [(m.check_id, m.skill_id, m.weight) for m in version.skill_mappings] == [
        (m.check_id, m.skill_id, m.weight) for m in TASK_VERSION.skill_mappings
    ]
    assert CATALOG.find_version(version.task_version_id) == version


def test_titles_come_from_the_briefs():
    assert TASK.title_en == "Practical Assignment: Cleaning Daily Sales Transactions"
    assert TASK.title_ar == heading(TASK.brief_ar)
    with pytest.raises(TaskPackageError):
        heading("no heading here")


def test_unknown_tasks_are_not_found():
    with pytest.raises(DomainError) as error:
        CATALOG.get("sql-report")
    assert error.value.code == "not_found"


def test_the_highest_published_version_wins_and_drafts_are_skipped(tmp_path):
    copy_package(tmp_path, "1")
    copy_package(tmp_path, "2")
    copy_package(tmp_path, "3", status="draft")

    assert TaskCatalog.load(tmp_path).get("clean-sales").package.version == "2"


def test_a_package_missing_its_dataset_is_refused(tmp_path):
    (copy_package(tmp_path, "1") / "data" / "sales_dirty.csv").unlink()

    with pytest.raises(TaskPackageError, match="sales_dirty.csv"):
        TaskCatalog.load(tmp_path)


def test_downloads_are_the_learner_file_in_both_formats():
    csv_file, xlsx_file = dataset(TASK, "csv"), dataset(TASK, "xlsx")

    assert (
        csv_file.content == (ROOT / "clean-sales" / "1" / "data" / "sales_dirty.csv").read_bytes()
    )
    assert (csv_file.filename, xlsx_file.filename) == ("sales_dirty.csv", "sales_dirty.xlsx")
    assert xlsx_file.content.startswith(b"PK\x03\x04")


@pytest.mark.parametrize(
    "content", [TASK.dataset_csv, to_csv(generate(LEARNER_SEED).clean).encode()]
)
def test_the_xlsx_conversion_grades_exactly_like_the_csv(content):
    evaluate = CATALOG.evaluator_registry().evaluate
    from_csv = asyncio.run(evaluate(TASK.task_version, artifact_ref(content)))
    from_xlsx = asyncio.run(
        evaluate(TASK.task_version, artifact_ref(csv_to_xlsx(content), "sales.xlsx"))
    )

    assert from_csv.checks == from_xlsx.checks
    assert from_csv.score == from_xlsx.score
