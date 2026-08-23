"""Women/general content entry point for Talk N Walks.

Builds a fresh Day-1 production pool from the quote libraries and adds
stream-aware illustrations plus topic-aware audio.
"""

from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from audio_quality_gate import require_real_audio
from illustration_pool import apply_illustration_pool
from legacy_visual_theme import apply_visual_theme as apply_legacy_visual_theme
from quote_library import build_curated_runtime_quote_file


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
    Path("data/library/user_curated_part_01.csv"),
    Path("data/library/women_empowerment_part_01.csv"),
    Path("data/library/women_empowerment_part_02.csv"),
    Path("data/library/women_empowerment_part_03.csv"),
    Path("data/library/women_empowerment_part_04.csv"),
]


def _apply_visuals() -> None:
    apply_illustration_pool(
        build_reel,
        Path("illustrations"),
        stream="women",
        quote_file=build_reel.QUOTES_FILE,
    )
    apply_legacy_visual_theme(build_reel)
    print("Illustration-based women/general visuals enabled.")


if __name__ == "__main__":
    build_reel.QUOTES_FILE = build_curated_runtime_quote_file(
        WOMEN_QUOTE_PARTS,
        Path("outputs/quotes_runtime.csv"),
        target_days=365,
        exclude_prefixes=("WLEG",),
        source_weights={"WOM": 12, "WEMP": 5, "UC": 4, "SG": 2},
    )
    _apply_visuals()
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
        stream="women",
    )
    require_real_audio(build_reel.OUTPUT_DIR)
