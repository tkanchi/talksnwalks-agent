"""Build stable runtime quote pools from the full Talk N Walks libraries.

The source libraries stay complete and attribution-rich. Production builders get a
smaller, deduplicated, higher-impact sequence with topic variety so we do not post
hundreds of same-category quotes in blocks.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from quote_text_quality import polish_quote_row


def _load_rows(parts: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for part in parts:
        if not part.exists():
            raise FileNotFoundError(f"Missing quote library part: {part}")
        with part.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = set(reader.fieldnames or [])
            if not {"Quote", "Theme"}.issubset(fieldnames):
                raise ValueError(f"{part} must contain Quote and Theme columns")
            rows.extend(polish_quote_row(dict(row)) for row in reader)
    return rows


def _normalise_quote(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _impact_score(row: dict[str, str], source_weights: dict[str, int] | None = None) -> int:
    """Deterministic social-content score; not an engagement guarantee."""
    quote = row.get("Quote", "").strip()
    lower = quote.lower()
    words = re.findall(r"\b[\w’'-]+\b", quote)
    word_count = len(words)
    char_count = len(quote)
    score = 0

    if 6 <= word_count <= 14:
        score += 18
    elif 15 <= word_count <= 18:
        score += 10
    elif 19 <= word_count <= 22:
        score += 3
    elif word_count < 5:
        score -= 5
    else:
        score -= 8

    if 35 <= char_count <= 85:
        score += 15
    elif 86 <= char_count <= 110:
        score += 7
    elif char_count > 135:
        score -= 12
    elif char_count < 25:
        score -= 3

    strong_terms = (
        "stop ", "choose ", "protect ", "build ", "leave ", "trust ",
        "start ", "keep ", "become ", "move ", "rest ", "love ",
        "discipline", "standards", "peace", "confidence", "future", "habits",
        "worth", "courage", "dream", "respect", "attention", "energy",
        "freedom", "strong", "money", "wealth", "success", "healing",
        "boundary", "boundaries",
    )
    score += min(12, sum(2 for term in strong_terms if term in lower))

    contrast_terms = (" not ", " but ", " instead ", " until ", " without ", ";")
    padded = f" {lower} "
    score += min(6, sum(2 for term in contrast_terms if term in padded))

    if "your" in lower or "you " in lower:
        score += 4
    if lower.startswith((
        "stop ", "choose ", "protect ", "build ", "start ", "keep ",
        "let ", "be ",
    )):
        score += 5

    # Negative commands can be powerful occasionally, but rewarding them as a
    # default caused too many early production quotes to begin with "Do not",
    # "Don't", or "Never". Keep those quotes in the library while lowering their
    # ranking enough to create more natural opening variety.
    if lower.startswith(("do not ", "don't ", "don’t ", "never ")):
        score -= 8

    for term in (
        "organization", "stakeholder", "performance system", "framework",
        "operating model", "productivity system",
    ):
        if term in lower:
            score -= 5

    quote_id = row.get("QuoteID", "")
    for prefix, weight in (source_weights or {}).items():
        if quote_id.startswith(prefix):
            score += weight
            break

    if row.get("SourceType", "").strip() == "original":
        score += 5
    elif row.get("SourceType", "").strip() == "inspired_by":
        score -= 2

    return score


def _write_runtime(rows: list[dict[str, str]], destination: Path) -> Path:
    if not rows:
        raise ValueError("Quote pool is empty")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Day", "Quote", "Theme", "QuoteID", "Topic", "SourceType"],
        )
        writer.writeheader()
        for day, row in enumerate(rows, start=1):
            row = polish_quote_row(row)
            writer.writerow(
                {
                    "Day": day,
                    "Quote": row.get("Quote", "").strip(),
                    "Theme": row.get("Theme", "").strip(),
                    "QuoteID": row.get("QuoteID", "").strip(),
                    "Topic": row.get("Topic", "").strip(),
                    "SourceType": row.get("SourceType", "").strip(),
                }
            )
    return destination


def build_runtime_quote_file(parts: list[Path], destination: Path) -> Path:
    """Legacy ordered concatenation, kept for backward compatibility."""
    rows = _load_rows(parts)
    return _write_runtime(rows, destination)


def build_curated_runtime_quote_file(
    parts: list[Path],
    destination: Path,
    *,
    target_days: int = 365,
    legacy_prefixes: tuple[str, ...] = (),
    exclude_prefixes: tuple[str, ...] = (),
    source_weights: dict[str, int] | None = None,
    required_source_type: str | None = None,
    require_book_author: bool = False,
) -> Path:
    """Create a varied high-impact pool, with optional source/attribution filters."""
    raw_rows = _load_rows(parts)

    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for row in raw_rows:
        quote_id = row.get("QuoteID", "")
        if any(quote_id.startswith(prefix) for prefix in exclude_prefixes):
            continue
        source_type = row.get("SourceType", "").strip()
        if required_source_type and source_type != required_source_type:
            continue
        if require_book_author:
            book = row.get("InspiredBy", "").strip()
            author = row.get("Author", "").strip()
            if not book or not author:
                continue
        quote = row.get("Quote", "").strip()
        normalised = _normalise_quote(quote)
        if not normalised or normalised in seen:
            continue
        seen.add(normalised)
        rows.append(row)

    preserved = [
        row for row in rows
        if any(row.get("QuoteID", "").startswith(prefix) for prefix in legacy_prefixes)
    ]
    preserved.sort(key=lambda row: row.get("QuoteID", ""))
    preserved_ids = {row.get("QuoteID", "") for row in preserved}

    candidates = [row for row in rows if row.get("QuoteID", "") not in preserved_ids]
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        row = dict(row)
        row["_score"] = str(_impact_score(row, source_weights))
        key = row.get("Topic", "").strip() or row.get("Theme", "").strip() or "Other"
        groups[key].append(row)

    for group in groups.values():
        group.sort(key=lambda row: (-int(row["_score"]), row.get("QuoteID", "")))

    topic_order = sorted(
        groups,
        key=lambda topic: (
            -max(int(row["_score"]) for row in groups[topic]),
            topic,
        ),
    )

    selected = list(preserved)
    cursor = 0
    while len(selected) < target_days and any(groups[topic] for topic in topic_order):
        topic = topic_order[cursor % len(topic_order)]
        if groups[topic]:
            row = groups[topic].pop(0)
            row.pop("_score", None)
            selected.append(row)
        cursor += 1

    return _write_runtime(selected[:target_days], destination)


def build_curated_simple_quote_file(
    source: Path,
    destination: Path,
    *,
    preserve_days: int = 0,
) -> Path:
    """Curate a simple quote source into a varied runtime pool."""
    with source.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    preserved = rows[:preserve_days]
    candidates = rows[preserve_days:]
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for index, row in enumerate(candidates, start=preserve_days + 1):
        enriched = dict(row)
        enriched["QuoteID"] = row.get("QuoteID", "") or row.get("ID", "") or f"CH{index:03d}"
        enriched["Topic"] = row.get("Topic", "") or row.get("Theme", "")
        enriched["SourceType"] = row.get("SourceType", "") or row.get("Type", "") or "original"
        enriched = polish_quote_row(enriched)
        enriched["_score"] = str(_impact_score(enriched))
        groups[row.get("Theme", "Other")].append(enriched)

    for group in groups.values():
        group.sort(key=lambda row: (-int(row["_score"]), row.get("QuoteID", "")))

    theme_order = sorted(
        groups,
        key=lambda theme: -max(int(row["_score"]) for row in groups[theme]),
    )
    selected: list[dict[str, str]] = []
    for index, row in enumerate(preserved, start=1):
        enriched = {
            **row,
            "QuoteID": row.get("QuoteID", "") or row.get("ID", "") or f"CH{index:03d}",
            "Topic": row.get("Topic", "") or row.get("Theme", ""),
            "SourceType": row.get("SourceType", "") or row.get("Type", "") or "original",
        }
        selected.append(polish_quote_row(enriched))

    cursor = 0
    while any(groups[theme] for theme in theme_order):
        theme = theme_order[cursor % len(theme_order)]
        if groups[theme]:
            row = groups[theme].pop(0)
            row.pop("_score", None)
            selected.append(row)
        cursor += 1

    return _write_runtime(selected, destination)
