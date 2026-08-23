"""Locked visual system for Talks N Walks posts.

Every quote gets a newly generated AI background. Quote text, attribution and
the lower-case Instagram handle are added in code afterward so those elements
stay exact and consistent. No logo is added to posts.

The historical illustration library is not used for AI post artwork.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from PIL import Image, ImageDraw

from ai_visual import generate_background


QUOTE_COLOUR = "#171820"
ACCENT_COLOUR = "#A984B8"
QUOTE_LINE_SPACING = 10
MAX_QUOTE_LINES = 6
MAX_QUOTE_HEIGHT = 480
QUOTE_MAX_SIZE = 64
QUOTE_MIN_SIZE = 32
MAX_QUOTE_WIDTH = 880
AUTHOR_SIZE = 34
HANDLE_SIZE = 27


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


def _fit_quote(build_reel, draw, quote):
    display = f"“{quote.strip()}”"
    fallback = None
    for size in range(QUOTE_MAX_SIZE, QUOTE_MIN_SIZE - 1, -1):
        font = build_reel.find_font(size, serif=True)
        lines = _wrap_quote(draw, display, font, MAX_QUOTE_WIDTH)
        wrapped = "\n".join(lines)
        box = draw.multiline_textbbox(
            (0, 0),
            wrapped,
            font=font,
            spacing=QUOTE_LINE_SPACING,
            align="center",
        )
        width = box[2] - box[0]
        height = box[3] - box[1]
        fallback = (wrapped, font, width, height)
        if len(lines) <= MAX_QUOTE_LINES and height <= MAX_QUOTE_HEIGHT:
            return fallback
    return fallback


def _day_from_output(output_jpg: Path) -> int | None:
    match = re.search(r"day_(\d+)", output_jpg.stem, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _row_for_output(build_reel, output_jpg: Path) -> dict[str, str]:
    day = _day_from_output(output_jpg)
    if not day or not Path(build_reel.QUOTES_FILE).exists():
        return {}
    with Path(build_reel.QUOTES_FILE).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[day - 1] if 0 < day <= len(rows) else {}


def _attribution(row: dict[str, str]) -> str:
    source_type = (row.get("SourceType") or "").strip().lower()
    author = (row.get("Author") or "").strip()
    inspired_by = (row.get("InspiredBy") or "").strip()

    if source_type == "inspired_by" and (inspired_by or author):
        return f"Inspired by {inspired_by or author}"
    if author:
        return f"— {author}"
    return ""


def _lighten_text_zone(canvas: Image.Image) -> Image.Image:
    """Add only a very soft light veil; never a dark top gradient."""
    overlay = Image.new("RGBA", canvas.size, (255, 250, 246, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(
        (0, 0, canvas.width, int(canvas.height * 0.54)),
        fill=(255, 250, 246, 44),
    )
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _draw_divider(draw, center_x: int, y: int, font):
    line_w = 140
    gap = 28
    draw.line(
        (center_x - gap - line_w, y, center_x - gap, y),
        fill=ACCENT_COLOUR,
        width=2,
    )
    draw.line(
        (center_x + gap, y, center_x + gap + line_w, y),
        fill=ACCENT_COLOUR,
        width=2,
    )
    heart = "♡"
    box = draw.textbbox((0, 0), heart, font=font)
    draw.text(
        (center_x - (box[2] - box[0]) / 2, y - 18),
        heart,
        fill=ACCENT_COLOUR,
        font=font,
    )


def _prepare_placeholder(build_reel):
    """Keep the legacy builder contract without selecting an illustration."""
    build_reel.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = build_reel.OUTPUT_DIR / ".ai_visual_placeholder.png"
    build_reel.Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(placeholder)
    build_reel.ILLUSTRATION_DIR = Path(build_reel.OUTPUT_DIR)
    build_reel.ILLUSTRATIONS = [placeholder.name]


def apply_visual_theme(build_reel):
    """Install the Talks N Walks AI visual renderer without a logo overlay."""
    _prepare_placeholder(build_reel)

    def compose_post(quote, illustration_path, output_jpg):
        output_jpg = Path(output_jpg)
        row = _row_for_output(build_reel, output_jpg)
        audience = (row.get("Audience") or "All").strip()
        topic = (row.get("Topic") or row.get("Theme") or "Mindset").strip()
        author_line = _attribution(row)

        debug_background = output_jpg.with_name(output_jpg.stem + "_background.jpg")
        canvas = generate_background(
            quote,
            audience=audience,
            topic=topic,
            width=build_reel.CANVAS_W,
            height=build_reel.CANVAS_H,
            debug_path=debug_background,
        )
        canvas = _lighten_text_zone(canvas)
        draw = build_reel.ImageDraw.Draw(canvas)

        wrapped, quote_font, quote_w, quote_h = _fit_quote(build_reel, draw, quote)
        author_font = build_reel.find_font(AUTHOR_SIZE, serif=True)
        handle_font = build_reel.find_font(HANDLE_SIZE, serif=False)
        symbol_font = build_reel.find_font(32, serif=False)

        attribution_h = 0
        if author_line:
            box = draw.textbbox((0, 0), author_line, font=author_font)
            attribution_h = box[3] - box[1]

        handle = build_reel.HANDLE.lower()
        hbox = draw.textbbox((0, 0), handle, font=handle_font)
        handle_w = hbox[2] - hbox[0]
        handle_h = hbox[3] - hbox[1]

        divider_gap = 36
        author_gap = 28 if author_line else 10
        handle_gap = 30
        total_h = (
            quote_h
            + divider_gap
            + 28
            + author_gap
            + attribution_h
            + handle_gap
            + handle_h
        )
        block_top = max(220, int(620 - total_h / 2))

        quote_y = block_top
        draw.multiline_text(
            ((build_reel.CANVAS_W - quote_w) / 2, quote_y),
            wrapped,
            fill=QUOTE_COLOUR,
            font=quote_font,
            spacing=QUOTE_LINE_SPACING,
            align="center",
        )

        divider_y = quote_y + quote_h + divider_gap
        _draw_divider(draw, build_reel.CANVAS_W // 2, divider_y, symbol_font)

        cursor_y = divider_y + 28 + author_gap
        if author_line:
            abox = draw.textbbox((0, 0), author_line, font=author_font)
            author_w = abox[2] - abox[0]
            draw.text(
                ((build_reel.CANVAS_W - author_w) / 2, cursor_y),
                author_line,
                fill=QUOTE_COLOUR,
                font=author_font,
            )
            cursor_y += attribution_h

        cursor_y += handle_gap
        draw.text(
            ((build_reel.CANVAS_W - handle_w) / 2, cursor_y),
            handle,
            fill=ACCENT_COLOUR,
            font=handle_font,
        )

        output_jpg.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_jpg, "JPEG", quality=94, optimize=True, progressive=True)

    build_reel.compose_post = compose_post
