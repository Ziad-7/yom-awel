"""Create real-evaluator uploads when the later presenter-kit PR is not merged yet."""

import csv
import io
import sys
from pathlib import Path

from yom_awel.evaluation.catalog import csv_to_xlsx
from yom_awel.evaluation.clean_sales_dataset import (
    LEARNER_SEED,
    apply_defects,
    generate,
    to_csv,
)


def generate_files(destination: Path) -> None:
    data = generate(LEARNER_SEED)
    clean = to_csv(data.clean).encode()
    duplicate_rows = apply_defects(
        data.clean,
        [defect for defect in data.defects if defect.kind == "duplicate_order"],
    )
    half_rows = apply_defects(
        data.clean,
        [
            defect
            for defect in data.defects
            if defect.kind in {"nonstandard_date", "missing_email"}
        ],
    )
    output = io.StringIO()
    columns = [column for column in data.clean[0] if column != "missing_email_reason"]
    writer = csv.DictWriter(
        output, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(data.clean)
    files = {
        "sales_cleaned.csv": clean,
        "sales_cleaned.xlsx": csv_to_xlsx(clean),
        "sales_retry_duplicates.csv": to_csv(duplicate_rows).encode(),
        "sales_retry_half.xlsx": csv_to_xlsx(to_csv(half_rows).encode()),
        "sales_rejected_missing_columns.csv": output.getvalue().encode(),
    }
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (destination / name).write_bytes(content)


if __name__ == "__main__":
    generate_files(Path(sys.argv[1]))
