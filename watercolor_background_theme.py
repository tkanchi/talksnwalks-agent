"""Reference-inspired pastel watercolor backgrounds for Talk N Walks reels.

Keeps the existing quote, illustration, handle and publishing behavior intact,
while replacing the flat/procedural canvas with a very light watercolor-paper
background family inspired by the approved botanical references: soft washes
around the edges, leaves in the top-right and bottom-left corners, and a clean
center for quote readability.

Men use a separate pastel subset without pink or lavender.
"""

from __future__ import annotations

import random

from PIL import ImageFilter

import legacy_visual_theme as legacy


BACKGROUND_VERSION = "watercolor-v2"

GENERAL_PRESETS = (
    {
        "name": "sage_blush",
        "base": (255, 253, 249),
        "wash_a": (218, 233, 220),
        "wash_b": (247, 225, 216),
        "leaf_a": (166, 188, 164),
        "leaf_b": (222, 195, 176),
    },
    {
        "name": "soft_peach",
        "base": (255, 252, 246),
        "wash_a": (250, 225, 205),
        "wash_b": (248, 235, 211),
        "leaf_a": (217, 177, 146),
        "leaf_b": (235, 197, 176),
    },
    {
        "name": "blush_lilac",
        "base": (255, 252, 250),
        "wash_a": (247, 225, 225),
        "wash_b": (232, 224, 245),
        "leaf_a": (201, 178, 211),
        "leaf_b": (225, 183, 190),
    },
    {
        "name": "lilac_pink",
        "base": (255, 252, 252),
        "wash_a": (232, 225, 248),
        "wash_b": (248, 224, 236),
        "leaf_a": (192, 167, 220),
        "leaf_b": (226, 177, 202),
    },
    {
        "name": "peach_gold",
        "base": (255, 253, 247),
        "wash_a": (250, 225, 201),
        "wash_b": (249, 237, 203),
        "leaf_a": (219, 180, 130),
        "leaf_b": (231, 186, 160),
    },
    {
        "name": "blush_coral",
        "base": (255, 252, 249),
        "wash_a": (248, 225, 218),
        "wash_b": (246, 235, 224),
        "leaf_a": (219, 163, 156),
        "leaf_b": (232, 187, 174),
    },
)

MEN_PRESETS = (
    {
        "name": "sage_mint",
        "base": (254, 253, 248),
        "wash_a": (217, 232, 218),
        "wash_b": (226, 239, 234),
        "leaf_a": (151, 177, 154),
        "leaf_b": (181, 201, 184),
    },
    {
        "name": "soft_peach_sand",
        "base": (255, 253, 247),
        "wash_a": (248, 229, 209),
        "wash_b": (240, 229, 205),
        "leaf_a": (198, 169, 132),
        "leaf_b": (211, 185, 151),
    },
    {
        "name": "powder_blue_teal",
        "base": (252, 254, 252),
        "wash_a": (220, 234, 237),
        "wash_b": (216, 233, 228),
        "leaf_a": (139, 170, 168),
        "leaf_b": (164, 188, 181),
    },
)


def _preset_for(stream: str, output_jpg):
    day = legacy._day_number(output_jpg)
    normalized = (stream or "women").strip().lower()
    presets = MEN_PRESETS if normalized == "men" else GENERAL_PRESETS
    # Deterministic pseudo-random choice: rebuilds of the same stream/day remain identical.
    return random.Random(f"{normalized}:{day}:{BACKGROUND_VERSION}").choice(presets)


