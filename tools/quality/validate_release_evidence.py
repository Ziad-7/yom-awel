"""Validator for product claim matrix and authoritative source register."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

VALID_CLAIM_TYPES = {"statistical", "capability"}
VALID_CLAIM_STATUSES = {"current", "experimental", "roadmap", "verified"}
VALID_OWNERS = {"member-1", "member-2", "member-3", "member-4", "member-5"}


def validate_release_evidence(
    sources_data: dict[str, Any], claims_data: dict[str, Any]
) -> list[str]:
    """Validate source register and claim matrix.

    Returns a list of human-readable error strings. Empty list indicates validity.
    """
    errors: list[str] = []

    # 1. Validate sources
    if not isinstance(sources_data, dict):
        return ["Source register root must be a YAML dictionary."]

    sources = sources_data.get("sources")
    if not isinstance(sources, list):
        errors.append("Source register must contain a 'sources' list.")
        registered_source_ids: set[str] = set()
    else:
        registered_source_ids = set()
        for idx, src in enumerate(sources):
            if not isinstance(src, dict):
                errors.append(f"Source at index {idx} must be a dictionary.")
                continue

            src_id = src.get("id")
            if not src_id or not isinstance(src_id, str):
                errors.append(f"Source at index {idx} missing 'id'.")
            elif src_id in registered_source_ids:
                errors.append(f"Duplicate source id: '{src_id}'.")
            else:
                registered_source_ids.add(src_id)

            for req_field in [
                "title",
                "publisher",
                "publication_date",
                "url",
                "supported_claim",
            ]:
                val = src.get(req_field)
                if not val or not isinstance(val, str) or not val.strip():
                    errors.append(
                        f"Source '{src_id or idx}' missing required field '{req_field}'."
                    )

    # 2. Validate claims
    if not isinstance(claims_data, dict):
        errors.append("Claim matrix root must be a YAML dictionary.")
        return errors

    claims = claims_data.get("claims")
    if not isinstance(claims, list) or len(claims) == 0:
        errors.append("Claim matrix must contain a non-empty 'claims' list.")
        return errors

    seen_claim_ids: set[str] = set()
    for idx, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"Claim at index {idx} must be a dictionary.")
            continue

        c_id = claim.get("id")
        if not c_id or not isinstance(c_id, str):
            errors.append(f"Claim at index {idx} missing 'id'.")
        elif c_id in seen_claim_ids:
            errors.append(f"Duplicate claim id: '{c_id}'.")
        else:
            seen_claim_ids.add(c_id)

        c_type = claim.get("type")
        if c_type not in VALID_CLAIM_TYPES:
            errors.append(
                f"Claim '{c_id or idx}' has invalid type '{c_type}'. Must be one of {sorted(VALID_CLAIM_TYPES)}."
            )

        status = claim.get("status")
        if status not in VALID_CLAIM_STATUSES:
            errors.append(
                f"Claim '{c_id or idx}' has invalid status '{status}'. Must be one of {sorted(VALID_CLAIM_STATUSES)}."
            )

        owner = claim.get("owner")
        if owner not in VALID_OWNERS:
            errors.append(
                f"Claim '{c_id or idx}' has invalid owner '{owner}'. Must be one of {sorted(VALID_OWNERS)}."
            )

        wording = claim.get("wording")
        if not wording or not isinstance(wording, str) or not wording.strip():
            errors.append(f"Claim '{c_id or idx}' missing 'wording'.")

        locations = claim.get("usage_locations")
        if not isinstance(locations, list) or len(locations) == 0:
            errors.append(f"Claim '{c_id or idx}' missing 'usage_locations' list.")

        # Statistical claim specifics
        if c_type == "statistical":
            src_ref = claim.get("source_id")
            if not src_ref or src_ref not in registered_source_ids:
                errors.append(
                    f"Statistical claim '{c_id}' references unknown or missing source_id '{src_ref}'."
                )

        # Capability claim specifics
        if c_type == "capability" and status == "current":
            evidence = claim.get("evidence")
            if not isinstance(evidence, dict):
                errors.append(
                    f"Current capability claim '{c_id}' missing 'evidence' dictionary."
                )
            else:
                tests = evidence.get("automated_tests")
                if not isinstance(tests, list) or len(tests) == 0:
                    errors.append(
                        f"Current capability claim '{c_id}' must name at least one automated test in evidence.automated_tests."
                    )
                previews = evidence.get("preview_checks")
                if not isinstance(previews, list) or len(previews) == 0:
                    errors.append(
                        f"Current capability claim '{c_id}' must name at least one preview check in evidence.preview_checks."
                    )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    sources_path = root / "docs" / "product" / "evidence" / "source-register.yaml"
    claims_path = root / "docs" / "product" / "evidence" / "claim-matrix.yaml"

    if len(sys.argv) > 1:
        sources_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        claims_path = Path(sys.argv[2])

    if not sources_path.exists():
        print(f"Error: Source register not found at {sources_path}", file=sys.stderr)
        return 1

    if not claims_path.exists():
        print(f"Error: Claim matrix not found at {claims_path}", file=sys.stderr)
        return 1

    try:
        sources_data = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
        claims_data = yaml.safe_load(claims_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        print(f"Error reading YAML files: {exc}", file=sys.stderr)
        return 1

    errors = validate_release_evidence(sources_data, claims_data)
    if errors:
        print(
            f"FAILED: Found {len(errors)} error(s) in release evidence:",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"SUCCESS: Release evidence at {sources_path} and {claims_path} is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
