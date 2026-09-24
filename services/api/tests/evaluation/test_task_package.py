import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from yom_awel.domain.contracts import TaskVersion
from yom_awel.evaluation.task_package import (
    MANIFEST_NAME,
    MAX_ARTIFACT_BYTES,
    TaskPackageError,
    content_hash,
    load_task_package,
    parse_task_package,
)

ROOT = Path(__file__).resolve().parents[4]
CLEAN_SALES = ROOT / "task_packages" / "clean-sales" / "1"
CLEAN_SALES_MANIFEST: dict[str, Any] = json.loads(
    (CLEAN_SALES / MANIFEST_NAME).read_text(encoding="utf-8")
)
LEARNING_OBJECTIVES: dict[str, Any] = yaml.safe_load(
    (CLEAN_SALES / "learning-objectives.yaml").read_text(encoding="utf-8")
)
BRIEF_AR = "نظّف بيانات المبيعات.\n".encode()


def manifest(**overrides: Any) -> dict[str, Any]:
    value = copy.deepcopy(CLEAN_SALES_MANIFEST)
    value.update(overrides)
    return value


def write_package(root: Path, data: dict[str, Any], files: dict[str, bytes]) -> Path:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (root / MANIFEST_NAME).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return root


def published(files: dict[str, bytes]) -> dict[str, Any]:
    pinned = [
        {"path": name, "sha256": hashlib.sha256(content).hexdigest()}
        for name, content in files.items()
    ]
    return manifest(status="published", content=pinned)


def assert_rejected(data: dict[str, Any], reason: str) -> None:
    with pytest.raises(TaskPackageError, match=reason) as error:
        parse_task_package(json.dumps(data))
    assert error.value.code == "task_package_invalid"


def test_clean_sales_v1_is_complete_and_balanced() -> None:
    package = parse_task_package(json.dumps(CLEAN_SALES_MANIFEST))

    assert package.task_id == "clean-sales"
    assert package.version == "1"
    assert package.evaluator_id == "sales-cleaning"
    assert package.evaluator_version == "1"
    assert package.pass_threshold == 75
    assert package.limits.max_bytes == MAX_ARTIFACT_BYTES
    assert [check.points for check in package.checks] == [25, 25, 25, 25]
    assert package.policy.business_key == "order_id"
    assert package.dataset_seed == 20260920
    assert package.critical_check_ids == {"unique_orders"}


def test_clean_sales_checks_match_the_canonical_task_version_fixture() -> None:
    package = parse_task_package(json.dumps(CLEAN_SALES_MANIFEST))
    fixture = TaskVersion.model_validate_json(
        (ROOT / "contracts" / "fixtures" / "task-version-clean-sales.json").read_text("utf-8")
    )

    assert [(c.check_id, c.skill_id, c.points) for c in package.checks] == [
        (m.check_id, m.skill_id, m.weight) for m in fixture.skill_mappings
    ]
    assert package.pass_threshold == fixture.pass_threshold


def test_clean_sales_v1_is_published_with_verified_member_1_content() -> None:
    package = load_task_package(CLEAN_SALES)

    assert package.status == "published"
    assert [item.path for item in package.content] == [
        "content/brief.ar-EG.md",
        "content/brief.en.md",
        "content/hints.ar-EG.md",
        "content/hints.en.md",
    ]


def test_clean_sales_manifest_matches_the_merged_learning_objectives() -> None:
    package = parse_task_package(json.dumps(CLEAN_SALES_MANIFEST))
    policy = LEARNING_OBJECTIVES["pass_policy"]
    formats = LEARNING_OBJECTIVES["format_policy"]
    bounds = formats["bounds"]
    content = LEARNING_OBJECTIVES["content_manifest"]
    guidance = {
        item["check_id"]: (item["guidance_ar"], item["guidance_en"])
        for item in LEARNING_OBJECTIVES["diagnostic_vocabulary"]["check_diagnostics"]
    }
    objectives = {
        check_id: (objective["points"], objective["skill_id"])
        for objective in LEARNING_OBJECTIVES["learning_objectives"]
        for check_id in objective["check_ids"]
    }

    assert (package.task_id, package.version) == (
        LEARNING_OBJECTIVES["task_id"],
        LEARNING_OBJECTIVES["version"],
    )
    assert (package.evaluator_id, package.evaluator_version) == (
        policy["evaluator_id"],
        policy["evaluator_version"],
    )
    assert package.pass_threshold == policy["pass_threshold"]
    assert package.critical_check_ids == set(policy["critical_checks"])
    assert {c.check_id: (c.points, c.skill_id) for c in package.checks} == objectives
    assert {c.check_id: (c.hint_ar, c.hint_en) for c in package.checks} == guidance
    assert (
        list(package.policy.required_columns)
        == (LEARNING_OBJECTIVES["required_artifacts"]["output"]["required_columns"])
    )
    assert list(package.limits.extensions) == formats["supported_formats"]
    assert (
        package.limits.max_bytes,
        package.limits.max_expanded_bytes,
        package.limits.max_rows,
        package.limits.max_columns,
    ) == (
        bounds["max_bytes"],
        bounds["max_expanded_bytes"],
        bounds["max_rows"],
        bounds["max_columns"],
    )
    assert {item.path: item.sha256 for item in package.content} == {
        content[name]: content["pinned_hashes"][f"{name}_sha256"]
        for name in ("brief_ar", "brief_en", "hints_ar", "hints_en")
    }


