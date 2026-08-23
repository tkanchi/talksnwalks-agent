"""Stable illustration renderer with the locked Talks N Walks soft editorial theme.

All existing illustration PNGs remain the source library.  This compositor
restyles them at build time so every stream shares the same warm cream,
sage/peach watercolor aesthetic without regenerating or replacing the assets.
"""

from collections import deque
import math
import re

from PIL import ImageFilter


CANVAS_BACKGROUNDS = (
    "#FBF7EF",  # warm cream
    "#FAF4F0",  # blush cream
    "#F6F6EE",  # sage cream
    "#FBF3EA",  # peach cream
)
BACKGROUND_COLOR = CANVAS_BACKGROUNDS[0]

PALETTES = (
    ((205, 133, 111), (166, 176, 143)),  # peach + sage
    ((191, 151, 139), (151, 165, 142)),  # dusty blush + olive sage
    ((217, 170, 149), (175, 185, 158)),  # warm peach + light sage
    ((196, 158, 147), (145, 162, 143)),  # rose taupe + eucalyptus
)

CHARCOAL = (45, 43, 42)
SOFT_INK = (67, 63, 61)
WARM_PAPER = (250, 247, 239)
SOFT_GOLD = (201, 163, 88)

QUOTE_LINE_SPACING = 8
MAX_QUOTE_LINES = 4
MAX_QUOTE_HEIGHT = 300
WHITE_BACKGROUND_THRESHOLD = 248


def _day_number(output_jpg):
    match = re.search(r"day_(\d+)", output_jpg.stem, re.IGNORECASE)
    return int(match.group(1)) if match else 1


def _background_for_output(output_jpg):
    day = _day_number(output_jpg)
    return CANVAS_BACKGROUNDS[(day - 1) % len(CANVAS_BACKGROUNDS)]


def _palette_for_output(output_jpg):
    day = _day_number(output_jpg)
    return PALETTES[(day - 1) % len(PALETTES)]


def _blend(a, b, amount):
    amount = max(0.0, min(1.0, amount))
    return tuple(round(a[i] * (1 - amount) + b[i] * amount) for i in range(3))


