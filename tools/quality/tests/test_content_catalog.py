import re
from pathlib import Path

import yaml

from tools.quality.validate_content_catalog import validate_content_catalog


ROOT = Path(__file__).resolve().parents[3]
COPY_PATH = ROOT / "docs" / "product" / "content" / "interface-copy.yaml"
GLOSSARY_PATH = ROOT / "docs" / "product" / "content" / "glossary.yaml"


def test_content_catalog_is_valid() -> None:
    assert COPY_PATH.exists(), f"Missing interface copy at {COPY_PATH}"
    assert GLOSSARY_PATH.exists(), f"Missing glossary at {GLOSSARY_PATH}"

    copy_data = yaml.safe_load(COPY_PATH.read_text(encoding="utf-8"))
    glossary_data = yaml.safe_load(GLOSSARY_PATH.read_text(encoding="utf-8"))

    errors = validate_content_catalog(copy_data, glossary_data)
    assert errors == [], f"Validation errors: {errors}"


def test_interface_copy_covers_all_required_states() -> None:
    copy_data = yaml.safe_load(COPY_PATH.read_text(encoding="utf-8"))
    messages = copy_data.get("messages", {})

    required_state_keys = [
        "loading",
        "empty",
        "success",
        "failure",
        "retryable",
        "offline",
        "unsupported_file",
        "oversized_file",
        "evaluation_failed",
        "fallback_feedback",
    ]

    for state_key in required_state_keys:
        assert any(
            state_key in msg_id for msg_id in messages
        ), f"Missing coverage for state '{state_key}' in interface-copy.yaml"


def test_placeholder_parity_across_languages() -> None:
    copy_data = yaml.safe_load(COPY_PATH.read_text(encoding="utf-8"))
    messages = copy_data.get("messages", {})

    placeholder_regex = re.compile(r"\{([a-zA-Z0-9_]+)\}")

    for msg_id, entry in messages.items():
        ar_text = entry.get("ar-EG", "")
        en_text = entry.get("en", "")

        ar_placeholders = set(placeholder_regex.findall(ar_text))
        en_placeholders = set(placeholder_regex.findall(en_text))

        assert (
            ar_placeholders == en_placeholders
        ), f"Placeholder mismatch in message '{msg_id}': ar={ar_placeholders} vs en={en_placeholders}"
