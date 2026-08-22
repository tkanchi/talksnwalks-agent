"""Women/general content entry point for Talk N Walks.

The proven visual/content builder stays unchanged; this wrapper only applies
a safer illustration order plus topic-aware audio after the Reel is built.
"""

import build_reel
from apply_audio import apply_audio_to_build


WOMEN_ILLUSTRATIONS = [
    # Keep Days 1-4 exactly as already published.
    "reading_01.png", "reading_02.png",
    "dancing_01.png", "dancing_02.png",
    # From Day 5 onward, avoid back-to-back illustrations from the same category.
    "music_01.png", "workout_01.png",
    "sleeping_01.png", "laughing_01.png",
    "music_02.png", "workout_02.png",
    "sleeping_02.png", "laughing_02.png",
]


if __name__ == "__main__":
    build_reel.ILLUSTRATIONS = WOMEN_ILLUSTRATIONS
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
    )
