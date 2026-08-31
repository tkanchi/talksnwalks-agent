from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from build_feed_preview import BACKGROUND_KEYS, compose
from build_month1_content_plan import (
    YOUTH_AUDIENCE_VALUES,
    filename_for_stem,
    is_youth_safe,
)

ROOT = Path(__file__).resolve().parent
QUOTES_FILE = ROOT / "data" / "quotes_master_clean.csv"
OBJECTS_FILE = ROOT / "data" / "illustration_objects.csv"
EVENTS_FILE = ROOT / "data" / "events.csv"

DEFAULT_OUTPUT = ROOT / "outputs" / "unified_selector" / "next_post.json"
DEFAULT_HISTORY = ROOT / "outputs" / "unified_selector" / "selection_history.json"

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}

# Exact words/phrases from the main quote drive illustration meaning. A trailing
# * means prefix match (for example priorit* matches priority/priorities). This
# avoids accidental substring matches such as "read" inside "thread".
SEMANTIC_TOPIC_KEYWORDS = {
    "Leadership": ("leadership", "leader", "leading", "directing", "responsibility"),
    "Self-Belief": ("confidence", "self-belief", "believe in yourself", "belief in yourself"),
    "Authenticity & Identity": ("authentic*", "identity", "pretend*", "be yourself", "yourself", "belonging"),
    "Friendship": ("friend*", "friendship", "teamwork", "circle"),
    "Family": ("family", "home", "parent*", "mother", "father", "sibling*"),
    "Career": ("career", "job", "workplace", "professional"),
    "Entrepreneurship": ("business", "startup", "entrepreneur*"),
    "Strategy & Decision-Making": ("strategy", "decision*", "choice*", "priorit*", "trade-off*"),
    "Execution": ("execute*", "execution", "finish*", "task*", "interrupt*", "productivity", "priority", "priorities"),
    "Discipline": ("discipline", "consistent*", "consistency", "routine*", "practice*", "habit*", "deliberate*"),
    "Goals": ("goal*", "dream*", "vision", "ambition", "achievement*"),
    "Peace": ("peace", "calm", "quiet", "stillness", "steady"),
    "Mental Health": ("mental health", "inner language", "self-talk", "trigger*", "thought*", "healing", "shame", "stress"),
    "Rest & Recovery": ("rest", "sleep*", "recover*", "recovery", "self-care", "pause"),
    "Health": ("health", "wellness", "hydrate*"),
    "Fitness": ("fitness", "workout*", "gym", "training", "exercise*"),
    "Body Confidence": ("body confidence", "body respect", "physical space", "appearance", "self-love"),
    "Reading & Books": ("book*", "read*", "library"),
    "Study & Learning": ("study*", "learn*", "student*", "school", "teacher*", "education", "curiosity"),
    "Digital Responsibility": ("digital", "screen*", "phone*", "technology", "online", "internet", "device*"),
    "Travel & Adventure": ("travel*", "adventure*", "journey*", "trip*"),
    "Kindness": ("kind", "kindness", "compassion*"),
    "Love": ("love", "romance", "self-love"),
    "Relationships": ("relationship*", "partner*"),
    "Communication & Social Skills": ("communication", "listen*", "conversation*", "speak*", "voice", "heard", "language", "meaning"),
    "Hope": ("hope", "optimis*", "future", "possibility", "possibilities"),
    "Resilience": ("resilien*", "setback*", "comeback*", "recover from", "mental toughness", "difficult things", "hard things"),
    "Courage": ("courage", "brave*", "bold*", "fear*"),
    "Purpose & Meaning": ("purpose", "meaningful", "meaning", "calling"),
    "Gratitude": ("gratitude", "grateful", "thankful", "thank you"),
    "Money Mindset": ("money", "wealth", "financial", "income", "millionaire*"),
    "Integrity & Character": ("integrity", "values", "character", "responsibility"),
    "Justice & Equality": ("justice", "equality", "equal*", "inclusive", "inclusion", "vulnerable", "fairness"),
    "Happiness": ("happiness", "joy"),
}

