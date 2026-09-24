"""Validator for task learning objectives and content contracts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def validate_objectives_manifest(
    data: dict[str, Any], root_dir: Path | None = None
) -> list[str]:
    """Validate a parsed learning-objectives.yaml manifest.

    Returns a list of human-readable error strings. An empty list denotes a valid manifest.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Manifest root must be a YAML dictionary."]

    if data.get("task_id") != "clean-sales":
        errors.append(f"task_id must be 'clean-sales', got '{data.get('task_id')}'.")

    if str(data.get("version")) != "1":
        errors.append(f"version must be '1', got '{data.get('version')}'.")

    if not data.get("intended_learner_level"):
        errors.append("Missing required 'intended_learner_level'.")

    context = data.get("workplace_context")
    if not isinstance(context, dict) or not context.get("company_name"):
        errors.append("Missing or incomplete 'workplace_context' section.")

    # Artifacts
    artifacts = data.get("required_artifacts")
    if (
        not isinstance(artifacts, dict)
        or not artifacts.get("input")
        or not artifacts.get("output")
    ):
        errors.append("Missing or incomplete 'required_artifacts' section.")

    # Pass policy
    pass_policy = data.get("pass_policy")
    if not isinstance(pass_policy, dict):
        errors.append("Missing 'pass_policy' section.")
        total_points = 100
    else:
        total_points = pass_policy.get("total_points", 100)
        threshold = pass_policy.get("pass_threshold", 75)
        if not isinstance(threshold, int) or threshold <= 0 or threshold > total_points:
            errors.append(f"Invalid pass_threshold '{threshold}'.")

        rule = pass_policy.get("rule")
        expected_rule = "passed = score >= 75 AND every critical check passed"
        if rule != expected_rule:
            errors.append(f"pass_policy.rule must be '{expected_rule}', got '{rule}'.")

        critical_checks = pass_policy.get("critical_checks")
        if (
            not isinstance(critical_checks, list)
            or "unique_orders" not in critical_checks
        ):
            errors.append("pass_policy.critical_checks must list 'unique_orders'.")

    # Format policy
    format_policy = data.get("format_policy")
    if not isinstance(format_policy, dict):
        errors.append("Missing 'format_policy' section.")
    else:
        supported = format_policy.get("supported_formats", [])
        if "csv" not in supported or "xlsx" not in supported:
            errors.append(
                "format_policy.supported_formats must support both 'csv' and 'xlsx'."
            )

    # Diagnostic vocabulary
    diag_vocab = data.get("diagnostic_vocabulary")
    if not isinstance(diag_vocab, dict):
        errors.append("Missing 'diagnostic_vocabulary' section.")
    else:
        if (
            not isinstance(diag_vocab.get("rejections"), list)
            or len(diag_vocab["rejections"]) == 0
        ):
            errors.append("diagnostic_vocabulary must contain non-empty 'rejections'.")
        if (
            not isinstance(diag_vocab.get("check_diagnostics"), list)
            or len(diag_vocab["check_diagnostics"]) == 0
        ):
            errors.append(
                "diagnostic_vocabulary must contain non-empty 'check_diagnostics'."
            )

    # Learning objectives
    objectives = data.get("learning_objectives")
    if not isinstance(objectives, list) or len(objectives) == 0:
        errors.append("Manifest must contain a non-empty 'learning_objectives' list.")
    else:
        seen_ids: set[str] = set()
        points_sum = 0
        for idx, obj in enumerate(objectives):
            if not isinstance(obj, dict):
                errors.append(f"Objective at index {idx} must be a dictionary.")
                continue

            obj_id = obj.get("id")
            if not obj_id or not isinstance(obj_id, str):
                errors.append(f"Objective at index {idx} missing valid 'id'.")
            elif obj_id in seen_ids:
                errors.append(f"Duplicate objective id: '{obj_id}'.")
            else:
                seen_ids.add(obj_id)

            if not obj.get("title") or not obj.get("description"):
                errors.append(
                    f"Objective '{obj_id or idx}' missing title or description."
                )

            if not obj.get("skill_id"):
                errors.append(f"Objective '{obj_id or idx}' missing 'skill_id'.")

            checks = obj.get("check_ids")
            if not isinstance(checks, list) or len(checks) == 0:
                errors.append(
                    f"Objective '{obj_id or idx}' must map to at least one check_id."
                )

            pts = obj.get("points")
            if not isinstance(pts, int) or pts <= 0:
                errors.append(
                    f"Objective '{obj_id or idx}' must define positive integer points."
                )
            else:
                points_sum += pts

        if isinstance(pass_policy, dict) and points_sum != total_points:
            errors.append(
                f"Sum of objective points ({points_sum}) does not equal total_points ({total_points})."
            )

    # Transformations
    transforms = data.get("transformations")
    if not isinstance(transforms, dict):
        errors.append("Missing 'transformations' section.")
    else:
        if (
            not isinstance(transforms.get("allowed"), list)
            or len(transforms["allowed"]) == 0
        ):
            errors.append("Transformations must define a non-empty 'allowed' list.")
        if (
            not isinstance(transforms.get("forbidden"), list)
            or len(transforms["forbidden"]) == 0
        ):
            errors.append("Transformations must define a non-empty 'forbidden' list.")

    # Misconceptions
    misconceptions = data.get("misconception_catalog")
    if not isinstance(misconceptions, list) or len(misconceptions) == 0:
        errors.append("Manifest must contain a non-empty 'misconception_catalog'.")

    # Content manifest
    content_manifest = data.get("content_manifest")
    if not isinstance(content_manifest, dict):
        errors.append("Missing 'content_manifest' section.")
    elif root_dir is not None:
        base_dir = root_dir / "task_packages" / "clean-sales" / "1"
        for key in ["brief_ar", "brief_en", "hints_ar", "hints_en"]:
            rel_path = content_manifest.get(key)
            if not rel_path:
                errors.append(f"content_manifest missing entry for '{key}'.")
                continue
            full_path = base_dir / rel_path
            if not full_path.exists():
                errors.append(f"Referenced content file does not exist: {full_path}")
            elif full_path.stat().st_size == 0:
                errors.append(f"Referenced content file is empty: {full_path}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    manifest_path = (
        root / "task_packages" / "clean-sales" / "1" / "learning-objectives.yaml"
    )

    if len(sys.argv) > 1:
        manifest_path = Path(sys.argv[1])

    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    try:
        content = manifest_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except (yaml.YAMLError, OSError) as exc:
        print(f"Error reading YAML file: {exc}", file=sys.stderr)
        return 1

    errors = validate_objectives_manifest(data, root_dir=root)
    if errors:
        print(
            f"FAILED: Found {len(errors)} error(s) in learning objectives:",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"SUCCESS: Learning objectives at {manifest_path} are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
