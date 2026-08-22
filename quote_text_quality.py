"""Copy-edit production quote text without changing source attribution metadata.

The source CSVs are our reference libraries. This module applies small,
high-confidence copy edits by QuoteID and a conservative punctuation/spacing
normalizer before quotes enter a runtime publishing pool.
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
    "MEN027": "Resilience is not about never falling; it is learning how to rise without worshipping the fall.",
    "MEN072": "A founder's first job is not to look successful; it is to find evidence that the idea works.",
    "MEN082": "Do not mistake people you party with for people you can build with.",
    "MEN086": "The market does not reward how passionately you built something; it rewards how useful customers find it.",
    "MEN091": "Wealth is what remains when nobody is watching.",
    "MEN161": "The goal is not to stop working forever; it is to avoid staying somewhere solely because you cannot afford to leave.",
    "MEN170": "A founder grows when 'I can do everything' becomes 'Everything should not depend on me.'",
    "MEN184": "Revenue is applause you can deposit; retention is trust you have earned.",
    "MEN224": "Do not build wealth for your children to inherit without giving them the wisdom to carry it.",
    "MEN293": "Your process should make excellent work easier, not make bureaucracy heavier.",
    "MEN343": "A childhood nickname can make forty-year-old men feel ten years old again.",
    "MEN363": "Your first cricket team had no contracts or sponsors, but it may have had the strongest loyalty you will ever know.",
    "SG019": "Remembering names, details, and personal moments tells people they are important enough to remember.",
    "SG023": "Let another person keep their dignity even when correction is necessary.",
    "SG033": "Much of our anxiety lives in a future we have not actually entered.",
    "SG050": "Meaning can carry a person through pain that comfort alone cannot ease.",
    "SG052": "Ask not only when this season will end, but what it is asking you to become.",
    "SG107": "Your best work needs enough uninterrupted time for your mind to stop switching contexts.",
    "SG213": "Your state affects performance, so learn how your body, focus, and language influence it.",
    "SG264": "Break a large task into a next step small enough to begin immediately.",
    "SG298": "Separate what is your responsibility from what belongs to someone else.",
    "SG317": "Let happiness support performance instead of waiting until the work is complete to feel it.",
    "SG354": "Your past can explain you without giving you permission to remain unchanged.",
    "SG356": "Keep proof of the hard things you have already done for the days when self-doubt returns.",
    "WEMP001": "Do not wait to feel perfectly ready before stepping toward the opportunity you have already earned.",
    "WEMP024": "Earning more often begins when a woman stops treating money as proof of goodness or selfishness.",
    "WEMP077": "Your self-talk should not be the loudest voice discouraging you.",
    "WEMP116": "Competence matters, but self-doubt can keep your competence hidden when opportunities arise.",
    "WEMP176": "Women create more freely when they stop demanding that every creative act justify its existence.",
    "WEMP178": "Use a small physical action to interrupt the habit of backing away.",
    "WEMP187": "Lead from the position you occupy instead of waiting for someone to name you a leader.",
    "WEMP203": "Your identity can hold many roles—daughter, mother, professional, partner, citizen, and dreamer—without reducing you to any one of them.",
    "WEMP225": "Your voice gets stronger when you use it before you feel polished.",
    "WEMP290": "Choose relationships that allow your spirit to expand instead of constantly defending itself.",
    "WEMP324": "Examine your earning ceiling whenever fear, rather than market value, is holding it down.",
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
    """Return a copied row with its production quote copy-edited."""
    polished = dict(row)
    quote_id = (polished.get("QuoteID") or polished.get("ID") or "").strip()
    source_text = QUOTE_CORRECTIONS.get(quote_id, polished.get("Quote", ""))
    polished["Quote"] = polish_quote_text(source_text)
    return polished
