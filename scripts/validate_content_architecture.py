#!/usr/bin/env python3
"""Validate the data-driven content architecture without publishing anything."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_content_master import build_master  # noqa: E402


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def clean(value: str | None) -> str:
    return (value or "").strip()


def main() -> None:
    topic_rows = read_csv(DATA / "topics.csv")
    topics = {clean(row["Topic"]) for row in topic_rows}
    mapping_rows = read_csv(DATA / "theme_mappings.csv")
    mappings = {
        (clean(row["SourceLibrary"]), clean(row["SourceTheme"])): row
        for row in mapping_rows
    }

    sources = {
        "women": DATA / "quotes.csv",
        "men": DATA / "men" / "quotes.csv",
        "children": DATA / "children" / "quotes.csv",
        "books": DATA / "references" / "books.csv",
        "leaders": DATA / "references" / "leaders_classics.csv",
        "kids_morals": DATA / "references" / "kids_morals.csv",
    }

    missing: list[str] = []
    for library, path in sources.items():
        rows = read_csv(path)
        theme_field = "Theme"
        themes = {clean(row[theme_field]) for row in rows}
        for theme in sorted(themes):
            if (library, theme) not in mappings:
                missing.append(f"{library}: {theme}")

    if missing:
        raise SystemExit("Unmapped source themes:\n- " + "\n- ".join(missing))

    unknown_topics: list[str] = []
    for row in mapping_rows:
        primary = clean(row["PrimaryTopic"])
        if primary not in topics:
            unknown_topics.append(f"primary: {primary}")
        for secondary in [part.strip() for part in row["SecondaryTopics"].split(",") if part.strip()]:
            if secondary not in topics:
                unknown_topics.append(f"secondary: {secondary}")
    if unknown_topics:
        raise SystemExit("Mappings reference unknown topics:\n- " + "\n- ".join(sorted(set(unknown_topics))))

    expected_rows = sum(len(read_csv(path)) for path in sources.values())
    output = DATA / "generated" / "content_master.csv"
    master = build_master(output)
    if len(master) != expected_rows:
        raise SystemExit(f"Generated {len(master)} rows but source files contain {expected_rows} rows")

    ids = [row["ContentID"] for row in master]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate ContentID values found")
    if any(not clean(row["Quote"]) for row in master):
        raise SystemExit("Blank quote found in generated content master")
    if any(clean(row["PrimaryTopic"]) not in topics for row in master):
        raise SystemExit("Generated row contains an unknown primary topic")

    print(f"Topics: {len(topics)}")
    print(f"Theme mappings: {len(mappings)}")
    print(f"Source rows mapped: {expected_rows}")
    print(f"Generated master rows: {len(master)}")
    print("Content architecture validation passed.")


if __name__ == "__main__":
    main()
