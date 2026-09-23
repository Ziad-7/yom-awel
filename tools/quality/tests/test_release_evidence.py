from pathlib import Path

import yaml

from tools.quality.validate_release_evidence import validate_release_evidence


ROOT = Path(__file__).resolve().parents[3]
SOURCES_PATH = ROOT / "docs" / "product" / "evidence" / "source-register.yaml"
CLAIMS_PATH = ROOT / "docs" / "product" / "evidence" / "claim-matrix.yaml"


def test_release_evidence_is_valid() -> None:
    assert SOURCES_PATH.exists(), f"Missing source register at {SOURCES_PATH}"
    assert CLAIMS_PATH.exists(), f"Missing claim matrix at {CLAIMS_PATH}"

    sources_data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    claims_data = yaml.safe_load(CLAIMS_PATH.read_text(encoding="utf-8"))

    errors = validate_release_evidence(sources_data, claims_data)
    assert errors == [], f"Evidence validation errors: {errors}"


def test_statistical_claims_reference_valid_sources() -> None:
    sources_data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    claims_data = yaml.safe_load(CLAIMS_PATH.read_text(encoding="utf-8"))

    registered_sources = {s["id"] for s in sources_data.get("sources", []) if "id" in s}

    for claim in claims_data.get("claims", []):
        if claim.get("type") == "statistical":
            source_ref = claim.get("source_id")
            assert source_ref in registered_sources, (
                f"Statistical claim '{claim.get('id')}' references unknown source '{source_ref}'"
            )


def test_current_claims_have_concrete_test_and_preview_evidence() -> None:
    claims_data = yaml.safe_load(CLAIMS_PATH.read_text(encoding="utf-8"))

    for claim in claims_data.get("claims", []):
        if claim.get("status") == "current":
            evidence = claim.get("evidence", {})
            assert evidence.get("automated_tests"), (
                f"Current claim '{claim.get('id')}' lacks automated_tests evidence"
            )
            assert evidence.get("preview_checks"), (
                f"Current claim '{claim.get('id')}' lacks preview_checks evidence"
            )
