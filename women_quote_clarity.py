"""Women/general production quote integrity rules.

Book-inspired wording is reviewed in the source library before publishing.
Production must never paraphrase that wording a second time: doing so can remove
context, weaken the idea, or change what the cited book actually teaches.
"""

from __future__ import annotations

import re


MIN_QUOTE_WORDS = 5
MAX_QUOTE_WORDS = 32


def apply_women_quote_clarity(row: dict[str, str]) -> dict[str, str]:
    """Preserve the audited source wording and all attribution metadata."""
    return dict(row)


def is_clear_women_quote(row: dict[str, str]) -> bool:
    """Reject only malformed copy; completeness takes priority over brevity."""
    quote = (row.get("Quote") or "").strip()
    words = re.findall(r"[A-Za-z’'-]+", quote)
    return MIN_QUOTE_WORDS <= len(words) <= MAX_QUOTE_WORDS
