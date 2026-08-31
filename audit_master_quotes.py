"""Phase 1.5 quality audit for the unified Talk N Walks quote library.

Produces two additive outputs and does not alter live production inputs:
- data/quotes_master_clean.csv: safe candidate rows for the future unified selector.
- data/quotes_master_review.csv: every master row with deterministic quality flags.

The audit is intentionally conservative. Subjective issues are flagged for review,
not silently rewritten or deleted. Existing high-confidence corrections from
quote_text_quality.py are applied to the clean candidate copy only.

Run directly or via the Phase 1.5 GitHub Actions audit workflow.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

from quote_text_quality import polish_quote_text, QUOTE_CORRECTIONS


ROOT = Path(__file__).resolve().parent
MASTER_FILE = ROOT / "data" / "quotes_master.csv"
TOPICS_FILE = ROOT / "data" / "topics.csv"
CLEAN_FILE = ROOT / "data" / "quotes_master_clean.csv"
REVIEW_FILE = ROOT / "data" / "quotes_master_review.csv"

HARD_FLAGS = {
    "duplicate",
    "missing_quote",
    "missing_quote_id",
    "unknown_topic",
    "missing_topic_category",
    "missing_book_attribution",
}

REVIEW_FLAGS = {
    "very_short",
    "very_long",
    "gender_coded",
    "aggressive_tone",
    "negative_command_opener",
    "legacy_unattributed",
    "missing_source_type",
}

GENDER_TERMS = re.compile(
    r"\b(man|men|male|woman|women|female|boy|boys|girl|girls|husband|wife|son|daughter)\b",
    re.IGNORECASE,
)

AGGRESSIVE_TERMS = re.compile(
    r"\b(revenge|dangerous|destroy|crush|dominate|enemy|enemies|weakness|villain|control|punish|punishment)\b",
    re.IGNORECASE,
)

NEGATIVE_COMMAND = re.compile(r"^(do not|don't|don’t|never)\b", re.IGNORECASE)

# Topics where gender/family terms can be essential rather than accidental.
GENDER_CONTEXT_TOPICS = {
    "Mother", "Father", "Sisters", "Brothers", "Marriage", "Parenting", "Family"
}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _load_topics() -> dict[str, str]:
    with TOPICS_FILE.open(newline="", encoding="utf-8") as f:
        return {
            _clean(row.get("Topic")): _clean(row.get("Category"))
            for row in csv.DictReader(f)
            if _clean(row.get("Topic"))
        }


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def _flags(row: dict[str, str], topics: dict[str, str]) -> list[str]:
    flags: list[str] = []
    quote = _clean(row.get("Quote"))
    quote_id = _clean(row.get("QuoteID"))
    topic = _clean(row.get("Topic"))
    category = _clean(row.get("TopicCategory"))
    source_type = _clean(row.get("SourceType"))
    book = _clean(row.get("InspiredBy"))
    author = _clean(row.get("Author"))

    if not quote:
        flags.append("missing_quote")
    if not quote_id:
        flags.append("missing_quote_id")
    if _clean(row.get("DuplicateOf")):
        flags.append("duplicate")
    if not topic or topic not in topics:
        flags.append("unknown_topic")
    if not category:
        flags.append("missing_topic_category")
    elif topic in topics and category != topics[topic]:
        flags.append("topic_category_mismatch")

    if source_type == "inspired_by" and (not book or not author):
        flags.append("missing_book_attribution")
    if not source_type:
        flags.append("missing_source_type")
    if source_type == "legacy_original" and not _clean(row.get("AttributionNote")):
        flags.append("legacy_unattributed")

    words = _word_count(quote)
    if quote and words < 5:
        flags.append("very_short")
    if words > 24 or len(quote) > 155:
        flags.append("very_long")

    if topic not in GENDER_CONTEXT_TOPICS and GENDER_TERMS.search(quote):
        flags.append("gender_coded")
    if AGGRESSIVE_TERMS.search(quote):
        flags.append("aggressive_tone")
    if NEGATIVE_COMMAND.search(quote):
        flags.append("negative_command_opener")

    return flags


def _status(flags: list[str]) -> str:
    if any(flag in HARD_FLAGS for flag in flags):
        return "exclude"
    if flags:
        return "review"
    return "approved"


def audit() -> tuple[int, int, int, Counter[str]]:
    topics = _load_topics()
    with MASTER_FILE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("Master quote library is empty")

    review_fields = list(rows[0].keys()) + [
        "CandidateQuote", "WordCount", "QualityStatus", "ReviewFlags"
    ]
    clean_fields = list(rows[0].keys()) + ["QualityStatus"]

    reviewed: list[dict[str, str]] = []
    clean_rows: list[dict[str, str]] = []
    flag_counts: Counter[str] = Counter()
    statuses: Counter[str] = Counter()

    for row in rows:
        row = {key: _clean(value) for key, value in row.items()}
        flags = _flags(row, topics)
        status = _status(flags)
        statuses[status] += 1
        flag_counts.update(flags)

        quote_id = row.get("QuoteID", "")
        candidate_quote = polish_quote_text(QUOTE_CORRECTIONS.get(quote_id, row.get("Quote", "")))

        reviewed.append(
            {
                **row,
                "CandidateQuote": candidate_quote,
                "WordCount": str(_word_count(candidate_quote)),
                "QualityStatus": status,
                "ReviewFlags": "|".join(flags),
            }
        )

        # The clean candidate is deliberately strict: only deterministic passes.
        # Review rows remain in quotes_master_review.csv until explicitly approved.
        if status == "approved":
            clean_rows.append({**row, "Quote": candidate_quote, "QualityStatus": "approved"})

    with REVIEW_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=review_fields)
        writer.writeheader()
        writer.writerows(reviewed)

    with CLEAN_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=clean_fields)
        writer.writeheader()
        writer.writerows(clean_rows)

    print(f"Audited {len(rows)} master rows")
    print(f"Approved candidate rows: {statuses['approved']}")
    print(f"Review-required rows: {statuses['review']}")
    print(f"Excluded rows: {statuses['exclude']}")
    print("Flag counts:")
    for flag, count in sorted(flag_counts.items()):
        print(f"  {flag}: {count}")

    return len(rows), statuses["approved"], statuses["review"], flag_counts


if __name__ == "__main__":
    audit()
