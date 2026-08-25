"""Reference-style pastel watercolor botanical backgrounds for Talk N Walks reels.

Keeps the existing quote, illustration, handle and publishing behavior intact.
The background follows the approved reference look: an airy ivory center, soft
irregular watercolor washes around the outer edges, and layered botanical
clusters only in the top-right and bottom-left corners.
"""

from __future__ import annotations

import random

from PIL import ImageFilter

import legacy_visual_theme as legacy


BACKGROUND_VERSION = "watercolor-botanical-v5"

GENERAL_PRESETS = (
    {
        "name": "sage_blush",
        "base": (255, 253, 248),
        "wash_a": (211, 230, 214),
        "wash_b": (247, 219, 211),
        "wash_c": (234, 226, 198),
        "leaf_a": (151, 181, 156),
        "leaf_b": (211, 190, 154),
    },
    {
        "name": "soft_peach",
        "base": (255, 252, 246),
        "wash_a": (249, 218, 193),
        "wash_b": (244, 231, 201),
        "wash_c": (229, 236, 218),
        "leaf_a": (180, 191, 155),
        "leaf_b": (211, 175, 143),
    },
    {
        "name": "blush_lilac",
        "base": (255, 252, 249),
        "wash_a": (245, 218, 221),
        "wash_b": (229, 217, 243),
        "wash_c": (218, 233, 220),
        "leaf_a": (160, 187, 164),
        "leaf_b": (198, 177, 204),
    },
    {
        "name": "lilac_sage",
        "base": (254, 253, 249),
        "wash_a": (230, 220, 244),
        "wash_b": (216, 232, 217),
        "wash_c": (244, 225, 211),
        "leaf_a": (155, 183, 160),
        "leaf_b": (188, 173, 200),
    },
    {
        "name": "peach_gold",
        "base": (255, 252, 245),
        "wash_a": (248, 220, 192),
        "wash_b": (246, 232, 194),
        "wash_c": (218, 232, 215),
        "leaf_a": (165, 188, 157),
        "leaf_b": (210, 178, 137),
    },
    {
        "name": "coral_sage",
        "base": (255, 252, 248),
        "wash_a": (246, 219, 210),
        "wash_b": (215, 231, 216),
        "wash_c": (240, 229, 201),
        "leaf_a": (157, 184, 160),
        "leaf_b": (207, 174, 149),
    },
)

MEN_PRESETS = (
    {
        "name": "sage_mint",
        "base": (254, 253, 248),
        "wash_a": (211, 230, 214),
        "wash_b": (222, 237, 229),
        "wash_c": (239, 228, 204),
        "leaf_a": (143, 173, 148),
        "leaf_b": (184, 171, 138),
    },
    {
        "name": "soft_peach_sand",
        "base": (255, 252, 246),
        "wash_a": (247, 222, 200),
        "wash_b": (239, 229, 204),
        "wash_c": (219, 232, 218),
        "leaf_a": (157, 181, 157),
        "leaf_b": (201, 174, 141),
    },
    {
        "name": "powder_blue_teal",
        "base": (253, 254, 250),
        "wash_a": (213, 232, 236),
        "wash_b": (209, 230, 224),
        "wash_c": (239, 228, 205),
        "leaf_a": (128, 162, 161),
        "leaf_b": (183, 173, 140),
    },
    {
        "name": "sand_sage",
        "base": (255, 253, 248),
        "wash_a": (239, 227, 205),
        "wash_b": (214, 230, 214),
        "wash_c": (231, 219, 198),
        "leaf_a": (146, 173, 149),
        "leaf_b": (188, 165, 132),
    },
)


def _preset_for(stream: str, output_jpg):
    """Rotate presets by day so consecutive days use visibly different palettes."""
    day = max(1, legacy._day_number(output_jpg))
    normalized = (stream or "women").strip().lower()
    presets = MEN_PRESETS if normalized == "men" else GENERAL_PRESETS
    stream_offset = sum(ord(char) for char in normalized) % len(presets)
    return presets[((day - 1) + stream_offset) % len(presets)]


