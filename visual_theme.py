"""Shared visual styling for Talk N Walks reel builders.

Keeps the existing layout and typography intact while using a warm cream
background so Instagram's white reaction controls remain visible.
"""

BACKGROUND_COLOR = "#F4F1EA"


def apply_visual_theme(build_reel):
    """Apply the approved cream-background visual theme to a build module."""
    original_compose_post = build_reel.compose_post

    def compose_post(quote, illustration_path, output_jpg):
        original_image_new = build_reel.Image.new

        def themed_image_new(mode, size, color=0):
            if mode == "RGB" and size == (build_reel.CANVAS_W, build_reel.CANVAS_H):
                color = BACKGROUND_COLOR
            return original_image_new(mode, size, color)

        build_reel.Image.new = themed_image_new
        try:
            original_compose_post(quote, illustration_path, output_jpg)
        finally:
            build_reel.Image.new = original_image_new

    build_reel.compose_post = compose_post
