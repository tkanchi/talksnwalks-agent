"""Men content entry point for TalksNWalks101."""

from pathlib import Path

import build_reel


CONTENT_NAME = "men"

build_reel.QUOTES_FILE = Path("data/men/quotes.csv")
build_reel.ILLUSTRATION_DIR = Path("illustrations/men")
build_reel.OUTPUT_DIR = Path("outputs/men")
build_reel.PUBLIC_DIR = Path("public/men")
build_reel.ILLUSTRATIONS = sorted(
    path.name for path in build_reel.ILLUSTRATION_DIR.glob("*.png")
)


if __name__ == "__main__":
    build_reel.main()
