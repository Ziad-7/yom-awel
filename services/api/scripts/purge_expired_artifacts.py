"""Bounded retention entry point.

Cloud credentials and a repository factory are intentionally injected by the
deployment composition root.  With no backend configured this command is a
safe no-op, which is what the free, local-only CI workflow runs.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purge expired submission artifacts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    mode = "dry-run" if args.dry_run else "manual/no-op"
    print(f"retention cleanup {mode}: no backend configured; no objects deleted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
