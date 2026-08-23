"""Stable pre-AI visual styling for Talk N Walks production builds.

This module preserves the last known working illustration-based renderer so
scheduled publishing can continue without an external image-generation API.
The newer AI renderer remains available separately in ``visual_theme.py``.
"""

from collections import deque
import re


PASTEL_BACKGROUNDS = (
    "#F6E6E8",  # blush pink
    "#E8F1F5",  # powder blue
    "#E9F3E8",  # sage mint
    "#F4EEDC",  # soft butter
    "#EEE8F5",  # pale lavender
    "#F5E8DE",  # peach cream
    "#E5F2EF",  # soft aqua
    "#F2E7EC",  # dusty rose
    "#E9EDF6",  # periwinkle mist
    "#EFF1E2",  # pale olive
    "#F3E5DF",  # muted coral
    "#E6F0EB",  # eucalyptus mist
)
BACKGROUND_COLOR = PASTEL_BACKGROUNDS[0]
QUOTE_LINE_SPACING = 8
MAX_QUOTE_LINES = 4
MAX_QUOTE_HEIGHT = 300
WHITE_BACKGROUND_THRESHOLD = 248


def _background_for_output(output_jpg):
    match = re.search(r"day_(\d+)", output_jpg.stem, re.IGNORECASE)
    if not match:
        return BACKGROUND_COLOR
    day = int(match.group(1))
    return PASTEL_BACKGROUNDS[(day - 1) % len(PASTEL_BACKGROUNDS)]


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


def apply_visual_theme(build_reel):
    """Apply the last known working illustration-based visual theme."""

    def compose_post(quote, illustration_path, output_jpg):
        canvas = build_reel.Image.new(
            "RGB",
            (build_reel.CANVAS_W, build_reel.CANVAS_H),
            _background_for_output(output_jpg),
        )
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
            fill="black",
            font=qfont,
            spacing=QUOTE_LINE_SPACING,
            align="center",
        )

        art_x = (build_reel.CANVAS_W - art.width) // 2
        canvas.paste(art, (art_x, art_y), art)
        draw.text(
            ((build_reel.CANVAS_W - handle_w) / 2, handle_y),
            build_reel.HANDLE,
            fill="black",
            font=hfont,
        )

        output_jpg.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_jpg, "JPEG", quality=94, optimize=True, progressive=True)

    build_reel.compose_post = compose_post
