"""Regenerate the presenter kit: graded uploads derived from the learner's own dirty file.

Usage: uv run --project services/api python demo/generate_demo_files.py [OUT]
OUT defaults to demo/files. Every file is byte-for-byte reproducible.

The builders live in ``yom_awel.evaluation.samples`` so judge mode serves the same files.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from yom_awel.evaluation.clean_sales_dataset import LEARNER_SEED, Dataset, generate
from yom_awel.evaluation.samples import SALES_FILES

OUTPUT_DIR = Path(__file__).resolve().parent / "files"
DEMO_FILES = SALES_FILES


def build_all(dataset: Dataset) -> dict[str, bytes]:
    return {name: build(dataset) for name, build in DEMO_FILES.items()}


def write_all(out_dir: Path, files: Mapping[str, bytes]) -> Sequence[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / name for name in files]
    for path, content in zip(paths, files.values(), strict=True):
        path.write_bytes(content)
    return paths


def main(out_dir: Path) -> None:
    for path in write_all(out_dir, build_all(generate(LEARNER_SEED))):
        print(path)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_DIR)
