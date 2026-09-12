from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from build_feed_preview import compose
from select_next_post import (
    SEMANTIC_TOPIC_KEYWORDS,
    _semantic_matches,
    append_history,
    build_selection,
    clean,
    history_entries,
    load_history,
    output_payload,
    write_history,
)

ROOT = Path(__file__).resolve().parent
HISTORY_FILE = ROOT / "shadow_logs" / "unified" / "selection_history_active.json"
OUTPUT_DIR = ROOT / "outputs" / "unified_shadow"
TZ = ZoneInfo("Asia/Kolkata")
HANDLE = "@talksnwalks101"

# Instagram discovery now relies more on clear caption context than long hashtag
# blocks. Keep these as readable phrases so the selected terms can be woven into
# natural caption copy and logged for later performance analysis.
CATEGORY_KEYWORDS = {
    "Relationships": (
        "relationships", "communication", "friendship", "love",
        "healthy relationships", "boundaries", "emotional intelligence", "connection",
    ),
    "Family": (
        "family", "parenting", "family relationships", "childhood",
        "motherhood", "fatherhood", "home", "personal growth",
    ),
    "Wellness": (
        "wellness", "self care", "mental health", "fitness",
        "healthy lifestyle", "body confidence", "rest", "wellbeing",
    ),
    "Mindset": (
        "mindset", "motivation", "self belief", "personal growth",
        "self improvement", "confidence", "resilience", "positive thinking",
    ),
    "Business": (
        "success", "entrepreneurship", "leadership", "career growth",
        "discipline", "execution", "decision making", "money mindset",
    ),
    "Youth": (
        "learning", "growth mindset", "teen confidence", "study motivation",
        "school life", "digital wellbeing", "life skills", "personal growth",
    ),
    "Values": (
        "kindness", "integrity", "character", "spirituality",
        "gratitude", "compassion", "personal growth", "life lessons",
    ),
    "Lifestyle": (
        "lifestyle", "inspiration", "work life balance", "travel",
        "books", "reading", "music", "daily motivation",
    ),
}

SEMANTIC_CATEGORY_PRIORITY = (
    (
        "Business",
        {
            "CEO Mindset", "Entrepreneurship", "Leadership", "Execution",
            "Money Mindset", "Career", "Strategy & Decision-Making",
        },
    ),
    (
        "Wellness",
        {"Fitness", "Health", "Mental Health", "Rest & Recovery", "Body Confidence"},
    ),
    (
        "Relationships",
        {"Friendship", "Best Friends", "Love", "Relationships", "Marriage", "Breakups", "Communication & Social Skills"},
    ),
    (
        "Family",
        {"Mother", "Father", "Sisters", "Brothers", "Siblings", "Family", "Parenting", "Childhood Nostalgia"},
    ),
    (
        "Youth",
        {"Study & Learning", "Kids Morals", "Teen Confidence", "Sports", "Digital Responsibility"},
    ),
    (
        "Values",
        {"Kindness", "Spirituality", "Integrity & Character", "Justice & Equality"},
    ),
    (
        "Lifestyle",
        {"Funny & Relatable", "Travel & Adventure", "Reading & Books", "Music & Dance", "Work-Life Balance"},
    ),
    (
        "Mindset",
        {
            "Self-Belief", "Discipline", "Resilience", "Growth", "Peace",
            "Gratitude", "Happiness", "Hope", "Goals", "Courage",
            "Purpose & Meaning", "Authenticity & Identity",
        },
    ),
)

CAPTION_NOTES = {
    "Relationships": (
        "Worth remembering in the conversations that matter.",
        "One to keep close when listening matters more than reacting.",
        "A useful thought for the way we show up with people.",
        "Some relationship lessons only make sense once we practice them.",
    ),
    "Family": (
        "One to carry into the small moments at home.",
        "Worth remembering around the people closest to us.",
        "The everyday moments with family are often where this matters most.",
        "A quiet reminder for the relationships we can easily take for granted.",
    ),
    "Wellness": (
        "Worth sitting with when you think about how you care for yourself.",
        "A useful reminder for days when your energy feels stretched.",
        "Sometimes the smallest steady practice is the one worth keeping.",
        "One to revisit when taking care of yourself starts feeling complicated.",
    ),
    "Mindset": (
        "One to come back to when your thoughts get noisy.",
        "Worth keeping nearby for the harder days.",
        "A small thought to carry into the next choice.",
        "Sometimes noticing the pattern is already useful progress.",
    ),
    "Business": (
        "A useful thought to carry into the next decision.",
        "Worth keeping in mind when priorities start competing.",
        "One to revisit before urgency decides the direction for you.",
        "A practical idea for the work that actually matters.",
    ),
    "Youth": (
        "A simple idea to keep close while learning and growing.",
        "Worth remembering when progress looks different from someone else's.",
        "One for the days you are still figuring things out.",
        "Learning is rarely as neat as it looks from the outside.",
    ),
    "Values": (
        "A quiet reminder for the way we treat people.",
        "Worth remembering in the small decisions nobody applauds.",
        "Character usually shows up in ordinary moments first.",
        "One to keep close when the easy choice is not the kindest.",
    ),
    "Lifestyle": (
        "A small thought for ordinary life.",
        "Worth carrying into the rest of the day.",
        "One to notice in the middle of everyday routines.",
        "Sometimes the useful part is simply paying attention.",
    ),
}
GENERIC_CAPTION_NOTES = (
    "One to sit with for a moment.",
    "Worth coming back to when it meets the right day.",
    "A small thought to carry into today.",
    "Keep the part that feels useful and come back to it later.",
)


