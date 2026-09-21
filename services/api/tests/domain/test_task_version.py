from uuid import uuid4

import pytest

from yom_awel.domain.contracts import SkillMapping, TaskVersion


def test_task_version_is_deeply_immutable() -> None:
    task_version = TaskVersion(
        task_version_id=uuid4(),
        task_id="test",
        version="1",
        instructions_ar="test",
        instructions_en="test",
        artifact_schema={"key": {"nested": "value"}, "arr": [1, 2]},
        evaluator_id="test",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=[SkillMapping(skill_id="s", check_id="c", weight=10)],
        content_hash="a" * 64,
    )

    with pytest.raises(TypeError, match="Immutable"):
        task_version.artifact_schema["key"]["nested"] = "new"  # type: ignore

    with pytest.raises(TypeError, match="Immutable"):
        task_version.artifact_schema["arr"].append(3)  # type: ignore

    with pytest.raises(TypeError, match="Immutable"):
        task_version.skill_mappings.append(SkillMapping(skill_id="s", check_id="c", weight=10))  # type: ignore


def test_task_version_preserves_json_schema() -> None:
    schema = TaskVersion.model_json_schema()
    assert schema["properties"]["artifact_schema"]["type"] == "object"
    assert "properties" not in schema["properties"]["artifact_schema"]
    assert schema["properties"]["skill_mappings"]["type"] == "array"


def test_task_version_is_defensively_copied() -> None:
    original_schema = {"key": {"nested": "value"}, "arr": [1, 2]}
    original_mappings = [SkillMapping(skill_id="s", check_id="c", weight=10)]

    task_version = TaskVersion(
        task_version_id=uuid4(),
        task_id="test",
        version="1",
        instructions_ar="test",
        instructions_en="test",
        artifact_schema=original_schema,  # type: ignore
        evaluator_id="test",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=original_mappings,  # type: ignore
        content_hash="a" * 64,
    )

    # Mutate originals
    original_schema["key"]["nested"] = "changed"  # type: ignore
    original_schema["arr"].append(3)  # type: ignore
    original_mappings.append(SkillMapping(skill_id="s2", check_id="c2", weight=10))

    # Assert task version remains unchanged
    assert task_version.artifact_schema["key"]["nested"] == "value"
    assert task_version.artifact_schema["arr"] == [1, 2]
    assert len(task_version.skill_mappings) == 1
    assert task_version.skill_mappings[0].skill_id == "s"


def test_task_version_blocks_inplace_operators() -> None:
    task_version = TaskVersion(
        task_version_id=uuid4(),
        task_id="test",
        version="1",
        instructions_ar="test",
        instructions_en="test",
        artifact_schema={"key": {"nested": "value"}, "arr": [1, 2]},
        evaluator_id="test",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=[SkillMapping(skill_id="s", check_id="c", weight=10)],
        content_hash="a" * 64,
    )

    with pytest.raises(TypeError, match="Immutable"):
        task_version.artifact_schema.setdefault("new_key", "value")  # type: ignore

    with pytest.raises(TypeError, match="Immutable"):
        task_version.artifact_schema |= {"new_key": "value"}  # type: ignore

    with pytest.raises(TypeError, match="Immutable"):
        task_version.artifact_schema["arr"] += [3]  # type: ignore

    with pytest.raises(TypeError, match="Immutable"):
        task_version.artifact_schema["arr"] *= 2  # type: ignore

    with pytest.raises(TypeError, match="Immutable"):
        task_version.skill_mappings += [SkillMapping(skill_id="s2", check_id="c2", weight=10)]  # type: ignore

    with pytest.raises(TypeError, match="Immutable"):
        task_version.skill_mappings *= 2  # type: ignore