def _watercolor_cloud(
    build_reel,
    canvas,
    box,
    color,
    *,
    alpha=30,
    blur=34,
    seed=0,
    blobs=10,
):
    """Build a translucent, uneven watercolor patch with softly visible edges."""
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    rng = random.Random(seed)

    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)

    for index in range(blobs):
        blob_w = width * rng.uniform(0.34, 0.78)
        blob_h = height * rng.uniform(0.28, 0.70)
        cx = rng.uniform(x0, x1)
        cy = rng.uniform(y0, y1)
        local_alpha = max(8, alpha + rng.randint(-8, 8) - index // 3)
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


def _watercolor_bloom(
    build_reel,
    canvas,
    center,
    radius,
    color,
    *,
    alpha=26,
    seed=0,
):
    """Add a pale layered bloom so washes feel hand-painted, not geometric."""
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    cx, cy = center

    for index in range(9):
        rx = radius * rng.uniform(0.45, 1.05)
        ry = radius * rng.uniform(0.35, 0.90)
        ox = rng.randint(-int(radius * 0.34), int(radius * 0.34))
        oy = rng.randint(-int(radius * 0.34), int(radius * 0.34))
        local_alpha = max(7, alpha - index + rng.randint(-3, 3))
        draw.ellipse(
            (
                int(cx + ox - rx),
                int(cy + oy - ry),
                int(cx + ox + rx),
                int(cy + oy + ry),
            ),
            fill=(*color, local_alpha),
        )

    overlay = overlay.filter(ImageFilter.GaussianBlur(max(16, int(radius * 0.14))))
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
    leaf_scale=1.0,
    alpha=70,
):
    """Draw one soft translucent watercolor-style branch."""
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    sx, sy = start
    ex, ey = end

    draw.line((sx, sy, ex, ey), fill=(*secondary, min(92, alpha + 12)), width=2)

    for index, t in enumerate((0.14, 0.28, 0.43, 0.58, 0.73, 0.87)):
        x = sx + (ex - sx) * t
        y = sy + (ey - sy) * t
        side = -1 if (index + (1 if mirror else 0)) % 2 else 1
        color = primary if index % 2 == 0 else secondary

        rx = max(8, int((16 if index < 4 else 13) * leaf_scale))
        ry = max(18, int((43 if index < 4 else 35) * leaf_scale))
        angle = side * (0.60 if mirror else 0.72)
        leaf_x = x + side * (40 * leaf_scale)

        outer = legacy._leaf_points(leaf_x, y - 4, rx, ry, angle)
        draw.polygon(outer, fill=(*color, alpha))

        inner = legacy._leaf_points(
            leaf_x,
            y - 4,
            max(6, rx - 4),
            max(15, ry - 9),
            angle,
        )
        draw.polygon(inner, fill=(*color, max(18, alpha // 3)))

    softened = overlay.filter(ImageFilter.GaussianBlur(1.1))
    canvas = build_reel.Image.alpha_composite(canvas.convert("RGBA"), softened)
    canvas = build_reel.Image.alpha_composite(canvas, overlay)
    return canvas.convert("RGB")


def _build_background(build_reel, preset, *, stream: str, output_jpg):
    """Create an airy reference-style watercolor frame around a clean center."""
    canvas = build_reel.Image.new(
        "RGB",
        (build_reel.CANVAS_W, build_reel.CANVAS_H),
        preset["base"],
    )
    w, h = build_reel.CANVAS_W, build_reel.CANVAS_H
    day = max(1, legacy._day_number(output_jpg))
    normalized = (stream or "women").strip().lower()
    seed_base = f"{normalized}:{day}:{BACKGROUND_VERSION}"

    # Layer irregular washes around the outside edge. The middle 45-50% of
    # the canvas stays intentionally quiet, like the approved reference image.
    edge_clouds = (
        ((-210, -120, int(w * 0.34), int(h * 0.30)), "wash_a", 31, 38, "lt"),
        ((-230, int(h * 0.18), int(w * 0.30), int(h * 0.55)), "wash_b", 24, 42, "lm"),
        ((-220, int(h * 0.63), int(w * 0.34), h + 160), "wash_c", 29, 40, "lb"),
        ((int(w * 0.72), -120, w + 220, int(h * 0.39)), "wash_b", 28, 38, "rt"),
        ((int(w * 0.78), int(h * 0.26), w + 230, int(h * 0.68)), "wash_a", 22, 42, "rm"),
        ((int(w * 0.70), int(h * 0.70), w + 220, h + 170), "wash_a", 29, 40, "rb"),
    )
    for box, color_key, alpha, blur, suffix in edge_clouds:
        canvas = _watercolor_cloud(
            build_reel,
            canvas,
            box,
            preset[color_key],
            alpha=alpha,
            blur=blur,
            seed=f"{seed_base}:{suffix}",
            blobs=11,
        )

    # Larger translucent blooms give the soft overlapping watercolor-paper feel
    # visible in the reference without filling the quote area.
    blooms = (
        ((int(w * 0.10), int(h * 0.12)), int(w * 0.22), "wash_c", 19, "b1"),
        ((int(w * 0.08), int(h * 0.44)), int(w * 0.24), "wash_a", 17, "b2"),
        ((int(w * 0.88), int(h * 0.13)), int(w * 0.25), "wash_b", 20, "b3"),
        ((int(w * 0.91), int(h * 0.49)), int(w * 0.22), "wash_c", 16, "b4"),
        ((int(w * 0.12), int(h * 0.86)), int(w * 0.25), "wash_b", 19, "b5"),
        ((int(w * 0.88), int(h * 0.84)), int(w * 0.27), "wash_a", 20, "b6"),
    )
    for center, radius, color_key, alpha, suffix in blooms:
        canvas = _watercolor_bloom(
            build_reel,
            canvas,
            center,
            radius,
            preset[color_key],
            alpha=alpha,
            seed=f"{seed_base}:{suffix}",
        )

    # Build layered botanical clusters rather than a single decorative twig.
    # Top-right cluster.
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (w + 10, 38),
        (w - 270, 390),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=True,
        leaf_scale=1.18,
        alpha=57,
    )
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (w - 25, 115),
        (w - 360, 255),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=False,
        leaf_scale=0.88,
        alpha=45,
    )
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (w + 15, 285),
        (w - 225, 505),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=True,
        leaf_scale=0.78,
        alpha=37,
    )

    # Bottom-left cluster.
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (-10, h - 20),
        (300, h - 470),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=False,
        leaf_scale=1.20,
        alpha=59,
    )
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (20, h - 95),
        (350, h - 255),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=True,
        leaf_scale=0.88,
        alpha=44,
    )
    canvas = _botanical_branch(
        build_reel,
        canvas,
        (-15, h - 300),
        (235, h - 540),
        preset["leaf_a"],
        preset["leaf_b"],
        mirror=False,
        leaf_scale=0.78,
        alpha=36,
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
                f"Approved reference-style watercolor background: "
                f"{preset['name']} ({BACKGROUND_VERSION})"
            )
        except Exception as exc:
            print(f"Watercolor background fallback: {exc}")
            fallback_compose(quote, illustration_path, output_jpg)

    build_reel.compose_post = compose_post
