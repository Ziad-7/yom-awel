from pathlib import Path

import yaml

from tools.quality.validate_submission_package import validate_submission_package

ROOT = Path(__file__).resolve().parents[3]
SUBMISSION_DIR = ROOT / "submission"


def test_submission_package_is_valid() -> None:
    errors = validate_submission_package(root_dir=ROOT)
    assert errors == [], f"Submission package validation errors: {errors}"


def test_no_placeholders_or_localhost_in_submission_docs() -> None:
    forbidden_tokens = ["TODO", "TBD", "REPLACE_ME", "localhost:"]
    for file in SUBMISSION_DIR.glob("*.md"):
        content = file.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in content, (
                f"Found forbidden token '{token}' in {file.name}"
            )


def test_asset_manifest_is_complete() -> None:
    manifest_path = SUBMISSION_DIR / "asset-manifest.yaml"
    assert manifest_path.exists(), "Missing asset-manifest.yaml"

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assets = data.get("assets", [])
    assert len(assets) > 0, "Asset manifest must define at least one exportable asset"

    for asset in assets:
        for field in ["source_path", "export_path", "mime_type", "purpose"]:
            assert field in asset, f"Asset missing '{field}'"
