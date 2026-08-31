from __future__ import annotations

import argparse
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

    # Keep captions focused: exactly five relevant hashtags.
    return deduped[:5]


def build_caption(selection: dict[str, str], hashtags: list[str]) -> str:
    support = clean(selection.get("SupportingText"))
    book = clean(selection.get("InspiredBy"))
    author = clean(selection.get("Author"))
    return (
        f"{support}\n\n"
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
