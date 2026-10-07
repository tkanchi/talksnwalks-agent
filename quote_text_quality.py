"""Copy-edit production quote text without changing source attribution metadata.

The source CSVs are our reference libraries. Book-inspired wording is audited
in those source files and must remain authoritative. This module keeps legacy
non-book copy edits plus a conservative punctuation/spacing normalizer.
"""

from __future__ import annotations

import re


# High-confidence grammar/clarity edits found during the full Women, Men,
# shared Self-Growth, and current Children production-library review. These are
# copy edits only; they do not change SourceType, InspiredBy, Author, Topic, or
# attribution metadata.
QUOTE_CORRECTIONS: dict[str, str] = {
    "WOM038": "Resilience is not about never falling; it is learning how to rise without hating the fall.",
    "WOM164": "Your brave life will require disappointing the version of you that always played it safe.",
    "WOM221": "Body respect is possible even on days when body love feels far away.",
    "WOM261": "Make space for quieter voices before decisions are made without them.",
    "WOM264": "Do one thing today that your fear would prefer you to postpone.",
    "WOM295": "Pause before your body has to force you to.",
    "WOM329": "Let the day be simple when your heart needs simplicity.",
    "MEN006": "Some people mistake silence for weakness, but quiet confidence does not need to prove itself.",
    "MEN020": "Upgrade your life until proving a point no longer matters.",
    "MEN027": "Resilience is not about never falling; it is learning how to rise without worshipping the fall.",
    "MEN033": "Having boundaries does not make you difficult; it makes your limits clear.",
    "MEN062": "Stay humble enough to learn and disciplined enough to execute.",
    "MEN072": "A founder's first job is not to look successful; it is to find evidence that the idea works.",
    "MEN082": "Do not mistake people you party with for people you can build with.",
    "MEN086": "The market does not reward how passionately you built something; it rewards how useful customers find it.",
    "MEN091": "Wealth is what remains when nobody is watching.",
    "MEN158": "Failure becomes costly only when it teaches you nothing.",
    "MEN161": "The goal is not to stop working forever; it is to avoid staying somewhere solely because you cannot afford to leave.",
    "MEN170": "A founder grows when 'I can do everything' becomes 'Everything should not depend on me.'",
    "MEN184": "Revenue is applause you can deposit; retention is trust you have earned.",
    "MEN224": "Do not build wealth for your children to inherit without giving them the wisdom to carry it.",
    "MEN248": "Sleep is part of performance, not time stolen from it.",
    "MEN293": "Your process should make excellent work easier, not make bureaucracy heavier.",
    "MEN343": "A childhood nickname can make forty-year-old men feel ten years old again.",
    "MEN360": "Guard your mornings, your money, your words, and your attention; much of life follows.",
    "MEN363": "Your first cricket team had no contracts or sponsors, but it may have had the strongest loyalty you will ever know.",
    "UC079": "Keep some ownership of your happiness instead of placing it entirely in someone else's hands.",
    "37": "You are allowed to ask for help, but do not hand off your responsibility.",
    "42": "If someone is being bullied, do not add your silence to the crowd.",
    "52": "Invite people in; you never know who needs that invitation.",
    "90": "The internet remembers, so post with the future in mind.",
    "92": "Health does not have one body shape.",
    "95": "Play, study, sleep, and laugh; growing up needs all of them.",
}


_CLOSING_QUOTES = "\"'”’"
_TERMINAL = ".!?…"


def _ensure_terminal_punctuation(text: str) -> str:
    """Add a final period only when no terminal punctuation is already present."""
    if not text:
        return text

    core = text.rstrip()
    closers = ""
    while core and core[-1] in _CLOSING_QUOTES:
        closers = core[-1] + closers
        core = core[:-1].rstrip()

    if core and core[-1] not in _TERMINAL:
        core += "."
    return core + closers


def polish_quote_text(text: str) -> str:
    """Conservatively normalize spacing and terminal punctuation."""
    text = (text or "").replace("\u00a0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:!?])(?=[A-Za-z])", r"\1 ", text)
    return _ensure_terminal_punctuation(text)


def polish_quote_row(row: dict[str, str]) -> dict[str, str]:
    """Normalize quote text without rewording audited book-inspired material."""
    polished = dict(row)
    quote_id = (polished.get("QuoteID") or polished.get("ID") or "").strip()
    source_type = (polished.get("SourceType") or polished.get("Type") or "").strip().lower()
    if source_type == "inspired_by":
        source_text = polished.get("Quote", "")
    else:
        source_text = QUOTE_CORRECTIONS.get(quote_id, polished.get("Quote", ""))
    polished["Quote"] = polish_quote_text(source_text)
    return polished
