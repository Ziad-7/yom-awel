from pathlib import Path

import yaml

from tools.quality.validate_learning_objectives import validate_objectives_manifest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    ROOT / "task_packages" / "clean-sales" / "1" / "learning-objectives.yaml"
)


def test_learning_objectives_manifest_is_valid() -> None:
    assert MANIFEST_PATH.exists(), f"Missing manifest at {MANIFEST_PATH}"
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    errors = validate_objectives_manifest(data, root_dir=ROOT)
    assert errors == [], f"Validation errors: {errors}"


def test_learning_content_files_exist_and_are_bilingual() -> None:
    content_dir = ROOT / "task_packages" / "clean-sales" / "1" / "content"
    required_files = [
        "brief.ar-EG.md",
        "brief.en.md",
        "hints.ar-EG.md",
        "hints.en.md",
    ]
    for filename in required_files:
        filepath = content_dir / filename
        assert filepath.exists(), f"Required content file missing: {filepath}"
        content = filepath.read_text(encoding="utf-8").strip()
        assert len(content) > 100, f"Content file {filename} is too short"


def test_content_does_not_reveal_internal_ground_truth_answers() -> None:
    content_dir = ROOT / "task_packages" / "clean-sales" / "1" / "content"
    forbidden_spoilers = [
        "ORD-2026-999",  # internal synthetic test artifact IDs
        "12345.67",
    ]
    for filepath in content_dir.glob("*.md"):
        text = filepath.read_text(encoding="utf-8")
        for spoiler in forbidden_spoilers:
            assert spoiler not in text, (
                f"Found leaked answer in {filepath.name}: {spoiler}"
            )


def test_pass_policy_critical_check_and_parity() -> None:
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    pass_policy = data["pass_policy"]
    assert pass_policy["rule"] == "passed = score >= 75 AND every critical check passed"
    assert "unique_orders" in pass_policy["critical_checks"]
    assert data["format_policy"]["supported_formats"] == ["csv", "xlsx"]
    assert data["format_policy"]["evaluation_parity"] is True


def test_diagnostic_vocabulary_matches_member_4_boundary() -> None:
    data = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    codes = {item["code"] for item in data["diagnostic_vocabulary"]["rejections"]}
    assert codes == {
        "unsupported_type",
        "artifact_too_large",
        "mime_mismatch",
        "expanded_size_exceeded",
        "sheet_limit_exceeded",
        "artifact_unreadable",
        "missing_columns",
        "duplicate_columns",
        "too_few_rows",
    }

    objective_checks = {
        check_id
        for objective in data["learning_objectives"]
        for check_id in objective["check_ids"]
    }
    diagnostic_checks = {
        item["check_id"] for item in data["diagnostic_vocabulary"]["check_diagnostics"]
    }
    assert diagnostic_checks == objective_checks
