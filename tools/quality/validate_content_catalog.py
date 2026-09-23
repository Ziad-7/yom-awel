"""Validator for interface copy catalog and bilingual glossary."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

PLACEHOLDER_REGEX = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def validate_content_catalog(
    copy_data: dict[str, Any], glossary_data: dict[str, Any]
) -> list[str]:
    """Validate interface copy catalog and glossary consistency.

    Returns a list of error strings. Empty list indicates full validity.
    """
    errors: list[str] = []

    # 1. Validate copy catalog
    if not isinstance(copy_data, dict):
        return ["Interface copy catalog must be a YAML dictionary."]

    messages = copy_data.get("messages")
    if not isinstance(messages, dict) or len(messages) == 0:
        errors.append("Interface copy must contain a non-empty 'messages' dictionary.")
    else:
        for msg_id, entry in messages.items():
            if not isinstance(entry, dict):
                errors.append(f"Message '{msg_id}' must be a dictionary.")
                continue

            ar_text = entry.get("ar-EG")
            if not ar_text or not isinstance(ar_text, str) or not ar_text.strip():
                errors.append(f"Message '{msg_id}' is missing valid 'ar-EG' text.")

            en_text = entry.get("en")
            if not en_text or not isinstance(en_text, str) or not en_text.strip():
                errors.append(f"Message '{msg_id}' is missing valid 'en' text.")

            acc_label = entry.get("accessible_label")
            if not acc_label or not isinstance(acc_label, str) or not acc_label.strip():
                errors.append(
                    f"Message '{msg_id}' is missing valid 'accessible_label'."
                )

            if ar_text and en_text:
                ar_vars = set(PLACEHOLDER_REGEX.findall(ar_text))
                en_vars = set(PLACEHOLDER_REGEX.findall(en_text))
                if ar_vars != en_vars:
                    errors.append(
                        f"Placeholder mismatch in message '{msg_id}': ar={ar_vars} vs en={en_vars}."
                    )

    # 2. Validate glossary
    if not isinstance(glossary_data, dict):
        errors.append("Glossary must be a YAML dictionary.")
    else:
        terms = glossary_data.get("terms")
        if not isinstance(terms, list) or len(terms) == 0:
            errors.append("Glossary must contain a non-empty 'terms' list.")
        else:
            seen_term_ids: set[str] = set()
            for idx, term in enumerate(terms):
                if not isinstance(term, dict):
                    errors.append(f"Glossary term at index {idx} must be a dictionary.")
                    continue

                term_id = term.get("id")
                if not term_id or not isinstance(term_id, str):
                    errors.append(f"Glossary term at index {idx} is missing 'id'.")
                elif term_id in seen_term_ids:
                    errors.append(f"Duplicate glossary term id: '{term_id}'.")
                else:
                    seen_term_ids.add(term_id)

                if not term.get("en") or not term.get("ar_preferred"):
                    errors.append(
                        f"Glossary term '{term_id or idx}' missing 'en' or 'ar_preferred'."
                    )

                if not term.get("definition"):
                    errors.append(
                        f"Glossary term '{term_id or idx}' missing 'definition'."
                    )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    copy_path = root / "docs" / "product" / "content" / "interface-copy.yaml"
    glossary_path = root / "docs" / "product" / "content" / "glossary.yaml"

    if len(sys.argv) > 1:
        copy_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        glossary_path = Path(sys.argv[2])

    if not copy_path.exists():
        print(f"Error: Interface copy not found at {copy_path}", file=sys.stderr)
        return 1

    if not glossary_path.exists():
        print(f"Error: Glossary not found at {glossary_path}", file=sys.stderr)
        return 1

    try:
        copy_data = yaml.safe_load(copy_path.read_text(encoding="utf-8"))
        glossary_data = yaml.safe_load(glossary_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        print(f"Error reading YAML files: {exc}", file=sys.stderr)
        return 1

    errors = validate_content_catalog(copy_data, glossary_data)
    if errors:
        print(
            f"FAILED: Found {len(errors)} error(s) in content catalog:", file=sys.stderr
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"SUCCESS: Interface copy and glossary at {copy_path} and {glossary_path} are valid."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
