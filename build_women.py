"""Women/general content entry point for Talk N Walks.

Keeps the proven builder while using the expanded quote library, safer
illustration order, shared visual theme, and topic-aware audio.
"""

from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from quote_library import build_runtime_quote_file
from visual_theme import apply_visual_theme


WOMEN_QUOTE_PARTS = [
    Path("data/library/women_motivating_part_01.csv"),
    Path("data/library/women_motivating_part_02.csv"),
    Path("data/library/women_motivating_part_03.csv"),
    Path("data/library/women_motivating_part_04.csv"),
    Path("data/library/self_growth_part_01.csv"),
    Path("data/library/self_growth_part_02.csv"),
    Path("data/library/self_growth_part_03.csv"),
    Path("data/library/self_growth_part_04.csv"),
    Path("data/library/self_growth_part_05.csv"),
    Path("data/library/women_empowerment_part_01.csv"),
    Path("data/library/women_empowerment_part_02.csv"),
    Path("data/library/women_empowerment_part_03.csv"),
    Path("data/library/women_empowerment_part_04.csv"),
]

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
    build_reel.QUOTES_FILE = build_runtime_quote_file(
        WOMEN_QUOTE_PARTS,
        Path("outputs/quotes_runtime.csv"),
    )
    build_reel.ILLUSTRATIONS = WOMEN_ILLUSTRATIONS
    apply_visual_theme(build_reel)
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
    )