SEMANTIC_TAG_KEYWORDS = {
    "learning": ("learn*", "student*", "school", "teacher*", "education", "study*"),
    "reading": ("read*", "book*", "library"),
    "focus": ("focus*", "attention", "interrupt*", "concentrat*", "deep work", "distraction*"),
    "time": ("time", "morning", "schedule*", "deadline*"),
    "new-day": ("morning", "new day", "start the day"),
    "morning": ("morning", "start the day"),
    "future": ("future", "vision", "possibility", "possibilities"),
    "reflection": ("inner language", "self-talk", "reflect*", "trigger*", "thought*", "shame"),
    "writing": ("journal", "inner language", "self-talk"),
    "challenge": ("challenge*", "difficult", "hard thing*", "setback*", "mental toughness"),
    "toughness": ("mental toughness", "difficult things", "hard things"),
    "health": ("health", "wellness", "body respect", "self-care"),
    "self-care": ("self-care", "care for yourself", "care for yourself"),
    "relationship": ("relationship*", "communication", "conversation*", "listen*", "partner*"),
    "communication": ("communication", "conversation*", "listen*", "voice", "language"),
    "listening": ("listen*", "heard", "receives meaning"),
    "kindness": ("kind", "kindness", "compassion*"),
    "love": ("love", "self-love", "romance"),
    "family": ("family", "parent*", "mother", "father", "home"),
    "freedom": ("freedom", "boundary", "boundaries", "control"),
    "choice": ("choice*", "decision*", "boundary", "boundaries"),
    "planning": ("plan*", "priority", "priorities", "routine*", "habit*", "prepare*"),
    "execution": ("execute*", "execution", "finish*", "task*", "action*", "productivity"),
    "business": ("business", "career", "workplace", "entrepreneur*"),
    "leadership": ("leadership", "leader", "leading", "directing"),
    "responsibility": ("responsibility", "accountability", "integrity", "values"),
    "goals": ("goal*", "ambition", "achievement*", "financial"),
    "purpose": ("purpose", "meaningful", "meaning", "calling"),
    "direction": ("direction", "path", "calling"),
    "opportunity": ("opportunity", "new chapter", "possibility", "possibilities"),
    "calm": ("calm", "peace", "quiet", "stillness", "steady"),
    "rest": ("rest", "sleep*", "recovery", "pause"),
    "travel": ("travel*", "journey*", "adventure*", "trip*"),
    "access": ("access", "inclusive", "inclusion", "equal*", "vulnerable"),
    "equality": ("equality", "equal*", "inclusive", "inclusion"),
}


def clean(value: object) -> str:
    return str(value or "").strip()


def split_pipe(value: str) -> set[str]:
    return {part.strip() for part in clean(value).split("|") if part.strip()}


def split_csv(value: str) -> set[str]:
    return {part.strip() for part in clean(value).split(",") if part.strip()}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def stable_tiebreak(on_date: date, row: dict[str, str]) -> str:
    payload = f"{on_date.isoformat()}|{clean(row.get('QuoteID'))}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _needle_matches(text: str, needle: str) -> bool:
    needle = clean(needle).casefold()
    if not needle:
        return False
    if needle.endswith("*"):
        stem = re.escape(needle[:-1])
        return bool(re.search(rf"\b{stem}[\w'-]*", text))
    if " " in needle or "-" in needle:
        return needle in text
    return bool(re.search(rf"\b{re.escape(needle)}\b", text))


def _semantic_matches(text: str, mapping: dict[str, tuple[str, ...]]) -> set[str]:
    return {
        label
        for label, needles in mapping.items()
        if any(_needle_matches(text, needle) for needle in needles)
    }


def illustration_semantic_score(obj: dict[str, str], quote: dict[str, str]) -> int:
    quote_text = clean(quote.get("Quote")).casefold()
    support_text = clean(quote.get("SupportingText")).casefold()
    quote_topics = _semantic_matches(quote_text, SEMANTIC_TOPIC_KEYWORDS)
    quote_tags = _semantic_matches(quote_text, SEMANTIC_TAG_KEYWORDS)

    primary = split_pipe(obj.get("PrimaryTopics", ""))
    secondary = split_pipe(obj.get("SecondaryTopics", ""))
    object_tags = {tag.casefold() for tag in split_csv(obj.get("Tags", ""))}

    score = 0
    if quote_topics or quote_tags:
        # The actual quote outranks imported taxonomy and generated support.
        score += 300 * len(quote_topics & primary)
        score += 160 * len(quote_topics & secondary)
        score += 130 * len(quote_tags & object_tags)
    else:
        # If the wording is too abstract to map, use support + canonical topic as
        # a fallback rather than guessing from unrelated metadata.
        support_topics = _semantic_matches(support_text, SEMANTIC_TOPIC_KEYWORDS)
        support_tags = _semantic_matches(support_text, SEMANTIC_TAG_KEYWORDS)
        topic = clean(quote.get("Topic"))
        score += 120 * len(support_topics & primary)
        score += 60 * len(support_topics & secondary)
        score += 50 * len(support_tags & object_tags)
        if topic in primary:
            score += 100
        if topic in secondary:
            score += 50

    return score


