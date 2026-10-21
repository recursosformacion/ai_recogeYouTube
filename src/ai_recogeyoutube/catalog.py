"""Import a safe, minimal CSV export of works from OSAP."""

import csv
from pathlib import Path

from .db import upsert_work
from .models import WorkRecord


def _split(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").split("|") if part.strip()]


def import_catalog_csv(csv_path: Path, db_path: Path) -> int:
    """Import CSV columns: work_id,title; optional composers,alternate_titles,catalog_numbers,languages,formation.

    Multi-value fields use | as a separator. The importer never connects to OSAP.
    """
    imported = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"work_id", "title"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must include work_id and title columns")
        for line_number, row in enumerate(reader, start=2):
            if not (row.get("work_id") or "").strip():
                raise ValueError(f"Missing work_id on CSV line {line_number}")
            if not (row.get("title") or "").strip():
                raise ValueError(f"Missing title on CSV line {line_number}")
            work = WorkRecord(
                work_id=row["work_id"].strip(),
                title=row["title"].strip(),
                composers=_split(row.get("composers")),
                alternate_titles=_split(row.get("alternate_titles")),
                catalog_numbers=_split(row.get("catalog_numbers")),
                languages=_split(row.get("languages")),
                formation=(row.get("formation") or "").strip() or None,
            )
            upsert_work(db_path, work)
            imported += 1
    return imported
