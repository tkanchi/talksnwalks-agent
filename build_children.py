"""Kids, pre-teen, and teen content entry point for TalksNWalks101."""

from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from quote_library import build_curated_simple_quote_file
from visual_theme import apply_visual_theme


CONTENT_NAME = "children"

build_reel.ILLUSTRATION_DIR = Path("illustrations/children")
build_reel.OUTPUT_DIR = Path("outputs/children")
build_reel.PUBLIC_DIR = Path("public/children")
build_reel.ILLUSTRATIONS = sorted(
    path.name for path in build_reel.ILLUSTRATION_DIR.glob("*.png")
)


if __name__ == "__main__":
    # Days 1-3 stay fixed because Days 2 and 3 already have publish logs.
    # Future rows are reordered for stronger hooks and better theme variety.
    build_reel.QUOTES_FILE = build_curated_simple_quote_file(
        Path("data/library/children_master.csv"),
        Path("outputs/children/quotes_runtime.csv"),
        preserve_days=3,
    )
    apply_visual_theme(build_reel)
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
    )
