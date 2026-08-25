"""Plain premium daily backgrounds for Talk N Walks reels.

Keeps the existing quote, illustration, handle and publishing behavior intact.
Backgrounds use the finalized muted palette as simple solid fills. No botanical
shapes, fake leaves, gradients, watercolor blobs or busy textures are drawn.
"""

from __future__ import annotations

import legacy_visual_theme as legacy


BACKGROUND_VERSION = "muted-solid-v1"

# Finalized Talk N Walks daily background palette.
# Exact values from the approved palette board.
PALETTE = (
    {"name": "warm_ivory", "hex": "#F3EFE7", "rgb": (243, 239, 231)},
    {"name": "soft_stone", "hex": "#E8E3DC", "rgb": (232, 227, 220)},
    {"name": "dusty_beige", "hex": "#E6DCCF", "rgb": (230, 220, 207)},
    {"name": "pale_taupe", "hex": "#DDD4CB", "rgb": (221, 212, 203)},
    {"name": "mist_grey", "hex": "#E4E6E3", "rgb": (228, 230, 227)},
    {"name": "muted_sage", "hex": "#DDE4DA", "rgb": (221, 228, 218)},
    {"name": "blue_grey", "hex": "#DEE4E8", "rgb": (222, 228, 232)},
    {"name": "soft_blush", "hex": "#E8DDDA", "rgb": (232, 221, 218)},
)


def _preset_for(stream: str, output_jpg):
    """Rotate the finalized palette daily with a stable stream-specific offset."""
    day = max(1, legacy._day_number(output_jpg))
    normalized = (stream or "women").strip().lower()
    stream_offset = sum(ord(char) for char in normalized) % len(PALETTE)
    return PALETTE[((day - 1) + stream_offset) % len(PALETTE)]


def _build_background(build_reel, preset):
    """Create a plain solid premium background with no decorative shapes."""
    return build_reel.Image.new(
        "RGB",
        (build_reel.CANVAS_W, build_reel.CANVAS_H),
        preset["rgb"],
    )


def apply_visual_theme(build_reel, *, stream: str = "women"):
    """Apply the finalized plain muted background system to the existing renderer."""
    legacy.apply_visual_theme(build_reel)
    fallback_compose = build_reel.compose_post

    def compose_post(quote, illustration_path, output_jpg):
        try:
            preset = _preset_for(stream, output_jpg)
            primary, secondary = legacy._palette_for_output(output_jpg)
            canvas = _build_background(build_reel, preset)

            draw = build_reel.ImageDraw.Draw(canvas)
            wrapped_quote, qfont, quote_w, quote_h = legacy._fit_quote(
                build_reel, draw, quote
            )
            hfont = build_reel.find_font(build_reel.HANDLE_SIZE, serif=False)

            source_art = legacy._remove_opaque_white_background(
                build_reel.Image.open(illustration_path)
            )
            art = build_reel.fit_inside(
                source_art,
                build_reel.ILLUSTRATION_MAX_W,
                build_reel.ILLUSTRATION_MAX_H,
            )
            art = legacy._style_art(art, primary, secondary)

            hbox = draw.textbbox((0, 0), build_reel.HANDLE, font=hfont)
            handle_w = hbox[2] - hbox[0]
            handle_h = hbox[3] - hbox[1]

            total_height = (
                quote_h
                + build_reel.QUOTE_TO_ART_GAP
                + art.height
                + build_reel.ART_TO_HANDLE_GAP
                + handle_h
            )
            block_top = int(build_reel.BLOCK_CENTER_Y - total_height / 2)
            quote_y = block_top
            art_y = quote_y + quote_h + build_reel.QUOTE_TO_ART_GAP
            handle_y = art_y + art.height + build_reel.ART_TO_HANDLE_GAP

            draw.multiline_text(
                ((build_reel.CANVAS_W - quote_w) / 2, quote_y),
                wrapped_quote,
                fill=legacy.CHARCOAL,
                font=qfont,
                spacing=legacy.QUOTE_LINE_SPACING,
                align="center",
            )

            art_x = (build_reel.CANVAS_W - art.width) // 2
            canvas.paste(art, (art_x, art_y), art)

            canvas = legacy._draw_handle_brush(
                build_reel,
                canvas,
                handle_y,
                handle_w,
                handle_h,
                primary,
            )
            draw = build_reel.ImageDraw.Draw(canvas)
            draw.text(
                ((build_reel.CANVAS_W - handle_w) / 2, handle_y),
                build_reel.HANDLE.lower(),
                fill=legacy.SOFT_INK,
                font=hfont,
            )

            output_jpg.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(
                output_jpg,
                "JPEG",
                quality=94,
                optimize=True,
                progressive=True,
            )
            print(
                f"Finalized plain background: {preset['name']} "
                f"{preset['hex']} ({BACKGROUND_VERSION})"
            )
        except Exception as exc:
            print(f"Plain background fallback: {exc}")
            fallback_compose(quote, illustration_path, output_jpg)

    build_reel.compose_post = compose_post