def is_book_eligible(row: dict[str, str]) -> bool:
    return (
        clean(row.get("QualityStatus")).lower() == "approved"
        and clean(row.get("SourceType")).lower() == "inspired_by"
        and bool(clean(row.get("Quote")))
        and bool(clean(row.get("SupportingText")))
        and bool(clean(row.get("InspiredBy")))
        and bool(clean(row.get("Author")))
        and is_youth_safe(row)
    )


def safe_for_youth_context(row: dict[str, str]) -> bool:
    probe = dict(row)
    probe["Audience"] = "Kids|Teens"
    return is_youth_safe(probe)


def parse_iso_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + (nth - 1) * 7)


def resolve_event_date(rule: str, year: int) -> date | None:
    rule = clean(rule)
    if rule.startswith("FIXED:"):
        month, day = [int(part) for part in rule.split(":", 1)[1].split("-")]
        return date(year, month, day)

    if rule.startswith("NTH_WEEKDAY:"):
        _, nth_raw, weekday_raw, month_raw = rule.split(":")
        month = MONTHS.get(month_raw.upper())
        weekday = WEEKDAYS.get(weekday_raw.upper())
        if month is None or weekday is None:
            raise ValueError(f"Unsupported NTH_WEEKDAY rule: {rule}")
        return nth_weekday(year, month, weekday, int(nth_raw))

    if rule.startswith("LOOKUP:"):
        return None

    raise ValueError(f"Unsupported event DateRule: {rule}")


