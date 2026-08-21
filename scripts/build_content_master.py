#!/usr/bin/env python3
"""Build a unified, metadata-rich content library from the existing TalksNWalks CSVs.

This script is intentionally build-only. It does not modify the legacy quote files,
select a live Instagram post, or publish anything.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

OUTPUT_FIELDS = [
    "ContentID",
    "Quote",
    "Audience",
    "PrimaryTopic",
    "SecondaryTopics",
    "Occasion",
    "Tone",
    "SourceType",
    "Author",
    "Source",
    "IllustrationTags",
    "Highlight",
    "Status",
    "UsedCount",
    "LastUsedDate",
    "Notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def clean(value: str | None) -> str:
    return (value or "").strip()


def split_csv_value(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = clean(item)
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_audience(value: str) -> str:
    raw = clean(value)
    replacements = {
        "Kids / Teens": "Kids|Teens",
        "Kids / Pre-teens": "Kids",
        "Pre-teens / Teens": "Kids|Teens",
        "Kids / Pre-teens / Teens": "Kids|Teens",
        "Kids / Pre-teens / Teens / Adults": "All",
    }
    if raw in replacements:
        return replacements[raw]
    if " / " in raw:
        parts = [part.strip() for part in raw.split("/")]
        normalized: list[str] = []
        for part in parts:
            if part in {"Pre-teens", "Children"}:
                part = "Kids"
            if part and part not in normalized:
                normalized.append(part)
        return "|".join(normalized)
    return raw or "All"


def load_topics() -> dict[str, dict[str, str]]:
    rows = read_csv(DATA / "topics.csv")
    return {clean(row["Topic"]): row for row in rows}


def load_mappings() -> dict[tuple[str, str], dict[str, str]]:
    rows = read_csv(DATA / "theme_mappings.csv")
    return {
        (clean(row["SourceLibrary"]), clean(row["SourceTheme"])): row
        for row in rows
    }


def keyword_topics(quote: str) -> list[str]:
    """Add useful secondary topics based on the quote itself.

    Legacy themes such as Lifestyle & Joy are broad. These lightweight hints make
    the future selector better without changing the original source files.
    """
    text = quote.lower()
    rules = [
        (("friend", "crew", "brotherhood"), "Friendship"),
        (("mother", "mom", "mum"), "Mother"),
        (("father", "dad"), "Father"),
        (("sister",), "Sisters"),
        (("brother", "sibling"), "Siblings"),
        (("family", "home"), "Family"),
        (("love", "relationship", "partner", "romance"), "Relationships"),
        (("marriage", "married"), "Marriage"),
        (("gym", "rep", "workout", "train", "protein", "fitness"), "Fitness"),
        (("rest", "sleep", "recovery"), "Rest & Recovery"),
        (("body", "healthy", "health"), "Health"),
        (("book", "read"), "Reading & Books"),
        (("music", "song", "dance", "headphone"), "Music & Dance"),
        (("trip", "travel", "beach", "roadtrip", "hike", "adventure"), "Travel & Adventure"),
        (("school", "study", "learn", "education", "teacher", "homework"), "Study & Learning"),
        (("fair", "justice", "equal", "equality", "rights"), "Justice & Equality"),
        (("kind", "kindness", "helping", "empathy"), "Kindness"),
        (("speak", "voice", "listen", "conversation", "communicat"), "Communication & Social Skills"),
        (("leader", "leadership", "team"), "Leadership"),
        (("ceo", "owner", "ownership", "business", "company", "brand"), "CEO Mindset"),
        (("startup", "entrepreneur", "build value", "customer"), "Entrepreneurship"),
        (("money", "wealth", "financial", "finances"), "Money Mindset"),
        (("strategy", "plan", "decision", "prepare", "preparation"), "Strategy & Decision-Making"),
        (("purpose", "meaning", "values"), "Purpose & Meaning"),
        (("truth", "honest", "integrity", "character"), "Integrity & Character"),
        (("yourself", "identity", "authentic", "approval"), "Authenticity & Identity"),
        (("phone", "internet", "online", "screenshot", "posting", "message"), "Digital Responsibility"),
    ]
    found: list[str] = []
    for needles, topic in rules:
        if any(needle in text for needle in needles):
            found.append(topic)
    return unique(found)


def mapped_metadata(
    library: str,
    theme: str,
    quote: str,
    topics: dict[str, dict[str, str]],
    mappings: dict[tuple[str, str], dict[str, str]],
) -> tuple[str, list[str], str, str, str]:
    key = (library, theme)
    if key not in mappings:
        raise KeyError(f"No theme mapping for {library!r} / {theme!r}")

    mapping = mappings[key]
    primary = clean(mapping["PrimaryTopic"])
    if primary not in topics:
        raise KeyError(f"Mapped primary topic {primary!r} is not in data/topics.csv")

    secondary = split_csv_value(clean(mapping.get("SecondaryTopics")))
    secondary.extend(keyword_topics(quote))
    secondary = [topic for topic in unique(secondary) if topic != primary and topic in topics]

    topic = topics[primary]
    tone = clean(topic.get("DefaultTone"))
    highlight = clean(topic.get("Highlight"))

    tag_sources = [clean(topic.get("IllustrationTags"))]
    for secondary_topic in secondary[:3]:
        tag_sources.append(clean(topics[secondary_topic].get("IllustrationTags")))
    tags: list[str] = []
    for source in tag_sources:
        tags.extend(split_csv_value(source))
    tags = unique(tags)

    return primary, secondary, tone, highlight, ",".join(tags)


def make_row(
    *,
    content_id: str,
    quote: str,
    audience: str,
    library: str,
    theme: str,
    source_type: str,
    author: str = "",
    source: str = "",
    notes: str = "",
    topics: dict[str, dict[str, str]],
    mappings: dict[tuple[str, str], dict[str, str]],
) -> dict[str, str]:
    primary, secondary, tone, highlight, tags = mapped_metadata(
        library, theme, quote, topics, mappings
    )
    return {
        "ContentID": content_id,
        "Quote": quote,
        "Audience": normalize_audience(audience),
        "PrimaryTopic": primary,
        "SecondaryTopics": ",".join(secondary),
        "Occasion": "",
        "Tone": tone,
        "SourceType": source_type,
        "Author": author,
        "Source": source,
        "IllustrationTags": tags,
        "Highlight": highlight,
        "Status": "approved",
        "UsedCount": "0",
        "LastUsedDate": "",
        "Notes": notes,
    }


def import_day_library(
    path: Path,
    library: str,
    prefix: str,
    audience: str,
    topics: dict[str, dict[str, str]],
    mappings: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source_row in read_csv(path):
        day = int(clean(source_row["Day"]))
        theme = clean(source_row["Theme"])
        quote = clean(source_row["Quote"])
        rows.append(
            make_row(
                content_id=f"{prefix}-{day:03d}",
                quote=quote,
                audience=audience,
                library=library,
                theme=theme,
                source_type="original",
                notes=f"Imported from {path.relative_to(ROOT).as_posix()}; legacy theme={theme}",
                topics=topics,
                mappings=mappings,
            )
        )
    return rows


def import_books(
    topics: dict[str, dict[str, str]], mappings: dict[tuple[str, str], dict[str, str]]
) -> list[dict[str, str]]:
    path = DATA / "references" / "books.csv"
    rows: list[dict[str, str]] = []
    for source_row in read_csv(path):
        item_id = int(clean(source_row["ID"]))
        theme = clean(source_row["Theme"])
        display = clean(source_row.get("DisplayAttribution"))
        rows.append(
            make_row(
                content_id=f"BOOK-{item_id:03d}",
                quote=clean(source_row["Quote"]),
                audience=clean(source_row.get("Audience")) or "All",
                library="books",
                theme=theme,
                source_type=clean(source_row.get("Type")) or "inspired_by",
                author=clean(source_row.get("Author")),
                source=clean(source_row.get("Source")),
                notes=f"{display}; legacy theme={theme}" if display else f"legacy theme={theme}",
                topics=topics,
                mappings=mappings,
            )
        )
    return rows


def import_leaders(
    topics: dict[str, dict[str, str]], mappings: dict[tuple[str, str], dict[str, str]]
) -> list[dict[str, str]]:
    path = DATA / "references" / "leaders_classics.csv"
    rows: list[dict[str, str]] = []
    for source_row in read_csv(path):
        item_id = int(clean(source_row["ID"]))
        theme = clean(source_row["Theme"])
        verification = clean(source_row.get("VerificationStatus"))
        source_url = clean(source_row.get("SourceURL"))
        notes = f"verification={verification}; legacy theme={theme}"
        if source_url:
            notes += f"; source_url={source_url}"
        rows.append(
            make_row(
                content_id=f"CLASSIC-{item_id:03d}",
                quote=clean(source_row["Quote"]),
                audience=clean(source_row.get("Audience")) or "All",
                library="leaders",
                theme=theme,
                source_type=clean(source_row.get("Type")) or "inspired_by",
                author=clean(source_row.get("Author")),
                source=clean(source_row.get("Source")),
                notes=notes,
                topics=topics,
                mappings=mappings,
            )
        )
    return rows


def import_kids_morals(
    topics: dict[str, dict[str, str]], mappings: dict[tuple[str, str], dict[str, str]]
) -> list[dict[str, str]]:
    path = DATA / "references" / "kids_morals.csv"
    rows: list[dict[str, str]] = []
    for source_row in read_csv(path):
        item_id = int(clean(source_row["ID"]))
        theme = clean(source_row["Theme"])
        rows.append(
            make_row(
                content_id=f"MORAL-{item_id:03d}",
                quote=clean(source_row["Quote"]),
                audience=clean(source_row.get("AgeGroup")) or "Kids|Teens",
                library="kids_morals",
                theme=theme,
                source_type=clean(source_row.get("Type")) or "original_moral",
                notes=f"Imported from kids morals; legacy theme={theme}",
                topics=topics,
                mappings=mappings,
            )
        )
    return rows


def build_master(output_path: Path) -> list[dict[str, str]]:
    topics = load_topics()
    mappings = load_mappings()

    rows: list[dict[str, str]] = []
    rows.extend(import_day_library(DATA / "quotes.csv", "women", "WOMEN", "Women", topics, mappings))
    rows.extend(import_day_library(DATA / "men" / "quotes.csv", "men", "MEN", "Men", topics, mappings))
    rows.extend(import_day_library(DATA / "children" / "quotes.csv", "children", "CHILD", "Kids|Teens", topics, mappings))
    rows.extend(import_books(topics, mappings))
    rows.extend(import_leaders(topics, mappings))
    rows.extend(import_kids_morals(topics, mappings))

    ids = [row["ContentID"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate ContentID values were generated")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(DATA / "generated" / "content_master.csv"),
        help="Where to write the generated master CSV",
    )
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    rows = build_master(output)
    print(f"Built {len(rows)} unified content rows -> {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