def semantic_category(selection: dict[str, str]) -> str:
    quote_text = clean(selection.get("Quote")).casefold()
    semantic_topics = _semantic_matches(quote_text, SEMANTIC_TOPIC_KEYWORDS)

    # Words such as "voice" and "language" can describe identity or inner life,
    # not only communication. Require a stronger conversational signal before
    # allowing Communication & Social Skills to drive a relationship caption.
    strong_communication = bool(
        re.search(r"\b(communication|conversation\w*|listen\w*|speak\w*|heard)\b", quote_text)
        or "receives meaning" in quote_text
        or "safe conversations" in quote_text
    )
    if not strong_communication:
        semantic_topics.discard("Communication & Social Skills")

    for category, topics in SEMANTIC_CATEGORY_PRIORITY:
        if semantic_topics & topics:
            return category

    fallback = clean(selection.get("TopicCategory"))
    return fallback if fallback in CATEGORY_KEYWORDS else "Mindset"


def audience_keywords(selection: dict[str, str]) -> tuple[str, ...]:
    audience = clean(selection.get("Audience")).casefold()
    if "women" in audience:
        return ("women empowerment", "confidence for women")
    if audience == "men" or audience.startswith("men|") or "|men" in audience:
        return ("men's mindset", "self respect")
    if "kids" in audience or "teens" in audience:
        return ("teen motivation", "growth mindset")
    return ()


def build_keywords(selection: dict[str, str], limit: int = 9) -> list[str]:
    category = semantic_category(selection)
    topic = clean(selection.get("Topic")).casefold()
    event = clean(selection.get("Event")).casefold()

    candidates: list[str] = []
    if event:
        candidates.append(event)
    if topic:
        candidates.append(topic)
    candidates.extend(audience_keywords(selection))
    candidates.extend(CATEGORY_KEYWORDS.get(category, CATEGORY_KEYWORDS["Mindset"]))

    keywords: list[str] = []
    seen: set[str] = set()
    for phrase in candidates:
        phrase = clean(phrase).casefold()
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        keywords.append(phrase)
        if len(keywords) >= limit:
            break
    return keywords


def natural_list(items: list[str]) -> str:
    if not items:
        return "personal growth"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def caption_note(selection: dict[str, str]) -> str:
    category = semantic_category(selection)
    options = CAPTION_NOTES.get(category, GENERIC_CAPTION_NOTES)
    quote_id = clean(selection.get("QuoteID"))
    digest = hashlib.sha256(quote_id.encode("utf-8")).digest()
    return options[int.from_bytes(digest[:2], "big") % len(options)]


def build_caption(selection: dict[str, str], keywords: list[str]) -> str:
    support = clean(selection.get("SupportingText"))
    book = clean(selection.get("InspiredBy"))
    author = clean(selection.get("Author"))
    note = caption_note(selection)
    keyword_text = natural_list(keywords)
    return (
        f"{support}\n\n"
        f"{note}\n\n"
        f"If you're exploring {keyword_text}, save this reminder and share it with someone who may need it.\n\n"
        f"Inspired by {book} by {author}.\n\n"
        f"Follow {HANDLE} for book inspiration, daily wisdom and practical ideas for personal growth."
    )


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def default_start_date(history: dict) -> date:
    dates = [
        parse_date(clean(entry.get("selection_date")))
        for entry in history_entries(history)
        if clean(entry.get("selection_date"))
    ]
    if dates:
        return max(dates) + timedelta(days=1)
    return datetime.now(TZ).date()


def clear_output() -> None:
    if not OUTPUT_DIR.exists():
        return
    for path in sorted(OUTPUT_DIR.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()


def build_package(selection: dict[str, str], history: dict, index: int) -> dict:
    package_id = f"{clean(selection.get('SelectionDate'))}_{clean(selection.get('QuoteID'))}"
    package_dir = OUTPUT_DIR / "packages" / package_id
    package_dir.mkdir(parents=True, exist_ok=True)

    image_path = package_dir / "post.png"
    caption_path = package_dir / "caption.txt"
    package_path = package_dir / "package.json"

    keywords = build_keywords(selection)
    caption = build_caption(selection, keywords)

    compose(selection, image_path, index=index)

    payload = output_payload(selection)
    payload.update(
        {
            "mode": "shadow",
            "published": False,
            "package_id": package_id,
            "image": image_path.relative_to(ROOT).as_posix(),
            "caption_category": semantic_category(selection),
            "caption": caption,
            "keywords": keywords,
            # Keep the field for backward compatibility with old package readers,
            # but new captions intentionally contain no hashtags.
            "hashtags": [],
        }
    )

    caption_path.write_text(caption + "\n", encoding="utf-8")
    package_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    append_history(history, selection)
    latest = history_entries(history)[-1]
    latest.update(
        {
            "mode": "shadow",
            "published": False,
            "package_id": package_id,
            "caption_category": semantic_category(selection),
            "caption": caption,
            "keywords": keywords,
            "hashtags": [],
        }
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build persistent unified shadow post packages.")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--start-date", default="")
    parser.add_argument("--history", type=Path, default=HISTORY_FILE)
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be at least 1")

    history = load_history(args.history)
    history["mode"] = "shadow"
    start = parse_date(args.start_date) if args.start_date else default_start_date(history)

    clear_output()
    manifest: list[dict] = []
    base_index = len(history_entries(history))

    for offset in range(args.count):
        on_date = start + timedelta(days=offset)
        selection = build_selection(on_date, history)
        package = build_package(selection, history, base_index + offset)
        manifest.append(package)
        print(
            f"{package['selection_date']} {package['quote_id']} | "
            f"{package['book']} | {package['topic']}"
        )

    write_history(args.history, history)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Built {len(manifest)} shadow packages")
    print(f"Persistent shadow history entries: {len(history_entries(history))}")
    print("Published: false")


if __name__ == "__main__":
    main()
