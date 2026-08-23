"""Shared visual styling for Talk N Walks reel builders.

The visual layer is intentionally self-contained: builders no longer need to
match quotes to a growing illustration library. Each quote gets a clean,
neutral line-art motif generated from the quote itself, while the approved
pastel background, serif typography, spacing, and handle remain consistent.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


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
ART_W = 560
ART_H = 420
LINE_WIDTH = 4


def _background_for_output(output_jpg):
    """Choose a repeatable pastel from the Day number in the output filename."""
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
            (0, 0), wrapped, font=font, spacing=QUOTE_LINE_SPACING, align="center"
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


def _motif_variant(quote: str) -> int:
    """Return a stable visual variant without maintaining semantic match rules."""
    return hashlib.sha256(quote.encode("utf-8")).digest()[0] % 4


def _draw_neutral_motif(draw, quote: str, left: int, top: int):
    """Draw lightweight gender- and age-neutral line art for the quote card."""
    cx = left + ART_W // 2
    cy = top + ART_H // 2
    variant = _motif_variant(quote)

    if variant == 0:
        # Horizon / rising sun / open path.
        draw.arc((cx - 105, cy - 150, cx + 105, cy + 60), 195, 345, fill="black", width=LINE_WIDTH)
        draw.line((left + 80, cy + 35, left + ART_W - 80, cy + 35), fill="black", width=LINE_WIDTH)
        draw.line((cx - 42, cy + 35, cx - 8, top + ART_H - 35), fill="black", width=LINE_WIDTH)
        draw.line((cx + 42, cy + 35, cx + 8, top + ART_H - 35), fill="black", width=LINE_WIDTH)
    elif variant == 1:
        # Compass / direction / forward movement.
        r = 108
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="black", width=LINE_WIDTH)
        draw.line((cx, cy - 145, cx, cy + 145), fill="black", width=LINE_WIDTH)
        draw.line((cx - 145, cy, cx + 145, cy), fill="black", width=LINE_WIDTH)
        draw.polygon(((cx, cy - 92), (cx - 24, cy + 20), (cx, cy), (cx + 24, cy + 20)), outline="black")
    elif variant == 2:
        # Mountain / progress / perspective.
        draw.line((left + 70, top + ART_H - 70, cx - 55, top + 105), fill="black", width=LINE_WIDTH)
        draw.line((cx - 55, top + 105, cx + 20, top + 215), fill="black", width=LINE_WIDTH)
        draw.line((cx + 20, top + 215, cx + 85, top + 145), fill="black", width=LINE_WIDTH)
        draw.line((cx + 85, top + 145, left + ART_W - 70, top + ART_H - 70), fill="black", width=LINE_WIDTH)
        draw.ellipse((left + ART_W - 155, top + 55, left + ART_W - 105, top + 105), outline="black", width=LINE_WIDTH)
    else:
        # Orbit / balance / possibility.
        draw.ellipse((cx - 115, cy - 115, cx + 115, cy + 115), outline="black", width=LINE_WIDTH)
        draw.arc((cx - 185, cy - 70, cx + 185, cy + 70), 12, 168, fill="black", width=LINE_WIDTH)
        draw.arc((cx - 185, cy - 70, cx + 185, cy + 70), 192, 348, fill="black", width=LINE_WIDTH)
        draw.ellipse((cx + 150, cy - 16, cx + 174, cy + 8), fill="black")


def _prepare_placeholder(build_reel):
    """Keep the legacy builder contract without depending on illustration files."""
    build_reel.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = build_reel.OUTPUT_DIR / ".neutral_template.png"
    build_reel.Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(placeholder)
    build_reel.ILLUSTRATION_DIR = Path(build_reel.OUTPUT_DIR)
    build_reel.ILLUSTRATIONS = [placeholder.name]


def apply_visual_theme(build_reel):
    """Apply the shared pastel quote template with generated neutral line art."""
    _prepare_placeholder(build_reel)

    def compose_post(quote, illustration_path, output_jpg):
        canvas = build_reel.Image.new(
            "RGB",
            (build_reel.CANVAS_W, build_reel.CANVAS_H),
            _background_for_output(output_jpg),
        )
        draw = build_reel.ImageDraw.Draw(canvas)
        wrapped_quote, qfont, quote_w, quote_h = _fit_quote(build_reel, draw, quote)
        hfont = build_reel.find_font(build_reel.HANDLE_SIZE, serif=False)

        hbox = draw.textbbox((0, 0), build_reel.HANDLE, font=hfont)
        handle_w = hbox[2] - hbox[0]
        handle_h = hbox[3] - hbox[1]

        total_height = (
            quote_h
            + build_reel.QUOTE_TO_ART_GAP
            + ART_H
            + build_reel.ART_TO_HANDLE_GAP
            + handle_h
        )
        block_top = int(build_reel.BLOCK_CENTER_Y - total_height / 2)
        quote_y = block_top
        art_y = quote_y + quote_h + build_reel.QUOTE_TO_ART_GAP
        handle_y = art_y + ART_H + build_reel.ART_TO_HANDLE_GAP

        draw.multiline_text(
            ((build_reel.CANVAS_W - quote_w) / 2, quote_y),
            wrapped_quote,
            fill="black",
            font=qfont,
            spacing=QUOTE_LINE_SPACING,
            align="center",
        )

        _draw_neutral_motif(draw, quote, (build_reel.CANVAS_W - ART_W) // 2, art_y)

        draw.text(
            ((build_reel.CANVAS_W - handle_w) / 2, handle_y),
            build_reel.HANDLE,
            fill="black",
            font=hfont,
        )

        output_jpg.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_jpg, "JPEG", quality=94, optimize=True, progressive=True)

    build_reel.compose_post = compose_post
