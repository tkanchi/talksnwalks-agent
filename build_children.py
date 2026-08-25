"""Kids, pre-teen, and teen content entry point for TalksNWalks101."""

from __future__ import annotations

import csv
from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from audio_quality_gate import require_real_audio
from engagement_card import apply_engagement_card
from illustration_pool import apply_illustration_pool
from watercolor_background_theme import apply_visual_theme
from quote_library import build_curated_simple_quote_file


CONTENT_NAME = "children"
build_reel.OUTPUT_DIR = Path("outputs/children")
build_reel.PUBLIC_DIR = Path("public/children")

CHILD_TOPIC_MAP = {
    "Kindness & Empathy": "Kindness",
    "Honesty & Integrity": "Integrity & Character",
    "Respect & Equality": "Justice & Equality",
    "Responsibility & Effort": "Discipline",
    "Courage & Speaking Up": "Courage",
    "Friendship & Inclusion": "Friendship",
    "Self-Control & Patience": "Peace",
    "Gratitude & Humility": "Gratitude",
    "Digital & Social Responsibility": "Digital Responsibility",
    "Health, Balance & Self-Respect": "Health",
    "Childhood & Family": "Family",
    "Study & Learning": "Study & Learning",
    "Sports & Teamwork": "Sports",
    "Teen Confidence & Identity": "Teen Confidence",
    "Joy, Music & Dance": "Music & Dance",
    "Peace & Spirituality": "Spirituality",
}


def apply_canonical_child_topics(path: Path) -> Path:
    """Map the kids-morals themes into the canonical Talk N Walks taxonomy."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if "Topic" not in fieldnames:
        raise ValueError(f"Runtime quote file is missing Topic: {path}")

    for row in rows:
        theme = (row.get("Theme") or "").strip()
        row["Topic"] = CHILD_TOPIC_MAP.get(theme, (row.get("Topic") or theme).strip())

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _apply_visuals() -> None:
    apply_illustration_pool(
        build_reel,
        Path("illustrations"),
        stream="children",
        quote_file=build_reel.QUOTES_FILE,
    )
    apply_visual_theme(build_reel, stream="children")
    print("Approved watercolor-background children visuals enabled.")


if __name__ == "__main__":
    build_reel.QUOTES_FILE = build_curated_simple_quote_file(
        Path("data/references/kids_morals.csv"),
        Path("outputs/children/quotes_runtime.csv"),
        preserve_days=0,
    )
    apply_canonical_child_topics(build_reel.QUOTES_FILE)
    _apply_visuals()
    apply_engagement_card(build_reel)
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
        stream="children",
    )
    require_real_audio(build_reel.OUTPUT_DIR)
