"""Build-only pastel workspace proof for Talks N Walks.

This replaces the rejected thumbnail/moodboard crop prototype with a single
real portrait scene stored as a repository asset. It is intentionally a proof
before expanding the pastel library. No logo is added.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from PIL import Image, ImageDraw

SCENE = Path("assets/pastel/workspace_proof.jpg")
QUOTE_COLOUR = "#25242a"
HANDLE_COLOUR = "#8b7186"
MAX_QUOTE_WIDTH = 870
QUOTE_MAX_SIZE = 62
QUOTE_MIN_SIZE = 34
LINE_SPACING = 10


def _day_from_output(output_jpg: Path) -> int | None:
    match = re.search(r"day_(\d+)", output_jpg.stem, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _row_for_output(build_reel, output_jpg: Path) -> dict[str, str]:
    day = _day_from_output(output_jpg)
    path = Path(build_reel.QUOTES_FILE)
    if not day or not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[day - 1] if 0 < day <= len(rows) else {}


def _attribution(row: dict[str, str]) -> str:
    source_type = (row.get("SourceType") or "").strip().lower()
    author = (row.get("Author") or "").strip()
    inspired_by = (row.get("InspiredBy") or "").strip()
    if source_type == "inspired_by" and (inspired_by or author):
        return f"Inspired by {inspired_by or author}"
    return f"— {author}" if author else ""


def _wrap(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
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
        lines = _wrap(draw, display, font, MAX_QUOTE_WIDTH)
        wrapped = "\n".join(lines)
        box = draw.multiline_textbbox(
            (0, 0), wrapped, font=font, spacing=LINE_SPACING, align="center"
        )
        fallback = (wrapped, font, box[2] - box[0], box[3] - box[1])
        if len(lines) <= 6 and fallback[3] <= 430:
            return fallback
    return fallback


def _text_veil(canvas: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    veil_h = int(canvas.height * 0.48)
    for y in range(veil_h):
        t = y / max(1, veil_h - 1)
        alpha = round(190 * (1 - t) + 25 * t)
        draw.line((0, y, canvas.width, y), fill=(255, 250, 247, alpha))
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _prepare_placeholder(build_reel):
    build_reel.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = build_reel.OUTPUT_DIR / ".pastel_workspace_placeholder.png"
    build_reel.Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(placeholder)
    build_reel.ILLUSTRATION_DIR = Path(build_reel.OUTPUT_DIR)
    build_reel.ILLUSTRATIONS = [placeholder.name]


def apply_pastel_visual_theme(build_reel, *, stream: str):
    """Install the single-scene pastel proof renderer. No logo."""
    _prepare_placeholder(build_reel)

    def compose_post(quote, illustration_path, output_jpg):
        if not SCENE.exists():
            raise FileNotFoundError(f"Pastel workspace proof asset missing: {SCENE}")

        output_jpg = Path(output_jpg)
        row = _row_for_output(build_reel, output_jpg)
        canvas = Image.open(SCENE).convert("RGB").resize(
            (build_reel.CANVAS_W, build_reel.CANVAS_H), Image.Resampling.LANCZOS
        )
        canvas = _text_veil(canvas)
        draw = build_reel.ImageDraw.Draw(canvas)

        wrapped, quote_font, quote_w, quote_h = _fit_quote(build_reel, draw, quote)
        quote_y = 235
        draw.multiline_text(
            ((build_reel.CANVAS_W - quote_w) / 2, quote_y),
            wrapped,
            fill=QUOTE_COLOUR,
            font=quote_font,
            spacing=LINE_SPACING,
            align="center",
        )

        cursor_y = quote_y + quote_h + 34
        author_line = _attribution(row)
        if author_line:
            author_font = build_reel.find_font(30, serif=True)
            box = draw.textbbox((0, 0), author_line, font=author_font)
            draw.text(
                ((build_reel.CANVAS_W - (box[2] - box[0])) / 2, cursor_y),
                author_line,
                fill=QUOTE_COLOUR,
                font=author_font,
            )
            cursor_y += (box[3] - box[1]) + 24

        handle = build_reel.HANDLE.lower()
        handle_font = build_reel.find_font(25, serif=False)
        hbox = draw.textbbox((0, 0), handle, font=handle_font)
        draw.text(
            ((build_reel.CANVAS_W - (hbox[2] - hbox[0])) / 2, cursor_y),
            handle,
            fill=HANDLE_COLOUR,
            font=handle_font,
        )

        output_jpg.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_jpg, "JPEG", quality=94, optimize=True, progressive=True)
        print("Pastel proof scene: unisex workspace; logo disabled.")

    build_reel.compose_post = compose_post
