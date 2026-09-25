import re
from pathlib import Path

import yaml

from tools.quality.validate_release_signoff import validate_release_signoff

ROOT = Path(__file__).resolve().parents[3]
SIGNOFF_PATH = ROOT / "docs" / "product" / "release" / "release-signoff.yaml"
RELEASE_DIR = ROOT / "docs" / "product" / "release"


def test_release_signoff_is_valid() -> None:
    assert SIGNOFF_PATH.exists(), f"Missing release sign-off at {SIGNOFF_PATH}"
    for doc in [
        "product-acceptance.md",
        "known-limitations.md",
        "submission-checklist.md",
    ]:
        assert (RELEASE_DIR / doc).exists(), f"Missing required release document: {doc}"

    data = yaml.safe_load(SIGNOFF_PATH.read_text(encoding="utf-8"))
    errors = validate_release_signoff(data, root_dir=ROOT)
    assert errors == [], f"Release signoff validation errors: {errors}"


def test_tested_source_sha_format() -> None:
    data = yaml.safe_load(SIGNOFF_PATH.read_text(encoding="utf-8"))
    sha = data.get("tested_source_sha")
    assert sha is None or re.fullmatch(r"[0-9a-f]{40}", sha), (
        f"Invalid commit SHA: '{sha}'"
    )


def test_no_go_may_have_no_tested_commit() -> None:
    data = yaml.safe_load(SIGNOFF_PATH.read_text(encoding="utf-8"))
    data["decision"] = "no-go"
    data["tested_source_sha"] = None
    assert validate_release_signoff(data, root_dir=ROOT) == []


def test_nonexistent_tested_commit_is_rejected() -> None:
    data = yaml.safe_load(SIGNOFF_PATH.read_text(encoding="utf-8"))
    data["tested_source_sha"] = "0" * 40
    errors = validate_release_signoff(data, root_dir=ROOT)
    assert any("not a resolvable Git commit" in error for error in errors)


def test_go_decision_has_all_passing_gates_and_approvals_or_owner_override() -> None:
    data = yaml.safe_load(SIGNOFF_PATH.read_text(encoding="utf-8"))
    decision = data.get("decision")
    assert decision in ["go", "no-go"], f"Invalid decision: '{decision}'"

    if decision == "go":
        gates = data.get("quality_gates", {})
        for gate_name, gate_info in gates.items():
            assert gate_info.get("status") == "passed", (
                f"Quality gate '{gate_name}' is not passed"
            )

        reviews = data.get("member_approvals", {})
        for m_idx in range(1, 6):
            member_key = f"member_{m_idx}"
            assert member_key in reviews, f"Missing approval for '{member_key}'"
        assert (
            all(reviews[key].get("status") == "approved" for key in reviews)
            or data.get("owner_override", {}).get("approved") is True
        )


def test_go_rejects_pending_members_without_owner_override() -> None:
    data = yaml.safe_load(SIGNOFF_PATH.read_text(encoding="utf-8"))
    data["decision"] = "go"
    data.pop("owner_override", None)
    data["member_approvals"]["member_1"]["status"] = "pending_review"
    assert any("member_1" in error for error in validate_release_signoff(data))


def test_go_rejects_incomplete_owner_override() -> None:
    data = yaml.safe_load(SIGNOFF_PATH.read_text(encoding="utf-8"))
    data["decision"] = "go"
    data["owner_override"]["approver"] = ""
    assert any("owner_override" in error for error in validate_release_signoff(data))
