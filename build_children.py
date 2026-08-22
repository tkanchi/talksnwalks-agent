"""Kids, pre-teen, and teen content entry point for TalksNWalks101."""

from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from visual_theme import apply_visual_theme


CONTENT_NAME = "children"

build_reel.QUOTES_FILE = Path("data/children/quotes.csv")
build_reel.ILLUSTRATION_DIR = Path("illustrations/children")
build_reel.OUTPUT_DIR = Path("outputs/children")
build_reel.PUBLIC_DIR = Path("public/children")
build_reel.ILLUSTRATIONS = sorted(
    path.name for path in build_reel.ILLUSTRATION_DIR.glob("*.png")
)


if __name__ == "__main__":
    apply_visual_theme(build_reel)
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
    )
