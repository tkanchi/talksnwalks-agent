"""Quarantined pastel renderer for Talks N Walks.

The first offline pastel prototype used thumbnail-sized moodboard crops and
produced visibly blurred/patched full-screen images. It is intentionally blocked
from production until proper full-size scene assets pass a build-only visual
review.

Branding rule: do not add a logo to generated posts. The lowercase Instagram
handle may remain as text in the final approved renderer.
"""


def apply_pastel_visual_theme(build_reel, *, stream: str):
    raise RuntimeError(
        "PASTEL_VISUALS_ENABLED is experimental and currently quarantined: "
        "full-size pastel scene assets must pass build-only review before use. "
        "No logo should be added by the replacement renderer."
    )