def test_published_package_loads_and_verifies_pinned_content(tmp_path: Path) -> None:
    files = {"content/brief.ar-EG.md": BRIEF_AR}
    package = load_task_package(write_package(tmp_path, published(files), files))

    assert package.status == "published"
    assert [item.path for item in package.content] == ["content/brief.ar-EG.md"]


def test_content_hash_is_stable_and_tracks_pinned_content() -> None:
    first = parse_task_package(json.dumps(published({"brief.md": b"one"})))
    same = parse_task_package(json.dumps(published({"brief.md": b"one"})))
    changed = parse_task_package(json.dumps(published({"brief.md": b"two"})))

    assert content_hash(first) == content_hash(same)
    assert content_hash(first) != content_hash(changed)
    assert len(content_hash(first)) == 64


@pytest.mark.parametrize(
    ("files_on_disk", "reason"),
    [
        ({}, "is missing"),
        ({"brief.md": b" \n"}, "is empty"),
        ({"brief.md": b"edited after publication"}, "changed after it was pinned"),
    ],
)
def test_load_rejects_unverifiable_content(
    tmp_path: Path, files_on_disk: dict[str, bytes], reason: str
) -> None:
    write_package(tmp_path, published({"brief.md": b"pinned"}), files_on_disk)

    with pytest.raises(TaskPackageError, match=reason):
        load_task_package(tmp_path)


def test_load_rejects_symlink_escaping_the_package(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"secret")
    package_root = tmp_path / "package"
    package_root.mkdir()
    try:
        (package_root / "brief.md").symlink_to(outside)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows requires Developer Mode or elevation to create symlinks")
        raise
    write_package(package_root, published({"brief.md": b"secret"}), {})

    with pytest.raises(TaskPackageError, match="escapes the package"):
        load_task_package(package_root)


def test_rejects_duplicate_check_ids() -> None:
    checks = copy.deepcopy(CLEAN_SALES_MANIFEST["checks"])
    checks[1]["check_id"] = checks[0]["check_id"]
    assert_rejected(manifest(checks=checks), "check_id values must be unique")


def test_rejects_points_that_do_not_total_100() -> None:
    checks = copy.deepcopy(CLEAN_SALES_MANIFEST["checks"])
    checks[0]["points"] = 24
    assert_rejected(manifest(checks=checks), "must total 100")


@pytest.mark.parametrize("column", ["business_key", "missing_email_reason_column"])
def test_rejects_policy_columns_that_are_not_required(column: str) -> None:
    policy = copy.deepcopy(CLEAN_SALES_MANIFEST["policy"])
    policy[column] = "undeclared"
    assert_rejected(manifest(policy=policy), "undeclared must be a required column")


def test_rejects_duplicate_required_columns() -> None:
    policy = copy.deepcopy(CLEAN_SALES_MANIFEST["policy"])
    policy["required_columns"].append("order_id")
    assert_rejected(manifest(policy=policy), "required_columns must be unique")


@pytest.mark.parametrize("critical", [None, "true", 1])
def test_rejects_a_missing_or_non_boolean_critical_flag(critical: Any) -> None:
    checks = copy.deepcopy(CLEAN_SALES_MANIFEST["checks"])
    if critical is None:
        del checks[0]["critical"]
    else:
        checks[0]["critical"] = critical
    assert_rejected(manifest(checks=checks), "checks.0.critical")


def test_rejects_published_package_without_pinned_content() -> None:
    assert_rejected(manifest(content=[]), "must pin its content files")


@pytest.mark.parametrize("path", ["/etc/passwd", "../brief.md", "content/../../x", "a\\b"])
def test_rejects_content_paths_outside_the_package(path: str) -> None:
    content = [{"path": path, "sha256": "a" * 64}]
    assert_rejected(manifest(content=content), "relative to the package")


def test_rejects_artifact_limit_above_the_upload_limit() -> None:
    limits = copy.deepcopy(CLEAN_SALES_MANIFEST["limits"])
    limits["max_bytes"] = MAX_ARTIFACT_BYTES + 1
    assert_rejected(manifest(limits=limits), "limits.max_bytes")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task_id", "Clean Sales"),
        ("version", "01"),
        ("evaluator_version", 1),
        ("pass_threshold", 101),
        ("status", "archived"),
        ("unexpected", True),
    ],
)
def test_rejects_invalid_top_level_fields(field: str, value: Any) -> None:
    assert_rejected(manifest(**{field: value}), field)
