"""Validator for the product capability ledger."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

VALID_STATUSES = {"current", "experimental", "roadmap"}
VALID_OWNERS = {"member-1", "member-2", "member-3", "member-4", "member-5"}


def validate_ledger(ledger: dict[str, Any]) -> list[str]:
    """Validate a parsed capability ledger dictionary.

    Returns a list of human-readable error messages. If empty, the ledger is valid.
    """
    errors: list[str] = []

    if not isinstance(ledger, dict):
        return ["Ledger root must be a YAML dictionary."]

    capabilities = ledger.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) == 0:
        return ["Ledger must contain a non-empty 'capabilities' list."]

    seen_ids: set[str] = set()

    for idx, item in enumerate(capabilities):
        if not isinstance(item, dict):
            errors.append(f"Capability at index {idx} must be a dictionary.")
            continue

        cap_id = item.get("id")
        if not cap_id or not isinstance(cap_id, str) or not cap_id.strip():
            errors.append(
                f"Capability at index {idx} is missing a valid non-empty 'id'."
            )
        elif cap_id in seen_ids:
            errors.append(f"Duplicate capability id: '{cap_id}'.")
        else:
            seen_ids.add(cap_id)

        owner = item.get("owner")
        if not owner or not isinstance(owner, str) or owner.strip() not in VALID_OWNERS:
            errors.append(
                f"Capability '{cap_id or idx}' has invalid or missing 'owner'. "
                f"Must be one of {sorted(VALID_OWNERS)}."
            )

        status = item.get("status")
        if status not in VALID_STATUSES:
            errors.append(
                f"Capability '{cap_id or idx}' has invalid status '{status}'. "
                f"Must be one of {sorted(VALID_STATUSES)}."
            )

        outcome = item.get("learner_outcome")
        if not outcome or not isinstance(outcome, str) or not outcome.strip():
            errors.append(f"Capability '{cap_id or idx}' is missing 'learner_outcome'.")

        impl_path = item.get("implementation_path")
        if not impl_path or (
            not isinstance(impl_path, str)
            and not (isinstance(impl_path, list) and len(impl_path) > 0)
        ):
            errors.append(
                f"Capability '{cap_id or idx}' is missing a valid 'implementation_path'."
            )

        evidence = item.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(
                f"Capability '{cap_id or idx}' is missing an 'evidence' dictionary."
            )
            continue

        automated_tests = evidence.get("automated_tests", [])
        preview_checks = evidence.get("preview_checks", [])

        if status == "current":
            if not isinstance(automated_tests, list) or len(automated_tests) == 0:
                errors.append(
                    f"Current capability '{cap_id}' must name at least one automated test in evidence.automated_tests."
                )
            if not isinstance(preview_checks, list) or len(preview_checks) == 0:
                errors.append(
                    f"Current capability '{cap_id}' must name at least one preview check in evidence.preview_checks."
                )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    target_path = root / "docs" / "product" / "capability-ledger.yaml"

    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])

    if not target_path.exists():
        print(f"Error: Capability ledger not found at {target_path}", file=sys.stderr)
        return 1

    try:
        content = target_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except (yaml.YAMLError, OSError) as exc:
        print(f"Error reading YAML file: {exc}", file=sys.stderr)
        return 1

    errors = validate_ledger(data)
    if errors:
        print(
            f"FAILED: Found {len(errors)} error(s) in capability ledger:",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"SUCCESS: Capability ledger at {target_path} is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
