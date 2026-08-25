"""Approved pastel watercolor botanical backgrounds for Talk N Walks reels.

Keeps the existing quote, illustration, handle and publishing behavior intact.
Backgrounds are generated directly in the renderer so every build gets a
clearly pastel watercolor background with botanical detail only in the
top-right and bottom-left corners. The center remains clean for readability,
and the base pastel changes every day.
"""

from __future__ import annotations

import random

from PIL import ImageFilter

import legacy_visual_theme as legacy


BACKGROUND_VERSION = "watercolor-botanical-v4"

GENERAL_PRESETS = (
    {
        "name": "sage_blush",
        "base": (240, 247, 241),
        "wash_a": (211, 230, 214),
        "wash_b": (247, 219, 211),
        "leaf_a": (150, 180, 155),
        "leaf_b": (219, 185, 171),
    },
    {
        "name": "soft_peach",
        "base": (252, 239, 229),
        "wash_a": (249, 218, 193),
        "wash_b": (244, 231, 201),
        "leaf_a": (203, 166, 132),
        "leaf_b": (226, 185, 161),
    },
    {
        "name": "blush_lilac",
        "base": (247, 239, 246),
        "wash_a": (245, 218, 221),
        "wash_b": (229, 217, 243),
        "leaf_a": (191, 170, 205),
        "leaf_b": (220, 174, 184),
    },
    {
        "name": "lilac_sage",
        "base": (241, 240, 249),
        "wash_a": (230, 220, 244),
        "wash_b": (216, 232, 217),
        "leaf_a": (177, 164, 202),
        "leaf_b": (157, 184, 160),
    },
    {
        "name": "peach_gold",
        "base": (252, 243, 226),
        "wash_a": (248, 220, 192),
        "wash_b": (246, 232, 194),
        "leaf_a": (204, 169, 126),
        "leaf_b": (225, 181, 151),
    },
    {
        "name": "coral_sage",
        "base": (249, 239, 233),
        "wash_a": (246, 219, 210),
        "wash_b": (215, 231, 216),
        "leaf_a": (211, 159, 153),
        "leaf_b": (154, 181, 158),
    },
)

MEN_PRESETS = (
    {
        "name": "sage_mint",
        "base": (238, 246, 240),
        "wash_a": (211, 230, 214),
        "wash_b": (222, 237, 229),
        "leaf_a": (143, 173, 148),
        "leaf_b": (173, 195, 179),
    },
    {
        "name": "soft_peach_sand",
        "base": (249, 240, 227),
        "wash_a": (247, 222, 200),
        "wash_b": (239, 229, 204),
        "leaf_a": (190, 160, 124),
        "leaf_b": (207, 181, 148),
    },
    {
        "name": "powder_blue_teal",
        "base": (235, 245, 247),
        "wash_a": (213, 232, 236),
        "wash_b": (209, 230, 224),
        "leaf_a": (128, 162, 161),
        "leaf_b": (153, 181, 176),
    },
    {
        "name": "sand_sage",
        "base": (245, 241, 229),
        "wash_a": (239, 227, 205),
        "wash_b": (214, 230, 214),
        "leaf_a": (184, 159, 125),
        "leaf_b": (146, 173, 149),
    },
)


def _preset_for(stream: str, output_jpg):
    """Rotate presets by day so consecutive days never use the same base color."""
    day = max(1, legacy._day_number(output_jpg))
    normalized = (stream or "women").strip().lower()
    presets = MEN_PRESETS if normalized == "men" else GENERAL_PRESETS
    stream_offset = sum(ord(char) for char in normalized) % len(presets)
    return presets[((day - 1) + stream_offset) % len(presets)]


def _soft_wash(build_reel, canvas, box, color, *, alpha=30, blur=78, seed=0):
    """Layer translucent irregular blobs into one soft watercolor wash."""
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    rng = random.Random(seed)

    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)

    for index in range(8):
        scale_x = rng.uniform(0.50, 1.00)
        scale_y = rng.uniform(0.45, 1.00)
        blob_w = width * scale_x
        blob_h = height * scale_y
        cx = rng.uniform(x0 + blob_w * 0.25, x1 - blob_w * 0.15)
        cy = rng.uniform(y0 + blob_h * 0.20, y1 - blob_h * 0.15)
        local_alpha = max(7, alpha - index * 2 + rng.randint(-3, 4))
        draw.ellipse(
            (
                int(cx - blob_w / 2),
                int(cy - blob_h / 2),
                int(cx + blob_w / 2),
                int(cy + blob_h / 2),
            ),
            fill=(*color, local_alpha),
        )

    overlay = overlay.filter(ImageFilter.GaussianBlur(blur))
    return build_reel.Image.alpha_composite(
        canvas.convert("RGBA"), overlay
    ).convert("RGB")


def _watercolor_stroke(
    build_reel,
    canvas,
    start,
    end,
    color,
    *,
    alpha=38,
    width=145,
    blur=24,
    seed=0,
):
    """Paint a broad translucent watercolor brush stroke near a corner."""
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    rng = random.Random(seed)

    sx, sy = start
    ex, ey = end

    for index in range(5):
        jitter = 24 + index * 3
        offset_x = rng.randint(-jitter, jitter)
        offset_y = rng.randint(-jitter, jitter)
        line_alpha = max(8, alpha - index * 5)
        line_width = max(30, width - index * 18)
        draw.line(
            (
                sx + offset_x,
                sy + offset_y,
                ex + offset_x,
                ey + offset_y,
            ),
            fill=(*color, line_alpha),
            width=line_width,
        )

    overlay = overlay.filter(ImageFilter.GaussianBlur(blur))
    return build_reel.Image.alpha_composite(
        canvas.convert("RGBA"), overlay
    ).convert("RGB")


