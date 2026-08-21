"""Women/general content entry point for Talk N Walks.

The proven visual/content builder stays unchanged; this wrapper only applies
topic-aware audio after the Reel is built.
"""

import build_reel
from apply_audio import apply_audio_to_build


if __name__ == "__main__":
    build_reel.main()
    apply_audio_to_build(
        build_reel.QUOTES_FILE,
        build_reel.OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
    )
