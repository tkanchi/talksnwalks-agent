"""Audit the shared Talk N Walks illustration library.

Usage:
    python illustration_inventory.py
    python illustration_inventory.py --output outputs/illustration_inventory.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from illustration_pool import audit_illustrations, write_inventory_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("illustrations"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/illustration_inventory.csv"),
    )
    args = parser.parse_args()

    report = audit_illustrations(args.directory)
    output = write_inventory_csv(args.directory, args.output)

    print(f"Illustrations: {report['total_pngs']} PNGs")
    print(f"Valid filenames: {report['valid_pngs']}")
    print(f"Invalid filenames: {len(report['invalid_names'])}")
    print(f"Exact duplicate groups: {len(report['duplicate_groups'])}")

    print("Audience counts:")
    for key, value in report["audience_counts"].items():
        print(f"  {key}: {value}")

    print("Topic-tag counts:")
    for key, value in report["topic_counts"].items():
        print(f"  {key}: {value}")

    if report["invalid_names"]:
        print("Invalid names:")
        for name in report["invalid_names"]:
            print(f"  {name}")

    if report["duplicate_groups"]:
        print("Exact duplicates:")
        for names in report["duplicate_groups"]:
            print("  " + " == ".join(names))

    print(f"Inventory CSV: {output}")


if __name__ == "__main__":
    main()
