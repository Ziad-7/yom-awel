"""Validator for product release sign-off and quality gates."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

SHA_REGEX = re.compile(r"^[0-9a-f]{40}$")
UTC_TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
REQUIRED_GATES = [
    "zero_cost_review",
    "hobby_non_commercial_eligibility",
    "secret_scan",
    "automated_tests",
    "browser_acceptance",
    "gemini_fallback_test",
]
REQUIRED_MEMBERS = [f"member_{i}" for i in range(1, 6)]


def validate_release_signoff(
    data: dict[str, Any], root_dir: Path | None = None
) -> list[str]:
    """Validate release signoff metadata and quality gate decisions.

    Returns a list of error messages. Empty list indicates full validity.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Release sign-off root must be a YAML dictionary."]

    decision = data.get("decision")
    if decision not in ["go", "no-go"]:
        errors.append(f"Invalid decision '{decision}'. Must be 'go' or 'no-go'.")

    sha = data.get("tested_source_sha")
    if sha is None:
        if decision == "go":
            errors.append("A 'go' decision requires tested_source_sha.")
    elif not isinstance(sha, str) or not SHA_REGEX.fullmatch(sha):
        errors.append(
            f"Invalid tested_source_sha '{sha}'. Must be null or 40-char lowercase hex."
        )
    elif root_dir is not None:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=root_dir,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"tested_source_sha '{sha}' is not a resolvable Git commit.")

    # Quality gates
    gates = data.get("quality_gates")
    if not isinstance(gates, dict):
        errors.append("Missing 'quality_gates' dictionary.")
    else:
        for gate_name in REQUIRED_GATES:
            gate_info = gates.get(gate_name)
            if not isinstance(gate_info, dict):
                errors.append(f"Missing required quality gate '{gate_name}'.")
            elif decision == "go" and gate_info.get("status") != "passed":
                errors.append(
                    f"Cannot issue 'go' decision: quality gate '{gate_name}' is '{gate_info.get('status')}' (must be 'passed')."
                )

    # Member approvals can be superseded by an explicit, traceable sole-owner decision.
    override = data.get("owner_override")
    override_valid = False
    if override is not None:
        if not isinstance(override, dict):
            errors.append("owner_override must be a dictionary.")
        else:
            approver = override.get("approver")
            basis = override.get("basis")
            confirmed_at = override.get("confirmed_at")
            override_valid = (
                override.get("approved") is True
                and isinstance(approver, str)
                and bool(approver.strip())
                and isinstance(basis, str)
                and bool(basis.strip())
                and isinstance(confirmed_at, str)
                and bool(UTC_TIMESTAMP_REGEX.fullmatch(confirmed_at))
                and data.get("signoff_lead") == approver
            )
            if not override_valid:
                errors.append(
                    "owner_override requires approval, approver/signoff lead, basis, and a UTC confirmation timestamp."
                )

    approvals = data.get("member_approvals")
    if not isinstance(approvals, dict):
        errors.append("Missing 'member_approvals' dictionary.")
    else:
        for member_key in REQUIRED_MEMBERS:
            m_info = approvals.get(member_key)
            if not isinstance(m_info, dict):
                errors.append(f"Missing approval entry for '{member_key}'.")
            elif (
                decision == "go"
                and not override_valid
                and m_info.get("status") != "approved"
            ):
                errors.append(
                    f"Cannot issue 'go' decision: '{member_key}' approval is '{m_info.get('status')}' (must be 'approved')."
                )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    signoff_path = root / "docs" / "product" / "release" / "release-signoff.yaml"

    if len(sys.argv) > 1:
        signoff_path = Path(sys.argv[1])

    if not signoff_path.exists():
        print(f"Error: Signoff file not found at {signoff_path}", file=sys.stderr)
        return 1

    try:
        data = yaml.safe_load(signoff_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        print(f"Error reading YAML file: {exc}", file=sys.stderr)
        return 1

    errors = validate_release_signoff(data, root_dir=root)
    if errors:
        print(
            f"FAILED: Found {len(errors)} error(s) in release sign-off:",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if data["decision"] == "go":
        print("SUCCESS: Release sign-off is valid and approved.")
    else:
        print("VALID: Release sign-off records a no-go decision.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
