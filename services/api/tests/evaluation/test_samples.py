"""Every judge-mode sample earns exactly the outcome and score it advertises."""

import asyncio
import hashlib
from pathlib import Path
from uuid import UUID

import pytest

from yom_awel.domain.contracts import ArtifactRef
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.catalog import TaskCatalog
from yom_awel.evaluation.samples import SAMPLES, Sample, sample, samples_for

ROOT = Path(__file__).resolve().parents[4]
CATALOG = TaskCatalog.load(ROOT / "task_packages")
EVALUATORS = CATALOG.evaluators()
CASES = [(task_id, item) for task_id, items in SAMPLES.items() for item in items]


@pytest.mark.parametrize(
    ("task_id", "item"), CASES, ids=[f"{task_id}:{item.sample_id}" for task_id, item in CASES]
)
def test_each_sample_earns_its_advertised_result(task_id: str, item: Sample) -> None:
    task = CATALOG.get(task_id)
    evaluator = EVALUATORS[(task.package.evaluator_id, task.package.evaluator_version)]
    content = item.build(task)
    artifact = ArtifactRef(
        artifact_id=UUID(int=3),
        filename=item.filename,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )

    result = asyncio.run(evaluator.evaluate(task.task_version, artifact))

    outcome = "rejected" if result.errors else "pass" if result.passed else "retry"
    assert (outcome, result.score) == (item.outcome, item.score)
    assert item.filename.rsplit(".", 1)[1] in task.package.limits.extensions


def test_every_task_offers_a_failing_and_a_passing_sample() -> None:
    assert set(SAMPLES) == {task.task_id for task in CATALOG.tasks()}
    for task_id, items in SAMPLES.items():
        assert len({item.sample_id for item in items}) == len(items)
        assert {"pass", "retry"} <= {item.outcome for item in items}, task_id


def test_sales_samples_are_the_presenter_kit_files_byte_for_byte() -> None:
    task = CATALOG.get("clean-sales")
    for item in samples_for("clean-sales"):
        assert item.build(task) == (ROOT / "demo" / "files" / item.filename).read_bytes()


def test_unknown_samples_are_not_found() -> None:
    with pytest.raises(DomainError):
        sample("clean-sales", "missing")
    assert samples_for("no-such-task") == ()
