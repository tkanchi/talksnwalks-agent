"""Deterministic supporting-text enrichment for the unified book library.

The main quote remains the book-inspired idea. SupportingText is editorial context:
short, non-attributed, and deliberately conversational so it reads like a human
clarification rather than a second quotation from the author.

Priority:
1. Approved hand-written Month-1 support lines.
2. Support already present in a source library.
3. Deterministic editorial support based on the row's existing theme/topic metadata.
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

# These deliberately avoid the old repetitive "The lesson / The book / This
# perspective" voice. The focus phrase comes from metadata already attached to
# the book-inspired row, so the supporting line clarifies rather than invents a
# new standalone quote.
TEMPLATES = (
    "At heart, this is about {focus}.",
    "In plain terms, this comes back to {focus}.",
    "The practical thread here is {focus}.",
    "What matters here is how {focus} shows up daily.",
    "This is really a reminder about {focus}.",
    "A useful way to read this is through {focus}.",
    "The point lands on {focus} in everyday life.",
    "Underneath the message is a focus on {focus}.",
    "The everyday version of this is {focus}.",
    "This comes down to {focus} in real life.",
    "Think of this as a note about {focus}.",
    "The core of it is {focus} in practice.",
    "Read it as a reminder to notice {focus}.",
    "The useful part is seeing {focus} in daily choices.",
    "A simple way to hold this is {focus}.",
    "In everyday life, this shows up as {focus}.",
    "The thought here is grounded in {focus}.",
    "This is a practical lens for thinking about {focus}.",
    "At its simplest, this is about {focus}.",
    "This is where {focus} becomes part of daily life.",
    "A grounded reading of this is {focus}.",
    "The thread running through this is {focus}.",
    "This is one way to make sense of {focus}.",
    "The message points back to {focus} in practice.",
    "What stays with you is the focus on {focus}.",
    "This is a quiet reminder to notice {focus}.",
    "The useful question here is what {focus} looks like daily.",
    "The message feels clearer when you name {focus}.",
    "Keep the attention on {focus} in ordinary moments.",
    "There is a practical focus here on {focus}.",
    "A simple reading is to keep noticing {focus}.",
    "The message makes more sense through {focus}.",
    "The practical side of this is {focus}.",
    "This is worth reading through the lens of {focus}.",
    "The clearest thread here is {focus}.",
    "The point is less abstract when you notice {focus}.",
    "In practice, the message keeps returning to {focus}.",
    "A useful place to start is with {focus}.",
    "What this highlights most clearly is {focus}.",
    "The real-world focus here is {focus}.",
    "It helps to read this as a note on {focus}.",
    "The message brings attention back to {focus}.",
    "The simplest thread to follow here is {focus}.",
    "The practical meaning sits close to {focus}.",
    "This message is easier to apply through {focus}.",
    "The point becomes clearer when you name {focus}.",
    "A useful reading keeps {focus} in view.",
    "The everyday meaning comes back to {focus}.",
    "The message stays grounded when you focus on {focus}.",
    "The core message keeps returning to {focus}.",
    "A practical reading starts with {focus}.",
    "The most useful thread here is {focus}.",
    "In real life, the message points toward {focus}.",
    "The message is easier to carry when framed as {focus}.",
    "A simple way to frame this is {focus}.",
    "The practical point here is {focus}.",
    "The message keeps {focus} close to everyday life.",
    "What this brings into focus is {focus}.",
    "The clearest everyday thread is {focus}.",
    "The point here is to keep noticing {focus}.",
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


def focus_phrase(row: dict[str, str]) -> str:
    candidates = (
        clean(row.get("OriginalTheme")),
        clean(row.get("Topic")),
        clean(row.get("TopicCategory")),
    )
    for raw in candidates:
        if not raw:
            continue
        phrase = raw.replace(" & ", " and ")
        phrase = re.sub(r"\s*\|\s*", " and ", phrase)
        phrase = re.sub(r"\s+", " ", phrase).strip(" -")
        if 1 <= word_count(phrase) <= 4:
            return phrase.casefold()
    return "the core idea"


def _candidate_order(quote_id: str) -> list[int]:
    digest = hashlib.sha256(clean(quote_id).encode("utf-8")).digest()
    start = int.from_bytes(digest[:4], "big") % len(TEMPLATES)
    return [(start + offset) % len(TEMPLATES) for offset in range(len(TEMPLATES))]


def generated_support(row: dict[str, str], used: set[str]) -> str:
    focus_options = []
    for key in ("OriginalTheme", "Topic", "TopicCategory"):
        probe = dict(row)
        probe["OriginalTheme"] = clean(row.get(key))
        focus = focus_phrase(probe)
        if focus not in focus_options:
            focus_options.append(focus)

    quote_norm = normalize(clean(row.get("Quote")))
    for focus in focus_options:
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
