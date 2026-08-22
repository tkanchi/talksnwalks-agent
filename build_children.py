"""Kids, pre-teen, and teen content entry point for TalksNWalks101."""

from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from illustration_pool import apply_illustration_pool
from quote_library import build_curated_simple_quote_file
from visual_theme import apply_visual_theme


CONTENT_NAME = "children"
build_reel.OUTPUT_DIR = Path("outputs/children")
build_reel.PUBLIC_DIR = Path("public/children")


if __name__ == "__main__":
    # Fresh experiment: start from Day 1 using the stronger age-appropriate morals pool.
    build_reel.QUOTES_FILE = build_curated_simple_quote_file(
        Path("data/references/kids_morals.csv"),
        Path("outputs/children/quotes_runtime.csv"),
        preserve_days=0,
    )
    apply_illustration_pool(
        build_reel,
        Path("illustrations"),
        stream="children",
        quote_file=build_reel.QUOTES_FILE,
    )
    apply_visual_theme(build_reel)
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
    )
