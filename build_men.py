"""Men content entry point for TalksNWalks101."""

import shutil
from pathlib import Path

import build_reel
from apply_audio import apply_audio_to_build
from audio_quality_gate import require_real_audio
from illustration_pool import apply_illustration_pool
from watercolor_background_theme import apply_visual_theme
from quote_library import build_curated_runtime_quote_file


CONTENT_NAME = "men"
MEN_QUOTE_PARTS = [
    Path("data/library/men_master_part_01.csv"),
    Path("data/library/men_master_part_02.csv"),
    Path("data/library/men_master_part_03.csv"),
    Path("data/library/men_master_part_04.csv"),
    Path("data/library/self_growth_part_01.csv"),
    Path("data/library/self_growth_part_02.csv"),
    Path("data/library/self_growth_part_03.csv"),
    Path("data/library/self_growth_part_04.csv"),
    Path("data/library/self_growth_part_05.csv"),
]

build_reel.OUTPUT_DIR = Path("outputs/men")
build_reel.PUBLIC_DIR = Path("public/men")


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
        raise FileNotFoundError("No non-all_* illustrations available for men publishing")
    return target


def _apply_visuals() -> None:
    apply_illustration_pool(
        build_reel,
        _live_illustration_dir("men"),
        stream="men",
        quote_file=build_reel.QUOTES_FILE,
    )
    apply_visual_theme(build_reel, stream="men")
    print("Approved men-safe watercolor-background visuals enabled.")


if __name__ == "__main__":
    build_reel.QUOTES_FILE = build_curated_runtime_quote_file(
        MEN_QUOTE_PARTS,
        Path("outputs/men/quotes_runtime.csv"),
        target_days=365,
        exclude_prefixes=("MLEG",),
        source_weights={"MEN": 12, "SG": 2},
        required_source_type="inspired_by",
        require_book_author=True,
    )
    _apply_visuals()
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
        stream="men",
    )
    require_real_audio(build_reel.OUTPUT_DIR)
