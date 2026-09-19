"""Women/general content entry point for Talk N Walks.

Builds a fresh Day-1 production pool from the quote libraries and adds
stream-aware illustrations plus topic-aware audio.
"""

import shutil
from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from audio_quality_gate import require_real_audio
from illustration_pool import apply_illustration_pool
from watercolor_background_theme import apply_visual_theme
from women_quote_clarity import apply_women_quote_clarity, is_clear_women_quote
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


def _live_illustration_dir(stream: str) -> Path:
    """Build a runtime pool that temporarily excludes all_* artwork."""
    source = Path("illustrations")
    target = Path(".runtime_illustrations") / stream
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    kept = 0
    for path in source.iterdir():
        if (
            not path.is_file()
            or path.suffix.lower() not in {".png", ".jpg", ".jpeg"}
            or path.name.lower().startswith("all_")
        ):
            continue
        destination = target / path.name
        try:
            destination.symlink_to(path.resolve())
        except OSError:
            shutil.copy2(path, destination)
        kept += 1

    if not kept:
        raise FileNotFoundError("No non-all_* illustrations available for women publishing")
    return target


def _apply_visuals() -> None:
    apply_illustration_pool(
        build_reel,
        _live_illustration_dir("women"),
        stream="women",
        quote_file=build_reel.QUOTES_FILE,
    )
    apply_visual_theme(build_reel, stream="women")
    print("Approved watercolor-background women/general visuals enabled.")


if __name__ == "__main__":
    build_reel.QUOTES_FILE = build_curated_runtime_quote_file(
        WOMEN_QUOTE_PARTS,
        Path("outputs/quotes_runtime.csv"),
        target_days=365,
        exclude_prefixes=("WLEG",),
        source_weights={"WOM": 12, "WEMP": 5, "UC": 4, "SG": 2},
        required_source_type="inspired_by",
        require_book_author=True,
        row_transform=apply_women_quote_clarity,
        row_filter=is_clear_women_quote,
        fixed_quote_ids_by_day={
            29: "SG094",
            30: "SG339",
            31: "WEMP166",
        },
    )
    _apply_visuals()
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
        stream="women",
    )
    require_real_audio(build_reel.OUTPUT_DIR, allow_generated=True)
