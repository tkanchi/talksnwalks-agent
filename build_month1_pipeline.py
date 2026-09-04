from __future__ import annotations

import csv
import os
from pathlib import Path

from PIL import Image

import build_reel
from apply_audio import apply_audio_to_build
from audio_quality_gate import require_real_audio
from build_feed_preview import BACKGROUND_RGB, compose as compose_feed_post

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "data" / "content_plan_month_01.csv"
OUTPUT_DIR = ROOT / "outputs" / "unified"
PUBLIC_DIR = ROOT / "public" / "unified"
RUNTIME_QUOTES = OUTPUT_DIR / "quotes_runtime.csv"
HANDLE = "@talksnwalks101"
REEL_W = 1080
REEL_H = 1920


def load_plan() -> list[dict[str, str]]:
    with PLAN.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No content plan rows found in {PLAN}")
    return rows


def resolve_post_number(rows: list[dict[str, str]]) -> int:
    raw = (os.getenv("POST_NUMBER") or os.getenv("DAY_NUMBER") or "1").strip()
    post_number = int(raw)
    if post_number < 1 or post_number > len(rows):
        raise ValueError(f"POST_NUMBER must be between 1 and {len(rows)}, got {post_number}")
    return post_number


def stream_for_audience(audience: str) -> str:
    value = (audience or "All").strip().lower()
    if "men" in value and "women" not in value:
        return "men"
    if any(token in value for token in ("kid", "teen", "youth", "child")):
        return "children"
    return "women"


def write_audio_runtime(rows: list[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    if "Theme" not in fieldnames:
        fieldnames.append("Theme")

    with RUNTIME_QUOTES.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["Theme"] = (item.get("Topic") or item.get("TopicCategory") or "Mindset").strip()
            writer.writerow(item)


def make_reel_frame(feed_image: Path, row: dict[str, str], output_path: Path) -> None:
    family = (row.get("BackgroundFamily") or "vanilla").strip()
    bg = BACKGROUND_RGB.get(family, BACKGROUND_RGB["vanilla"])
    card = Image.open(feed_image).convert("RGB")
    if card.size != (1080, 1080):
        raise ValueError(f"Expected 1080x1080 feed card, got {card.size}")

    frame = Image.new("RGB", (REEL_W, REEL_H), bg)
    frame.paste(card, (0, (REEL_H - card.height) // 2))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.save(output_path, "JPEG", quality=95, optimize=True, progressive=True)


def hashtag_token(value: str) -> str:
    return "".join(ch for ch in value.title() if ch.isalnum())


def build_caption(row: dict[str, str]) -> str:
    quote = (row.get("Quote") or "").strip()
    topic = (row.get("Topic") or "Mindset").strip()
    category = (row.get("TopicCategory") or "Mindset").strip()

    tags: list[str] = []
    for candidate in (
        hashtag_token(topic),
        hashtag_token(category),
        "Motivation",
        "DailyQuotes",
        "TalksNWalks",
    ):
        if candidate and candidate.lower() not in {tag.lower() for tag in tags}:
            tags.append(candidate)
        if len(tags) == 5:
            break

    caption_parts = [quote, HANDLE, " ".join(f"#{tag}" for tag in tags)]
    return "\n\n".join(caption_parts)


def main() -> None:
    rows = load_plan()
    post_number = resolve_post_number(rows)
    row = rows[post_number - 1]
    padded = f"{post_number:03d}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    write_audio_runtime(rows)

    feed_png = OUTPUT_DIR / f"day_{padded}_feed.png"
    reel_jpg = OUTPUT_DIR / f"day_{padded}_reel.jpg"
    fallback_wav = OUTPUT_DIR / f"day_{padded}_fallback.wav"
    reel_mp4 = PUBLIC_DIR / f"day_{padded}.mp4"
    caption_file = OUTPUT_DIR / "caption.txt"
    env_file = OUTPUT_DIR / "publish.env"

    compose_feed_post(row, feed_png)
    make_reel_frame(feed_png, row, reel_jpg)
    build_reel.write_fallback_audio(fallback_wav, duration=build_reel.REEL_SECONDS)
    build_reel.make_mp4(reel_jpg, fallback_wav, reel_mp4)
    caption_file.write_text(build_caption(row), encoding="utf-8")

    env_file.write_text(
        "\n".join(
            [
                "SKIP=false",
                f"DAY_NUMBER={post_number}",
                f"DAY_PADDED={padded}",
                f"POST_NUMBER={post_number}",
                f"QUOTE_ID={(row.get('QuoteID') or '').strip()}",
                f"AUDIENCE={(row.get('Audience') or '').strip()}",
                f"TOPIC={(row.get('Topic') or '').strip()}",
                f"VIDEO_FILE={reel_mp4.as_posix()}",
                f"IMAGE_FILE={feed_png.as_posix()}",
                f"REEL_FRAME={reel_jpg.as_posix()}",
                f"ILLUSTRATION={(row.get('Illustration') or '').strip()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stream = stream_for_audience(row.get("Audience", "All"))
    apply_audio_to_build(
        RUNTIME_QUOTES,
        OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
        stream=stream,
    )

    if os.getenv("REQUIRE_REAL_AUDIO", "false").strip().lower() == "true":
        require_real_audio(OUTPUT_DIR)

    print(f"Built unified Post {post_number}: {(row.get('QuoteID') or '').strip()}")
    print(f"Audience: {(row.get('Audience') or '').strip()} | Topic: {(row.get('Topic') or '').strip()}")
    print(f"Feed image: {feed_png}")
    print(f"Reel: {reel_mp4}")


if __name__ == "__main__":
    main()
