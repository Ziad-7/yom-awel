"""Validator for competition submission package and asset manifest."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import yaml

CLAIM_COMMENT_REGEX = re.compile(r"<!--\s*claim:\s*([a-zA-Z0-9_\-]+)\s*-->")
FORBIDDEN_TOKENS = ["TODO", "TBD", "REPLACE_ME", "localhost:"]
REQUIRED_FILES = [
    "application.md",
    "pitch-deck.md",
    "demo-script.md",
    "demo-contingency.md",
    "asset-manifest.yaml",
]


def validate_submission_package(root_dir: Path | None = None) -> list[str]:
    """Validate all submission package files, asset manifest hashes, and referenced claims.

    Returns a list of error strings. Empty list indicates full validity.
    """
    errors: list[str] = []

    if root_dir is None:
        root_dir = Path(__file__).resolve().parents[2]

    submission_dir = root_dir / "submission"
    if not submission_dir.exists():
        return [f"Submission directory not found at {submission_dir}"]

    # 1. Check required files
    for req_file in REQUIRED_FILES:
        target = submission_dir / req_file
        if not target.exists():
            errors.append(f"Missing required submission file: {target.name}")
        elif target.stat().st_size == 0:
            errors.append(f"Submission file is empty: {target.name}")

    # 2. Load claim matrix to verify claim references
    claims_path = root_dir / "docs" / "product" / "evidence" / "claim-matrix.yaml"
    known_claim_ids: set[str] = set()
    if claims_path.exists():
        try:
            claims_data = yaml.safe_load(claims_path.read_text(encoding="utf-8"))
            known_claim_ids = {
                c["id"] for c in claims_data.get("claims", []) if "id" in c
            }
        except (yaml.YAMLError, OSError) as exc:
            errors.append(f"Failed to load claim matrix: {exc}")

    # 3. Check markdown contents for placeholders and claim references
    for md_file in submission_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")

        for token in FORBIDDEN_TOKENS:
            if token in content:
                errors.append(f"Found forbidden token '{token}' in {md_file.name}")

        cited_claims = CLAIM_COMMENT_REGEX.findall(content)
        for claim_id in cited_claims:
            if known_claim_ids and claim_id not in known_claim_ids:
                errors.append(
                    f"File '{md_file.name}' cites unknown claim id: '{claim_id}'"
                )

    # 4. Validate asset manifest
    manifest_path = submission_dir / "asset-manifest.yaml"
    if manifest_path.exists():
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            errors.append(f"Failed to parse asset manifest: {exc}")
            return errors

        assets = manifest.get("assets", [])
        if not isinstance(assets, list) or len(assets) == 0:
            errors.append("asset-manifest.yaml must define a non-empty 'assets' list.")
        else:
            for idx, asset in enumerate(assets):
                if not isinstance(asset, dict):
                    errors.append(f"Asset at index {idx} must be a dictionary.")
                    continue

                for req_key in [
                    "id",
                    "source_path",
                    "export_path",
                    "mime_type",
                    "purpose",
                    "sha256",
                ]:
                    if not asset.get(req_key):
                        errors.append(
                            f"Asset '{asset.get('id', idx)}' missing required field '{req_key}'."
                        )

                src_rel = asset.get("source_path")
                if src_rel:
                    src_full = root_dir / src_rel
                    if not src_full.exists():
                        errors.append(
                            f"Asset '{asset.get('id')}' source_path does not exist: {src_rel}"
                        )
                    else:
                        actual_sha = hashlib.sha256(src_full.read_bytes()).hexdigest()
                        declared_sha = asset.get("sha256")
                        if declared_sha != actual_sha:
                            errors.append(
                                f"Asset '{asset.get('id')}' sha256 mismatch: "
                                f"declared '{declared_sha}' vs actual '{actual_sha}'"
                            )

                for cid in asset.get("claim_ids", []):
                    if known_claim_ids and cid not in known_claim_ids:
                        errors.append(
                            f"Asset '{asset.get('id')}' references unknown claim_id '{cid}'"
                        )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    errors = validate_submission_package(root_dir=root)
    if errors:
        print(
            f"FAILED: Found {len(errors)} error(s) in submission package:",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("SUCCESS: Submission package and asset manifest are fully valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
