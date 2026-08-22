"""Shared visual styling for Talk N Walks reel builders.

Keeps the approved cream background and monochrome layout while safely
wrapping longer quotes from the expanded content libraries.
"""

BACKGROUND_COLOR = "#F4F1EA"
QUOTE_LINE_SPACING = 8
MAX_QUOTE_LINES = 4
MAX_QUOTE_HEIGHT = 300


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


def apply_visual_theme(build_reel):
    """Apply the approved visual theme without changing the legacy builder."""

    def compose_post(quote, illustration_path, output_jpg):
        canvas = build_reel.Image.new(
            "RGB",
            (build_reel.CANVAS_W, build_reel.CANVAS_H),
            BACKGROUND_COLOR,
        )
        draw = build_reel.ImageDraw.Draw(canvas)
        wrapped_quote, qfont, quote_w, quote_h = _fit_quote(build_reel, draw, quote)
        hfont = build_reel.find_font(build_reel.HANDLE_SIZE, serif=False)

        art = build_reel.fit_inside(
            build_reel.Image.open(illustration_path),
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
