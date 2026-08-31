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

CATEGORY_HASHTAGS = {
    "Relationships": ("#relationships", "#communication"),
    "Family": ("#family", "#parenting"),
    "Wellness": ("#wellness", "#selfcare"),
    "Mindset": ("#mindset", "#motivation"),
    "Business": ("#success", "#entrepreneurship"),
    "Youth": ("#learning", "#growthmindset"),
    "Values": ("#kindness", "#personalgrowth"),
    "Lifestyle": ("#lifestyle", "#inspiration"),
}
BASE_HASHTAGS = ("#bookinspiration", "#dailywisdom", "#talksnwalks")

# A short editorial bridge makes captions feel written for a person rather than
# assembled from fields. These are deliberately reader-facing and do not claim
# to be words from the cited author.
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


def hashtag_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", clean(text).casefold())
    return f"#{slug}" if slug else ""


def build_hashtags(selection: dict[str, str]) -> list[str]:
    tags: list[str] = []

    event = clean(selection.get("Event"))
    if event:
        event_tag = hashtag_slug(event)
        if event_tag:
            tags.append(event_tag)

    category = clean(selection.get("TopicCategory"))
    tags.extend(CATEGORY_HASHTAGS.get(category, ("#motivation", "#inspiration")))
    tags.extend(BASE_HASHTAGS)

    deduped: list[str] = []
    for tag in tags:
        if tag and tag not in deduped:
            deduped.append(tag)

    return deduped[:5]


def caption_note(selection: dict[str, str]) -> str:
    category = clean(selection.get("TopicCategory"))
    options = CAPTION_NOTES.get(category, GENERIC_CAPTION_NOTES)
    quote_id = clean(selection.get("QuoteID"))
    digest = hashlib.sha256(quote_id.encode("utf-8")).digest()
    return options[int.from_bytes(digest[:2], "big") % len(options)]


def build_caption(selection: dict[str, str], hashtags: list[str]) -> str:
    support = clean(selection.get("SupportingText"))
    book = clean(selection.get("InspiredBy"))
    author = clean(selection.get("Author"))
    note = caption_note(selection)
    return (
        f"{support}\n\n"
        f"{note}\n\n"
        f"Inspired by {book} by {author}.\n\n"
        f"{HANDLE}\n"
        f"{' '.join(hashtags)}"
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

    hashtags = build_hashtags(selection)
    if len(hashtags) != 5:
        raise RuntimeError(f"Expected exactly 5 hashtags for {package_id}, got {hashtags}")
    caption = build_caption(selection, hashtags)

    compose(selection, image_path, index=index)

    payload = output_payload(selection)
    payload.update(
        {
            "mode": "shadow",
            "published": False,
            "package_id": package_id,
            "image": image_path.relative_to(ROOT).as_posix(),
            "caption": caption,
            "hashtags": hashtags,
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
            "caption": caption,
            "hashtags": hashtags,
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