def _wrap_quote(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        box = draw.textbbox((0, 0), candidate, font=font)
        if box[2] - box[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_quote(build_reel, draw, text):
    fallback = None
    for size in range(build_reel.QUOTE_MAX_SIZE, build_reel.QUOTE_MIN_SIZE - 1, -1):
        font = build_reel.find_font(size, serif=True)
        lines = _wrap_quote(draw, text, font, build_reel.MAX_QUOTE_WIDTH)
        wrapped = "\n".join(lines)
        box = draw.multiline_textbbox(
            (0, 0),
            wrapped,
            font=font,
            spacing=QUOTE_LINE_SPACING,
            align="center",
        )
        quote_w = box[2] - box[0]
        quote_h = box[3] - box[1]
        fallback = (wrapped, font, quote_w, quote_h)
        if (
            len(lines) <= MAX_QUOTE_LINES
            and quote_w <= build_reel.MAX_QUOTE_WIDTH
            and quote_h <= MAX_QUOTE_HEIGHT
        ):
            return fallback
    return fallback


def _remove_opaque_white_background(image):
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 255:
        return rgba

    width, height = rgba.size
    pixels = rgba.load()
    visited = bytearray(width * height)
    queue = deque()

    def add_if_background(x, y):
        index = y * width + x
        if visited[index]:
            return
        visited[index] = 1
        red, green, blue, _ = pixels[x, y]
        if (
            red >= WHITE_BACKGROUND_THRESHOLD
            and green >= WHITE_BACKGROUND_THRESHOLD
            and blue >= WHITE_BACKGROUND_THRESHOLD
        ):
            queue.append((x, y))

    for x in range(width):
        add_if_background(x, 0)
        if height > 1:
            add_if_background(x, height - 1)
    for y in range(1, max(1, height - 1)):
        add_if_background(0, y)
        if width > 1:
            add_if_background(width - 1, y)

    while queue:
        x, y = queue.popleft()
        red, green, blue, _ = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)

        if x > 0:
            add_if_background(x - 1, y)
        if x + 1 < width:
            add_if_background(x + 1, y)
        if y > 0:
            add_if_background(x, y - 1)
        if y + 1 < height:
            add_if_background(x, y + 1)

    return rgba


def _style_art(art, primary, secondary):
    """Soften existing artwork into a cream/sage/peach editorial watercolor look."""
    rgba = art.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size

    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue

            high = max(red, green, blue)
            low = min(red, green, blue)
            saturation = high - low
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue

            if luminance < 72:
                # Keep outlines elegant rather than heavy black.
                styled = _blend(CHARCOAL, primary, 0.06)
                new_alpha = min(alpha, 238)
            elif saturation > 34:
                # Existing colored assets keep their natural identity, but are
                # softened toward the locked pastel palette.
                softened = _blend((red, green, blue), WARM_PAPER, 0.24)
                accent = primary if (x + y) % 2 == 0 else secondary
                styled = _blend(softened, accent, 0.10)
                new_alpha = alpha
            elif luminance < 165:
                amount = (luminance - 72) / 93
                accent = primary if x < width * 0.55 else secondary
                styled = _blend(SOFT_INK, accent, 0.28 + 0.34 * amount)
                new_alpha = min(alpha, 228)
            else:
                # Enclosed white/grey clothing and props get a barely-there
                # watercolor tint instead of staying stark white.
                accent = primary if ((x // 50) + (y // 50)) % 2 == 0 else secondary
                styled = _blend(WARM_PAPER, accent, 0.16)
                new_alpha = min(alpha, 220)

            pixels[x, y] = (*styled, new_alpha)

    return rgba


def _watercolor_wash(build_reel, canvas, box, color, alpha=42, blur=42):
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = box
    # Several overlapping translucent shapes give a softer painted edge.
    draw.ellipse((x0, y0, x1, y1), fill=(*color, alpha))
    draw.ellipse(
        (x0 + 45, y0 - 25, x1 + 30, y1 - 55),
        fill=(*color, max(12, alpha // 2)),
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(blur))
    return build_reel.Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _leaf_points(cx, cy, rx, ry, angle):
    points = []
    for step in range(24):
        theta = 2 * math.pi * step / 24
        x = rx * math.cos(theta)
        y = ry * math.sin(theta)
        ca, sa = math.cos(angle), math.sin(angle)
        points.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return points


def _draw_botanicals(build_reel, canvas, primary, secondary):
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)

    # Lower-left branch, matching the approved editorial references.
    start = (30, canvas.height - 70)
    end = (220, canvas.height - 440)
    draw.line((*start, *end), fill=(*secondary, 145), width=4)
    for index, t in enumerate((0.18, 0.34, 0.50, 0.67, 0.83)):
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t
        side = -1 if index % 2 else 1
        color = secondary if index % 2 == 0 else primary
        points = _leaf_points(
            x + side * 42,
            y - 4,
            14,
            43,
            side * 0.72,
        )
        draw.polygon(points, fill=(*color, 115))

    # A much smaller upper-right hint keeps group/men/kids scenes uncluttered.
    start = (canvas.width - 30, 90)
    end = (canvas.width - 145, 300)
    draw.line((*start, *end), fill=(*secondary, 90), width=3)
    for index, t in enumerate((0.24, 0.50, 0.76)):
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t
        side = 1 if index % 2 else -1
        color = primary if index % 2 == 0 else secondary
        draw.polygon(
            _leaf_points(x + side * 28, y, 10, 31, side * 0.65),
            fill=(*color, 82),
        )

    # Sparse warm-gold paint flecks.
    for x, y, radius in (
        (205, canvas.height - 330, 4),
        (245, canvas.height - 295, 3),
        (canvas.width - 180, 275, 3),
        (canvas.width - 135, 235, 4),
    ):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*SOFT_GOLD, 120))

    return build_reel.Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _draw_handle_brush(build_reel, canvas, handle_y, handle_w, handle_h, primary):
    overlay = build_reel.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = build_reel.ImageDraw.Draw(overlay)
    pad_x = 38
    pad_y = 14
    x0 = (canvas.width - handle_w) / 2 - pad_x
    x1 = (canvas.width + handle_w) / 2 + pad_x
    y0 = handle_y - pad_y
    y1 = handle_y + handle_h + pad_y
    draw.rounded_rectangle(
        (x0, y0, x1, y1),
        radius=max(18, int((y1 - y0) / 2)),
        fill=(*primary, 62),
    )
    return build_reel.Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def apply_visual_theme(build_reel):
    """Apply the locked cream + sage/peach watercolor style to every illustration."""

    def compose_post(quote, illustration_path, output_jpg):
        primary, secondary = _palette_for_output(output_jpg)
        canvas = build_reel.Image.new(
            "RGB",
            (build_reel.CANVAS_W, build_reel.CANVAS_H),
            _background_for_output(output_jpg),
        )

        # Soft washes stay away from the quote area and add the gentle watercolor
        # feeling from the approved references.
        canvas = _watercolor_wash(
            build_reel,
            canvas,
            (
                int(build_reel.CANVAS_W * 0.58),
                int(build_reel.CANVAS_H * 0.34),
                build_reel.CANVAS_W + 120,
                int(build_reel.CANVAS_H * 0.78),
            ),
            primary,
            alpha=34,
            blur=54,
        )
        canvas = _watercolor_wash(
            build_reel,
            canvas,
            (
                -180,
                int(build_reel.CANVAS_H * 0.70),
                int(build_reel.CANVAS_W * 0.34),
                build_reel.CANVAS_H + 120,
            ),
            secondary,
            alpha=27,
            blur=48,
        )
        canvas = _draw_botanicals(build_reel, canvas, primary, secondary)

        draw = build_reel.ImageDraw.Draw(canvas)
        wrapped_quote, qfont, quote_w, quote_h = _fit_quote(build_reel, draw, quote)
        hfont = build_reel.find_font(build_reel.HANDLE_SIZE, serif=False)

        source_art = _remove_opaque_white_background(
            build_reel.Image.open(illustration_path)
        )
        art = build_reel.fit_inside(
            source_art,
            build_reel.ILLUSTRATION_MAX_W,
            build_reel.ILLUSTRATION_MAX_H,
        )
        art = _style_art(art, primary, secondary)

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
            fill=CHARCOAL,
            font=qfont,
            spacing=QUOTE_LINE_SPACING,
            align="center",
        )

        art_x = (build_reel.CANVAS_W - art.width) // 2
        canvas.paste(art, (art_x, art_y), art)

        canvas = _draw_handle_brush(
            build_reel, canvas, handle_y, handle_w, handle_h, primary
        )
        draw = build_reel.ImageDraw.Draw(canvas)
        draw.text(
            ((build_reel.CANVAS_W - handle_w) / 2, handle_y),
            build_reel.HANDLE.lower(),
            fill=SOFT_INK,
            font=hfont,
        )

        output_jpg.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_jpg, "JPEG", quality=94, optimize=True, progressive=True)

    build_reel.compose_post = compose_post