def _botanical_branch(
    build_reel,
    canvas,
    start,
    end,
    primary,
    secondary,
    *,
    mirror=False,
):
    """Draw one airy translucent botanical branch."""
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    sx, sy = start
    ex, ey = end

    draw.line((sx, sy, ex, ey), fill=(*secondary, 105), width=3)

    for index, t in enumerate((0.16, 0.30, 0.44, 0.59, 0.73, 0.87)):
        x = sx + (ex - sx) * t
        y = sy + (ey - sy) * t
        side = -1 if (index + (1 if mirror else 0)) % 2 else 1
        color = primary if index % 2 == 0 else secondary

        rx = 16 if index < 4 else 13
        ry = 44 if index < 4 else 36
        angle = side * (0.60 if mirror else 0.72)
        leaf_x = x + side * 42

        outer = legacy._leaf_points(leaf_x, y - 4, rx, ry, angle)
        draw.polygon(outer, fill=(*color, 88))

        inner = legacy._leaf_points(
            leaf_x,
            y - 4,
            max(8, rx - 4),
            max(21, ry - 9),
            angle,
        )
        draw.polygon(inner, fill=(*color, 30))

    softened = overlay.filter(ImageFilter.GaussianBlur(0.9))
    canvas = build_reel.Image.alpha_composite(canvas.convert("RGBA"), softened)
    canvas = build_reel.Image.alpha_composite(canvas, overlay)
    return canvas.convert("RGB")


def _build_background(build_reel, preset, *, stream: str, output_jpg):
    """Create the approved light watercolor botanical background."""
    canvas = build_reel.Image.new(
        "RGB",
        (build_reel.CANVAS_W, build_reel.CANVAS_H),
        preset["base"],
    )
    w, h = build_reel.CANVAS_W, build_reel.CANVAS_H
    day = max(1, legacy._day_number(output_jpg))
    normalized = (stream or "women").strip().lower()
    seed_base = f"{normalized}:{day}:{BACKGROUND_VERSION}"

    # Keep the central quote/illustration zone clean. All visible watercolor
    # lives predominantly in the two approved corners.
    canvas = _soft_wash(
        build_reel,
        canvas,
        (int(w * 0.55), -170, w + 260, int(h * 0.39)),
        preset["wash_a"],
        alpha=42,
        blur=82,
        seed=f"{seed_base}:tr-a",
    )
    canvas = _soft_wash(
        build_reel,
        canvas,
        (int(w * 0.67), -80, w + 170, int(h * 0.48)),
        preset["wash_b"],
        alpha=32,
        blur=72,
        seed=f"{seed_base}:tr-b",
    )
    canvas = _soft_wash(
        build_reel,
        canvas,
        (-260, int(h * 0.63), int(w * 0.46), h + 220),
        preset["wash_b"],
        alpha=43,
        blur=84,
        seed=f"{seed_base}:bl-a",
    )
    canvas = _soft_wash(
        build_reel,
        canvas,
        (-160, int(h * 0.73), int(w * 0.36), h + 120),
        preset["wash_a"],
        alpha=31,
        blur=70,
        seed=f"{seed_base}:bl-b",
    )

    # Broad translucent brush strokes make the watercolor visibly different
    # from the old flat beige/white background.
    canvas = _watercolor_stroke(
        build_reel,
        canvas,
        (int(w * 0.72), 40),
        (w + 65, 430),
        preset["wash_b"],
        alpha=44,
        width=165,
        blur=26,
        seed=f"{seed_base}:stroke-tr",
    )
    canvas = _watercolor_stroke(
        build_reel,
        canvas,
        (-70, h - 390),
        (int(w * 0.30), h + 35),
        preset["wash_a"],
        alpha=46,
        width=175,
        blur=28,
        seed=f"{seed_base}:stroke-bl",
    )

    canvas = _botanical_branch(
        build_reel,
        canvas,
        (w + 16, 18),
        (w - 245, 400),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=True,
    )
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (-18, h - 18),
        (265, h - 455),
        preset["leaf_a"],
        preset["leaf_b"],
    )
    return canvas


def apply_visual_theme(build_reel, *, stream: str = "women"):
    """Apply the approved watercolor botanical theme to the existing renderer."""
    legacy.apply_visual_theme(build_reel)
    fallback_compose = build_reel.compose_post

    def compose_post(quote, illustration_path, output_jpg):
        try:
            preset = _preset_for(stream, output_jpg)
            primary, secondary = legacy._palette_for_output(output_jpg)
            canvas = _build_background(
                build_reel,
                preset,
                stream=stream,
                output_jpg=output_jpg,
            )

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
                f"Approved watercolor botanical background: "
                f"{preset['name']} ({BACKGROUND_VERSION})"
            )
        except Exception as exc:
            print(f"Watercolor background fallback: {exc}")
            fallback_compose(quote, illustration_path, output_jpg)

    build_reel.compose_post = compose_post
