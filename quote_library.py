"""Build the legacy Day/Quote/Theme runtime CSV from segmented quote libraries."""

from __future__ import annotations

import csv
from pathlib import Path


def build_runtime_quote_file(parts: list[Path], destination: Path) -> Path:
    """Combine ordered source libraries without discarding their richer metadata."""
    rows: list[dict[str, str]] = []

    for part in parts:
        if not part.exists():
            raise FileNotFoundError(f"Missing quote library part: {part}")
        with part.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = set(reader.fieldnames or [])
            if not {"Quote", "Theme"}.issubset(fieldnames):
                raise ValueError(f"{part} must contain Quote and Theme columns")
            rows.extend(reader)

    if not rows:
        raise ValueError("Quote library is empty")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Day", "Quote", "Theme"])
        writer.writeheader()
        for day, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "Day": day,
                    "Quote": row["Quote"].strip(),
                    "Theme": row["Theme"].strip(),
                }
            )

    return destination