def _soft_wash(build_reel, canvas, box, color, *, alpha=32, blur=72):
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = box
    draw.ellipse((x0, y0, x1, y1), fill=(*color, alpha))
    draw.ellipse(
        (x0 + 55, y0 + 25, x1 + 95, y1 - 40),
        fill=(*color, max(10, alpha // 2)),
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(blur))
    return build_reel.Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _watercolor_stroke(build_reel, canvas, box, color, *, alpha=28, blur=28):
    """Add a soft irregular watercolor stroke without filling the clean center."""
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)

    for index, scale in enumerate((1.00, 0.84, 0.68)):
        inset_x = int(width * (1.0 - scale) * 0.5)
        inset_y = int(height * (1.0 - scale) * 0.5)
        shift_x = 22 * index
        shift_y = -12 * index
        draw.ellipse(
            (
                x0 + inset_x + shift_x,
                y0 + inset_y + shift_y,
                x1 - inset_x + shift_x,
                y1 - inset_y + shift_y,
            ),
            fill=(*color, max(8, alpha - index * 7)),
        )

    overlay = overlay.filter(ImageFilter.GaussianBlur(blur))
    return build_reel.Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _botanical_branch(build_reel, canvas, start, end, primary, secondary, *, mirror=False):
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    sx, sy = start
    ex, ey = end
    draw.line((sx, sy, ex, ey), fill=(*secondary, 92), width=3)

    for index, t in enumerate((0.17, 0.31, 0.46, 0.61, 0.76, 0.90)):
        x = sx + (ex - sx) * t
        y = sy + (ey - sy) * t
        side = -1 if (index + (1 if mirror else 0)) % 2 else 1
        color = primary if index % 2 == 0 else secondary
        rx = 13 if index < 4 else 10
        ry = 38 if index < 4 else 30
        angle = side * (0.62 if mirror else 0.72)
        points = legacy._leaf_points(x + side * 35, y - 3, rx, ry, angle)
        draw.polygon(points, fill=(*color, 96))

        # A smaller translucent pass gives the leaves a softer watercolor feel.
        inner_points = legacy._leaf_points(
            x + side * 35,
            y - 3,
            max(7, rx - 3),
            max(20, ry - 7),
            angle,
        )
        draw.polygon(inner_points, fill=(*color, 38))

    softened = overlay.filter(ImageFilter.GaussianBlur(0.8))
    canvas = build_reel.Image.alpha_composite(canvas.convert("RGBA"), softened)
    canvas = build_reel.Image.alpha_composite(canvas, overlay)
    return canvas.convert("RGB")


def _build_background(build_reel, preset):
    canvas = build_reel.Image.new(
        "RGB", (build_reel.CANVAS_W, build_reel.CANVAS_H), preset["base"]
    )
    w, h = build_reel.CANVAS_W, build_reel.CANVAS_H

    # Keep the middle light, but make the approved watercolor edges clearly visible.
    canvas = _soft_wash(
        build_reel,
        canvas,
        (-240, -150, int(w * 0.50), int(h * 0.42)),
        preset["wash_a"],
        alpha=18,
        blur=96,
    )
    canvas = _soft_wash(
        build_reel,
        canvas,
        (int(w * 0.55), -180, w + 250, int(h * 0.42)),
        preset["wash_b"],
        alpha=39,
        blur=92,
    )
    canvas = _soft_wash(
        build_reel,
        canvas,
        (-250, int(h * 0.61), int(w * 0.49), h + 250),
        preset["wash_a"],
        alpha=42,
        blur=96,
    )
    canvas = _soft_wash(
        build_reel,
        canvas,
        (int(w * 0.69), int(h * 0.70), w + 220, h + 180),
        preset["wash_b"],
        alpha=16,
        blur=96,
    )

    # Layered watercolor strokes in the two locked botanical corners.
    canvas = _watercolor_stroke(
        build_reel,
        canvas,
        (int(w * 0.68), -60, w + 120, 430),
        preset["wash_a"],
        alpha=31,
        blur=34,
    )
    canvas = _watercolor_stroke(
        build_reel,
        canvas,
        (-130, h - 500, int(w * 0.34), h + 70),
        preset["wash_b"],
        alpha=33,
        blur=36,
    )

    # Locked botanical placement from the approved references.
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (w + 8, 15),
        (w - 205, 355),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=True,
    )
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (-8, h - 15),
        (230, h - 410),
        preset["leaf_a"],
        preset["leaf_b"],
    )
    return canvas


def apply_visual_theme(build_reel, *, stream: str = "women"):
    """Apply the approved light watercolor botanical background family."""
    # Install the proven renderer first so any unexpected error has a safe fallback.
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
                build_reel, canvas, handle_y, handle_w, handle_h, primary
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
            print(f"Watercolor background: {preset['name']} ({BACKGROUND_VERSION})")
        except Exception as exc:
            print(f"Watercolor background fallback: {exc}")
            fallback_compose(quote, illustration_path, output_jpg)

    build_reel.compose_post = compose_post
