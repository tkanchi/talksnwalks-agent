"""Women/general content entry point for Talk N Walks.

Builds a fresh Day-1 production pool from the quote libraries and adds
stream-aware visuals plus topic-aware audio. The locked offline pastel renderer
is the default; external AI and the legacy illustration renderer are opt-in.
"""

import os
from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from audio_quality_gate import require_real_audio
from illustration_pool import apply_illustration_pool
from legacy_visual_theme import apply_visual_theme as apply_legacy_visual_theme
from pastel_visual_theme import apply_pastel_visual_theme
from quote_library import build_curated_runtime_quote_file
from visual_theme import apply_visual_theme as apply_ai_visual_theme


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


def _enabled(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _apply_visuals() -> None:
    if _enabled("AI_VISUALS_ENABLED"):
        apply_ai_visual_theme(build_reel)
        print("External AI visual renderer enabled for women/general build.")
        return

    if _enabled("LEGACY_VISUALS_ENABLED"):
        apply_illustration_pool(
            build_reel,
            Path("illustrations"),
            stream="women",
            quote_file=build_reel.QUOTES_FILE,
        )
        apply_legacy_visual_theme(build_reel)
        print("Legacy illustration renderer enabled for women/general build.")
        return

    apply_pastel_visual_theme(build_reel, stream="women")
    print("Locked pastel visual renderer enabled for women/general build.")


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
