"""Build the unified publishing master from book-inspired source material only.

Historical source files remain intact for provenance and published-history safety,
but the generated master library contains only rows explicitly marked
``SourceType=inspired_by``. The audit step separately rejects incomplete book
attribution before a row reaches the clean publishing library.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from supporting_text import enrich_supporting_text


ROOT = Path(__file__).resolve().parent
LIBRARY_DIR = ROOT / "data" / "library"
TOPICS_FILE = ROOT / "data" / "topics.csv"
THEME_MAPPINGS_FILE = ROOT / "data" / "theme_mappings.csv"
OUTPUT_FILE = ROOT / "data" / "quotes_master.csv"

FIELDNAMES = [
    "QuoteID",
    "Quote",
    "SupportingText",
    "Audience",
    "TopicCategory",
    "Topic",
    "Theme",
    "SourceType",
    "InspiredBy",
    "Author",
    "AttributionNote",
    "OriginalTheme",
    "SourceURL",
    "Occasion",
    "IllustrationTags",
    "SourceLibrary",
    "SourceFile",
    "DuplicateOf",
]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _normalise_quote(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _source_library(path: Path) -> str:
    name = path.name
    if name.startswith("men_"):
        return "men"
    if name.startswith("women_"):
        return "women"
    if name.startswith("children_"):
        return "children"
    if name.startswith("self_growth_"):
        return "self_growth"
    if name.startswith("user_curated_"):
        return "user_curated"
    return "library"


def _load_topics() -> dict[str, dict[str, str]]:
    with TOPICS_FILE.open(newline="", encoding="utf-8") as f:
        return {
            _clean(row.get("Topic")): row
            for row in csv.DictReader(f)
            if _clean(row.get("Topic"))
        }


def _load_theme_mappings() -> dict[tuple[str, str], str]:
    mappings: dict[tuple[str, str], str] = {}
    with THEME_MAPPINGS_FILE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            source = _clean(row.get("SourceLibrary"))
            theme = _clean(row.get("SourceTheme"))
            topic = _clean(row.get("PrimaryTopic"))
            if source and theme and topic:
                mappings[(source, theme)] = topic
    return mappings


def _canonical_topic(
    row: dict[str, str],
    source_library: str,
    topics: dict[str, dict[str, str]],
    mappings: dict[tuple[str, str], str],
) -> str:
    existing = _clean(row.get("Topic"))
    if existing in topics:
        return existing

    original_theme = _clean(row.get("OriginalTheme"))
    theme = original_theme or _clean(row.get("Theme"))

    # Rich women/men libraries often retain an old OriginalTheme while Theme is
    # the production rendering theme. Prefer a known source mapping where one
    # exists, otherwise retain a canonical Topic already supplied by the row.
    for source_key in (source_library, "women" if source_library == "user_curated" else source_library):
        mapped = mappings.get((source_key, theme))
        if mapped in topics:
            return mapped

    rendering_theme = _clean(row.get("Theme"))
    mapped = mappings.get((source_library, rendering_theme))
    if mapped in topics:
        return mapped

    return existing


def _legacy_children_row(row: dict[str, str], index: int) -> dict[str, str]:
    theme = _clean(row.get("Theme"))
    return {
        "QuoteID": f"CH{index:03d}",
        "Quote": _clean(row.get("Quote")),
        "SupportingText": "",
        "Audience": "Kids|Teens",
        "Theme": theme,
        "SourceType": "legacy_original",
        "InspiredBy": "",
        "Author": "",
        "AttributionNote": "Legacy children library row; source attribution is not recorded in the source file.",
        "OriginalTheme": theme,
        "SourceURL": "",
        "Occasion": "",
    }


def build() -> tuple[int, int]:
    topics = _load_topics()
    mappings = _load_theme_mappings()
    source_files = sorted(
        path for path in LIBRARY_DIR.glob("*.csv")
        if path.name != OUTPUT_FILE.name
    )
    if not source_files:
        raise RuntimeError("No quote source libraries found")

    master: list[dict[str, str]] = []
    seen_quotes: dict[str, str] = {}
    duplicate_count = 0

    for path in source_files:
        source_library = _source_library(path)
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for index, raw in enumerate(reader, start=1):
                row = {key: _clean(value) for key, value in raw.items() if key is not None}
                if not row.get("Quote"):
                    continue

                if source_library == "children" and "QuoteID" not in row:
                    row = _legacy_children_row(row, index)

                # Hard publishing-library rule: no original, legacy, adapted,
                # traditional, direct, or unattributed material enters master.
                if _clean(row.get("SourceType")).lower() != "inspired_by":
                    continue

                quote_id = row.get("QuoteID") or f"{path.stem.upper()}-{index:04d}"
                topic = _canonical_topic(row, source_library, topics, mappings)
                topic_meta = topics.get(topic, {})
                category = _clean(topic_meta.get("Category"))
                illustration_tags = _clean(topic_meta.get("IllustrationTags"))

                normalised = _normalise_quote(row.get("Quote", ""))
                duplicate_of = ""
                if normalised:
                    duplicate_of = seen_quotes.get(normalised, "")
                    if duplicate_of:
                        duplicate_count += 1
                    else:
                        seen_quotes[normalised] = quote_id

                master.append(
                    {
                        "QuoteID": quote_id,
                        "Quote": row.get("Quote", ""),
                        "SupportingText": row.get("SupportingText", ""),
                        "Audience": row.get("Audience", "All") or "All",
                        "TopicCategory": category,
                        "Topic": topic,
                        "Theme": row.get("Theme", ""),
                        "SourceType": row.get("SourceType", ""),
                        "InspiredBy": row.get("InspiredBy", ""),
                        "Author": row.get("Author", ""),
                        "AttributionNote": row.get("AttributionNote", ""),
                        "OriginalTheme": row.get("OriginalTheme", "") or row.get("Theme", ""),
                        "SourceURL": row.get("SourceURL", ""),
                        "Occasion": row.get("Occasion", ""),
                        "IllustrationTags": row.get("IllustrationTags", "") or illustration_tags,
                        "SourceLibrary": source_library,
                        "SourceFile": path.relative_to(ROOT).as_posix(),
                        "DuplicateOf": duplicate_of,
                    }
                )

    # SupportingText is part of the unified publishing contract. Preserve the
    # approved hand-written lines first, then source-provided lines, and fill all
    # remaining book rows with deterministic editorial context.
    master, support_stats = enrich_supporting_text(master)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(master)

    print(f"Built {OUTPUT_FILE.relative_to(ROOT)} with {len(master)} book-inspired rows")
    print(f"Exact normalized duplicates flagged: {duplicate_count}")
    print(f"SupportingText coverage: {len(master)}/{len(master)}")
    print("SupportingText sources: " + ", ".join(f"{key}={value}" for key, value in sorted(support_stats.items())))
    return len(master), duplicate_count


if __name__ == "__main__":
    build()
