"""Deterministic supporting-text enrichment for the unified book library.

The main quote remains the book-inspired idea. SupportingText is editorial context:
short, non-attributed, and deliberately plain so it does not look like a second
quotation from the author.

Priority:
1. Approved hand-written Month-1 support lines.
2. Support already present in a source library.
3. Deterministic editorial support based on the row's canonical theme/topic.
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

# These lines intentionally read as editorial explanation rather than quotable
# aphorisms. The focus phrase comes from the row's existing book/theme metadata.
# The focus always appears as an object/complement rather than a grammatical
# subject, which keeps compound phrases such as "happiness and habits" safe.
TEMPLATES = (
    "This idea makes {focus} practical in everyday choices.",
    "The lesson connects {focus} with choices you can repeat.",
    "In practice, small decisions give {focus} a visible place.",
    "This perspective turns {focus} into something you can practice.",
    "The takeaway is to bring {focus} into the next choice.",
    "Real change grows from bringing {focus} into daily action.",
    "This lesson keeps {focus} grounded in what you do.",
    "Small actions give {focus} a place in real life.",
    "The book treats {focus} as something strengthened through practice.",
    "This idea links {focus} to choices made today.",
    "The practical focus applies {focus} one choice at a time.",
    "This takeaway brings {focus} back to everyday behavior.",
    "The lesson gets clearer when you bring {focus} into decisions.",
    "This perspective makes {focus} useful beyond the page.",
    "Daily choices give {focus} room to become real.",
    "The idea becomes practical when you apply {focus} to what follows.",
    "This lesson turns {focus} from theory into repeatable action.",
    "The book connects {focus} with actions that can be practiced.",
    "This takeaway keeps {focus} close to the next decision.",
    "In everyday life, deliberate choices strengthen {focus}.",
    "The lesson places {focus} inside the choices you make.",
    "This idea asks how to bring {focus} into daily action.",
    "The practical takeaway applies {focus} through consistent action.",
    "This perspective makes {focus} part of ordinary practice.",
    "The book makes {focus} easier to apply through small choices.",
    "This lesson shows {focus} through what you repeatedly choose.",
    "The idea keeps {focus} connected to practical behavior.",
    "Everyday decisions give {focus} a concrete place to grow.",
    "This takeaway turns {focus} into something actionable today.",
    "The lesson keeps {focus} close to choices you make.",
    "This perspective connects {focus} with consistent everyday behavior.",
    "The book brings {focus} into the rhythm of daily choices.",
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
