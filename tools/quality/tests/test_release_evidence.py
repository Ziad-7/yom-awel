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

    errors = validate_release_evidence(sources_data, claims_data, root_dir=ROOT)
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


def _claim(**overrides: object) -> dict[str, object]:
    claim: dict[str, object] = {
        "id": "claim-example",
        "type": "capability",
        "wording": "Example capability.",
        "usage_locations": ["README.md"],
        "status": "pending",
        "pending_reason": "Not yet verified end to end.",
        "owner": "member-1",
        "evidence": {"automated_tests": [], "artifacts": [], "preview_checks": []},
    }
    claim.update(overrides)
    return claim


def test_pending_claim_must_state_why_it_is_pending() -> None:
    errors = validate_release_evidence(
        {"sources": []}, {"claims": [_claim(pending_reason="")]}
    )

    assert errors == ["Pending claim 'claim-example' must state its 'pending_reason'."]


def test_cited_evidence_paths_must_exist(tmp_path: Path) -> None:
    (tmp_path / "exists_test.py").write_text("", encoding="utf-8")
    evidence = {
        "automated_tests": ["exists_test.py", "missing_test.py"],
        "artifacts": ["missing/file.csv"],
        "preview_checks": [],
    }

    errors = validate_release_evidence(
        {"sources": []}, {"claims": [_claim(evidence=evidence)]}, root_dir=tmp_path
    )

    assert errors == [
        (
            "Claim 'claim-example' cites automated_tests path that does not exist: "
            "'missing_test.py'."
        ),
        "Claim 'claim-example' cites artifacts path that does not exist: 'missing/file.csv'.",
    ]


def test_experimental_is_no_longer_a_claim_status() -> None:
    errors = validate_release_evidence(
        {"sources": []}, {"claims": [_claim(status="experimental")]}
    )

    assert any("invalid status 'experimental'" in error for error in errors)