def active_events(on_date: date, events: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    active: list[dict[str, str]] = []
    for event in events:
        for year in (on_date.year - 1, on_date.year, on_date.year + 1):
            event_date = resolve_event_date(event.get("DateRule", ""), year)
            if event_date is None:
                continue
            lead = int(clean(event.get("LeadDays")) or "0")
            follow = int(clean(event.get("FollowDays")) or "0")
            if event_date - timedelta(days=lead) <= on_date <= event_date + timedelta(days=follow):
                row = dict(event)
                row["ResolvedDate"] = event_date.isoformat()
                active.append(row)
                break

    return sorted(
        active,
        key=lambda event: (
            PRIORITY_RANK.get(clean(event.get("Priority")).lower(), 9),
            clean(event.get("ResolvedDate")),
            clean(event.get("EventID")),
        ),
    )


def event_audience_score(row: dict[str, str], event: dict[str, str]) -> int:
    quote_audiences = split_pipe(row.get("Audience", "")) or {"All"}
    event_audiences = split_pipe(event.get("Audiences", "")) or {"All"}

    if "All" in event_audiences:
        return 2
    if quote_audiences & event_audiences:
        return 3
    if "All" in quote_audiences:
        return 2

    adult_tokens = {"Adults", "Women", "Men"}
    if "Adults" in event_audiences and quote_audiences & adult_tokens:
        return 2
    return 0


def event_relevance(row: dict[str, str], event: dict[str, str]) -> tuple[int, str]:
    occasion = clean(row.get("Occasion"))
    event_id = clean(event.get("EventID"))
    event_name = clean(event.get("Event"))
    topic = clean(row.get("Topic"))
    primary = clean(event.get("PrimaryTopic"))
    secondary = split_csv(event.get("SecondaryTopics", ""))

    if occasion and occasion in {event_id, event_name}:
        return 4, "explicit occasion"
    if topic == primary:
        return 3, "primary topic"
    if topic in secondary:
        return 2, "secondary topic"
    return 0, ""


def history_entries(history: dict) -> list[dict]:
    selections = history.get("selections", [])
    return selections if isinstance(selections, list) else []


def load_history(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "selections": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid history format: {path}")
    data.setdefault("version", 1)
    data.setdefault("selections", [])
    return data


def write_history(path: Path, history: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def select_quote(
    on_date: date,
    quotes: list[dict[str, str]],
    events: list[dict[str, str]],
    history: dict,
) -> tuple[dict[str, str], dict[str, str] | None, str]:
    entries = history_entries(history)
    used_ids = {clean(entry.get("quote_id")) for entry in entries}
    candidates = [
        row for row in quotes
        if is_book_eligible(row) and clean(row.get("QuoteID")) not in used_ids
    ]
    if not candidates:
        raise RuntimeError("No unused eligible book-inspired quotes with SupportingText remain")

    topic_counts = Counter(clean(entry.get("topic")) for entry in entries)
    book_counts = Counter(clean(entry.get("book")) for entry in entries)
    recent_topics = [clean(entry.get("topic")) for entry in entries[-4:]]
    recent_books = [clean(entry.get("book")) for entry in entries[-4:]]

    for event in active_events(on_date, events):
        event_key = (clean(event.get("EventID")), clean(event.get("ResolvedDate")))
        event_limit = 3 if clean(event.get("Priority")).lower() == "high" else 2
        used_event_count = sum(
            1
            for entry in entries
            if (clean(entry.get("event_id")), clean(entry.get("event_date"))) == event_key
        )
        last_event_key = (
            (clean(entries[-1].get("event_id")), clean(entries[-1].get("event_date")))
            if entries
            else ("", "")
        )
        if used_event_count >= event_limit or last_event_key == event_key:
            continue

        event_has_youth = bool(split_pipe(event.get("Audiences", "")) & YOUTH_AUDIENCE_VALUES)
        event_candidates: list[tuple[dict[str, str], int, int, str]] = []
        for row in candidates:
            relevance, relevance_label = event_relevance(row, event)
            audience_score = event_audience_score(row, event)
            if relevance <= 0 or audience_score <= 0:
                continue
            if event_has_youth and not safe_for_youth_context(row):
                continue
            event_candidates.append((row, relevance, audience_score, relevance_label))

        if event_candidates:
            row, relevance, audience_score, relevance_label = min(
                event_candidates,
                key=lambda item: (
                    -item[1],
                    -item[2],
                    clean(item[0].get("Topic")) in recent_topics[-2:],
                    clean(item[0].get("InspiredBy")) in recent_books[-2:],
                    topic_counts[clean(item[0].get("Topic"))],
                    book_counts[clean(item[0].get("InspiredBy"))],
                    stable_tiebreak(on_date, item[0]),
                ),
            )
            reason = (
                f"occasion: {clean(event.get('Event'))} "
                f"({relevance_label}; priority={clean(event.get('Priority'))})"
            )
            return row, event, reason

    row = min(
        candidates,
        key=lambda candidate: (
            clean(candidate.get("Topic")) in recent_topics[-2:],
            clean(candidate.get("InspiredBy")) in recent_books[-2:],
            topic_counts[clean(candidate.get("Topic"))],
            book_counts[clean(candidate.get("InspiredBy"))],
            clean(candidate.get("Topic")),
            stable_tiebreak(on_date, candidate),
        ),
    )
    return row, None, "evergreen: topic/book variety with unused QuoteID"


def choose_illustration(
    quote: dict[str, str],
    objects: list[dict[str, str]],
    history: dict,
) -> tuple[dict[str, str], str, int]:
    approved = [obj for obj in objects if clean(obj.get("StyleStatus")).lower() == "approved"]
    if not approved:
        raise RuntimeError("No approved illustration objects available")

    entries = history_entries(history)
    object_counts = Counter(clean(entry.get("object_id")) for entry in entries[-30:])
    recent_object_ids = [clean(entry.get("object_id")) for entry in entries[-3:]]
    recent_tags: set[str] = set()
    for entry in entries[-3:]:
        recent_tags.update(entry.get("illustration_tags", []) or [])

    scores = {
        clean(obj.get("ObjectID")): illustration_semantic_score(obj, quote)
        for obj in approved
    }
    best_score = max(scores.values())

    if best_score > 0:
        floor = max(best_score * 0.70, best_score - 100)
        pool = [obj for obj in approved if scores[clean(obj.get("ObjectID"))] >= floor]
    else:
        pool = list(approved)

    non_recent = [obj for obj in pool if clean(obj.get("ObjectID")) not in recent_object_ids]
    if non_recent:
        pool = non_recent

    def rank(obj: dict[str, str]) -> tuple:
        oid = clean(obj.get("ObjectID"))
        tags = {tag.casefold() for tag in split_csv(obj.get("Tags", ""))}
        tag_overlap = len(tags & recent_tags)
        return (
            object_counts[oid],
            -scores[oid],
            tag_overlap,
            oid,
        )

    chosen = min(pool, key=rank)
    oid = clean(chosen.get("ObjectID"))
    return chosen, filename_for_stem(chosen.get("FileStem", "")), scores[oid]


def choose_background(history: dict) -> str:
    entries = history_entries(history)
    counts = Counter(clean(entry.get("background")) for entry in entries)
    recent = [clean(entry.get("background")) for entry in entries[-3:]]
    return min(
        BACKGROUND_KEYS,
        key=lambda key: (key in recent, counts[key], BACKGROUND_KEYS.index(key)),
    )


def choose_placement(obj: dict[str, str], history: dict) -> str:
    prefs = [part for part in clean(obj.get("PreferredPlacements")).split("|") if part]
    if not prefs:
        return "bottom_center"
    entries = history_entries(history)
    counts = Counter(clean(entry.get("placement")) for entry in entries)
    previous = clean(entries[-1].get("placement")) if entries else ""
    return min(prefs, key=lambda placement: (placement == previous, counts[placement], placement))


def build_selection(on_date: date, history: dict) -> dict:
    quotes = load_csv(QUOTES_FILE)
    objects = load_csv(OBJECTS_FILE)
    events = load_csv(EVENTS_FILE)

    quote, event, reason = select_quote(on_date, quotes, events, history)
    quote = dict(quote)
    quote["SupportingTextSource"] = "master"

    obj, illustration, illustration_score = choose_illustration(quote, objects, history)
    background = choose_background(history)
    placement = choose_placement(obj, history)

    selection = dict(quote)
    selection.update(
        {
            "SelectionDate": on_date.isoformat(),
            "SelectionReason": reason,
            "EventID": clean(event.get("EventID")) if event else "",
            "Event": clean(event.get("Event")) if event else "",
            "EventResolvedDate": clean(event.get("ResolvedDate")) if event else "",
            "ObjectID": clean(obj.get("ObjectID")),
            "Illustration": illustration,
            "IllustrationTags": clean(obj.get("Tags")),
            "IllustrationScore": str(illustration_score),
            "Placement": placement,
            "BackgroundFamily": background,
        }
    )
    return selection


def history_entry(selection: dict[str, str]) -> dict:
    return {
        "selection_date": clean(selection.get("SelectionDate")),
        "quote_id": clean(selection.get("QuoteID")),
        "audience": clean(selection.get("Audience")),
        "topic_category": clean(selection.get("TopicCategory")),
        "topic": clean(selection.get("Topic")),
        "book": clean(selection.get("InspiredBy")),
        "author": clean(selection.get("Author")),
        "event_id": clean(selection.get("EventID")),
        "event": clean(selection.get("Event")),
        "event_date": clean(selection.get("EventResolvedDate")),
        "object_id": clean(selection.get("ObjectID")),
        "illustration": clean(selection.get("Illustration")),
        "illustration_score": int(clean(selection.get("IllustrationScore")) or "0"),
        "illustration_tags": sorted(
            tag.casefold() for tag in split_csv(selection.get("IllustrationTags", ""))
        ),
        "placement": clean(selection.get("Placement")),
        "background": clean(selection.get("BackgroundFamily")),
        "reason": clean(selection.get("SelectionReason")),
    }


def append_history(history: dict, selection: dict[str, str]) -> None:
    history.setdefault("version", 1)
    history.setdefault("selections", []).append(history_entry(selection))


def output_payload(selection: dict[str, str]) -> dict:
    return {
        "selection_date": clean(selection.get("SelectionDate")),
        "quote_id": clean(selection.get("QuoteID")),
        "quote": clean(selection.get("Quote")),
        "supporting_text": clean(selection.get("SupportingText")),
        "supporting_text_source": clean(selection.get("SupportingTextSource")),
        "audience": clean(selection.get("Audience")),
        "topic_category": clean(selection.get("TopicCategory")),
        "topic": clean(selection.get("Topic")),
        "source_type": clean(selection.get("SourceType")),
        "book": clean(selection.get("InspiredBy")),
        "author": clean(selection.get("Author")),
        "event_id": clean(selection.get("EventID")),
        "event": clean(selection.get("Event")),
        "event_date": clean(selection.get("EventResolvedDate")),
        "object_id": clean(selection.get("ObjectID")),
        "illustration": clean(selection.get("Illustration")),
        "illustration_score": int(clean(selection.get("IllustrationScore")) or "0"),
        "illustration_tags": sorted(
            tag.casefold() for tag in split_csv(selection.get("IllustrationTags", ""))
        ),
        "placement": clean(selection.get("Placement")),
        "background": clean(selection.get("BackgroundFamily")),
        "reason": clean(selection.get("SelectionReason")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Select the next unified Talk N Walks post.")
    parser.add_argument("--date", dest="selection_date", default="")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write-history", action="store_true")
    parser.add_argument("--render", type=Path)
    args = parser.parse_args()

    on_date = parse_iso_date(args.selection_date)
    history = load_history(args.history)
    selection = build_selection(on_date, history)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output_payload(selection), indent=2), encoding="utf-8")

    if args.render:
        compose(selection, args.render, index=len(history_entries(history)))

    if args.write_history:
        append_history(history, selection)
        write_history(args.history, history)

    print(json.dumps(output_payload(selection), indent=2))


if __name__ == "__main__":
    main()
