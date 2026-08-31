"""Deterministic supporting-text enrichment for the unified book library.

The main quote remains the book-inspired idea. SupportingText is editorial context:
short, non-attributed, and conversational so it reads like a human clarification
rather than a second quotation from the author.

Priority:
1. Approved hand-written Month-1 support lines.
2. Support already present in a source library.
3. Deterministic editorial support based on canonical topic first, then legacy theme.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APPROVED_SUPPORT_FILE = ROOT / "data" / "supporting_text_month_01.csv"

WORD_RE = re.compile(r"\b[\w’'-]+\b")
NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

# {focus} is always used as an object/complement. That avoids subject-verb
# agreement problems with compound phrases while keeping the voice natural.
TEMPLATES = (
    "At heart, this is about {focus}.",
    "In plain terms, this comes back to {focus}.",
    "The practical thread here points back to {focus}.",
    "What matters here is keeping {focus} in view.",
    "This is really a reminder about {focus}.",
    "A useful way to read this keeps {focus} in mind.",
    "The point lands on {focus} in everyday life.",
    "Underneath the message is a focus on {focus}.",
    "The everyday takeaway comes back to {focus}.",
    "This comes down to {focus} in real life.",
    "Think of this as a note about {focus}.",
    "The core is keeping {focus} in view.",
    "Read it as a reminder to notice {focus}.",
    "The useful part is keeping {focus} close to daily choices.",
    "A simple way to hold this is to remember {focus}.",
    "In everyday life, this keeps the focus on {focus}.",
    "The thought here stays grounded in {focus}.",
    "This offers a practical lens for thinking about {focus}.",
    "At its simplest, this is about {focus}.",
    "This keeps {focus} connected to daily life.",
    "A grounded reading keeps the focus on {focus}.",
    "The thread running through this points back to {focus}.",
    "This is one way to make sense of {focus}.",
    "The message points back to {focus} in practice.",
    "What stays with you is the focus on {focus}.",
    "This is a quiet reminder to notice {focus}.",
    "A useful question is how to make room for {focus}.",
    "The message gets clearer when you name {focus}.",
    "Keep the attention on {focus} in ordinary moments.",
    "There is a practical focus here on {focus}.",
    "A simple reading is to keep noticing {focus}.",
    "The message makes more sense with {focus} in mind.",
    "The practical side is keeping {focus} in view.",
    "This is worth reading with {focus} in mind.",
    "The clearest thread here points toward {focus}.",
    "The point feels less abstract when you notice {focus}.",
    "In practice, the message keeps returning to {focus}.",
    "A useful place to start is by noticing {focus}.",
    "What this highlights most clearly is the role of {focus}.",
    "The real-world focus here stays on {focus}.",
    "It helps to read this as a note on {focus}.",
    "The message brings attention back to {focus}.",
    "The simplest thread to follow points toward {focus}.",
    "The practical meaning stays close to {focus}.",
    "This message feels easier to apply with {focus} in view.",
    "The point gets clearer when you name {focus}.",
    "A useful reading keeps {focus} in view.",
    "The everyday meaning comes back to {focus}.",
    "The message stays grounded when you keep {focus} in mind.",
    "The core message keeps returning to {focus}.",
    "A practical reading starts by noticing {focus}.",
    "The most useful thread here points back to {focus}.",
    "In real life, the message points toward {focus}.",
    "The message is easier to carry with {focus} in mind.",
    "A simple way to frame this keeps the focus on {focus}.",
    "The practical point here keeps the focus on {focus}.",
    "The message keeps {focus} close to everyday life.",
    "What this brings into focus is the importance of {focus}.",
    "The clearest everyday thread points back to {focus}.",
    "The point here is to keep noticing {focus}.",
    "A useful takeaway is to keep {focus} in sight.",
    "This lands more clearly when you think about {focus}.",
    "The everyday value comes from paying attention to {focus}.",
    "A practical way to carry this is to remember {focus}.",
)


def clean(value: object) -> str:
    return str(value or "").strip()


def word_count(text: str) -> int:
    return len(WORD_RE.findall(clean(text)))


def normalize(text: str) -> str:
    return NORMALIZE_RE.sub("", clean(text).casefold())


def load_approved_overrides(path: Path = APPROVED_SUPPORT_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            clean(row.get("QuoteID")): clean(row.get("SupportingText"))
            for row in csv.DictReader(handle)
            if clean(row.get("QCStatus")).lower() == "approved"
            and clean(row.get("QuoteID"))
            and clean(row.get("SupportingText"))
        }


def focus_phrase(value: str) -> str:
    phrase = clean(value).replace(" & ", " and ")
    phrase = re.sub(r"\s*\|\s*", " and ", phrase)
    phrase = re.sub(r"\s+", " ", phrase).strip(" -")
    if 1 <= word_count(phrase) <= 4:
        return phrase.casefold()
    return ""


def focus_options(row: dict[str, str]) -> list[str]:
    # Canonical Topic is cleaner and more reader-friendly than many imported
    # legacy theme strings. Legacy theme remains a fallback for uniqueness.
    options: list[str] = []
    for key in ("Topic", "OriginalTheme", "TopicCategory"):
        focus = focus_phrase(row.get(key, ""))
        if focus and focus not in options:
            options.append(focus)
    if "the core idea" not in options:
        options.append("the core idea")
    return options


def _candidate_order(quote_id: str) -> list[int]:
    digest = hashlib.sha256(clean(quote_id).encode("utf-8")).digest()
    start = int.from_bytes(digest[:4], "big") % len(TEMPLATES)
    return [(start + offset) % len(TEMPLATES) for offset in range(len(TEMPLATES))]


def generated_support(row: dict[str, str], used: set[str]) -> str:
    quote_norm = normalize(clean(row.get("Quote")))
    for focus in focus_options(row):
        for template_index in _candidate_order(clean(row.get("QuoteID"))):
            candidate = TEMPLATES[template_index].format(focus=focus)
            count = word_count(candidate)
            candidate_norm = normalize(candidate)
            if not (6 <= count <= 14):
                continue
            if candidate_norm == quote_norm or candidate_norm in used:
                continue
            return candidate

    raise RuntimeError(
        f"Could not create unique 6-14 word supporting text for {clean(row.get('QuoteID'))}"
    )


def enrich_supporting_text(
    rows: list[dict[str, str]],
    *,
    overrides: dict[str, str] | None = None,
) -> tuple[list[dict[str, str]], Counter[str]]:
    overrides = load_approved_overrides() if overrides is None else overrides
    used: set[str] = set()
    stats: Counter[str] = Counter()
    enriched: list[dict[str, str]] = []

    for original in rows:
        row = dict(original)
        quote_id = clean(row.get("QuoteID"))
        support = ""
        source = ""

        if clean(overrides.get(quote_id)):
            support = clean(overrides[quote_id])
            source = "approved_override"
        elif clean(row.get("SupportingText")):
            support = clean(row.get("SupportingText"))
            source = "source"
        else:
            support = generated_support(row, used)
            source = "generated_editorial"

        count = word_count(support)
        if not 6 <= count <= 14:
            raise RuntimeError(
                f"SupportingText for {quote_id} must be 6-14 words; got {count}: {support}"
            )

        support_norm = normalize(support)
        if support_norm in used:
            if source == "generated_editorial":
                support = generated_support(row, used)
                support_norm = normalize(support)
            else:
                raise RuntimeError(f"Duplicate approved/source SupportingText for {quote_id}: {support}")

        if support_norm == normalize(clean(row.get("Quote"))):
            raise RuntimeError(f"SupportingText duplicates main quote for {quote_id}")

        row["SupportingText"] = support
        used.add(support_norm)
        stats[source] += 1
        enriched.append(row)

    if len(used) != len(enriched):
        raise RuntimeError("SupportingText uniqueness check failed")

    return enriched, stats
