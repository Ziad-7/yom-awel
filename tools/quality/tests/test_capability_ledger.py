from pathlib import Path

import yaml

from tools.quality.validate_capability_ledger import validate_ledger


ROOT = Path(__file__).resolve().parents[3]


def test_capability_ledger_is_complete() -> None:
    ledger = yaml.safe_load(
        (ROOT / "docs/product/capability-ledger.yaml").read_text(encoding="utf-8")
    )
    errors = validate_ledger(ledger)
    assert errors == []


def test_current_capabilities_name_test_and_preview_evidence() -> None:
    ledger = yaml.safe_load(
        (ROOT / "docs/product/capability-ledger.yaml").read_text(encoding="utf-8")
    )
    for capability in ledger["capabilities"]:
        if capability["status"] == "current":
            assert capability["evidence"]["automated_tests"]
            assert capability["evidence"]["preview_checks"]
