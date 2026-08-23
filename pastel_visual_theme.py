"""Locked offline pastel visual renderer for Talks N Walks.

Uses a small curated scene sprite derived from the approved visual moodboard.
No external image API and no historical illustration selection are required.
Quote text, attribution, handle, and fixed logo are composited deterministically.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from brand_logo import load_logo
from pastel_sprite_data import load_pastel_sprite


TILE_W = 105
TILE_H = 186
QUOTE_COLOUR = "#202027"
HANDLE_COLOUR = "#8B7186"
QUOTE_LINE_SPACING = 10
QUOTE_MAX_SIZE = 62
QUOTE_MIN_SIZE = 32
MAX_QUOTE_WIDTH = 870
MAX_QUOTE_LINES = 6
LOGO_SIZE = 82

SCENES = (
    {"name": "women_cozy_window", "tile": 0, "audience": "women", "tags": {"lifestyle", "rest", "peace", "home", "wellness", "coffee", "reading"}},
    {"name": "women_balcony", "tile": 1, "audience": "women", "tags": {"growth", "hope", "peace", "reflection", "travel", "mindset"}},
    {"name": "men_workspace", "tile": 2, "audience": "men", "tags": {"business", "career", "focus", "discipline", "planning", "leadership", "goals"}},
    {"name": "men_soft_gym", "tile": 3, "audience": "men", "tags": {"fitness", "health", "discipline", "strength", "wellness", "workout"}},
    {"name": "kids_tree_friendship", "tile": 4, "audience": "kids", "tags": {"friendship", "kindness", "family", "peace", "nature", "values"}},
    {"name": "kids_study", "tile": 5, "audience": "kids", "tags": {"study", "learning", "school", "focus", "youth", "goals"}},
    {"name": "all_garden_path", "tile": 6, "audience": "all", "tags": {"growth", "mindset", "peace", "goals", "hope", "nature", "courage"}},
    {"name": "all_beach_path", "tile": 7, "audience": "all", "tags": {"peace", "travel", "rest", "wellness", "hope", "nature", "lifestyle"}},
)

KEYWORDS = {
    "gym": "fitness", "workout": "fitness", "body": "health", "health": "health",
    "discipline": "discipline", "strong": "strength", "strength": "strength",
    "career": "career", "business": "business", "team": "leadership", "leader": "leadership",
    "work": "career", "focus": "focus", "goal": "goals", "goals": "goals",
    "study": "study", "school": "school", "learn": "learning", "learning": "learning",
    "friend": "friendship", "friends": "friendship", "kind": "kindness", "family": "family",
    "peace": "peace", "rest": "rest", "heal": "wellness", "hope": "hope",
    "grow": "growth", "growth": "growth", "travel": "travel", "journey": "travel",
    "read": "reading", "book": "reading", "coffee": "coffee", "home": "home",
}


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


def _tokens(row: dict[str, str], quote: str) -> set[str]:
    raw = " ".join((row.get("Topic", ""), row.get("Theme", ""), quote)).lower()
    words = set(re.findall(r"[a-z]+", raw))
    tokens = set(words)
    for word, tag in KEYWORDS.items():
        if word in words:
            tokens.add(tag)
    return tokens


def _audience_family(stream: str) -> set[str]:
    stream = stream.lower()
    if stream == "women":
        return {"women", "all"}
    if stream == "men":
        return {"men", "all"}
    if stream in {"children", "kids", "teens"}:
        return {"kids", "all"}
    return {"all"}


def _choose_scene(stream: str, row: dict[str, str], quote: str, day: int) -> dict:
    allowed = _audience_family(stream)
    quote_tokens = _tokens(row, quote)
    candidates = [scene for scene in SCENES if scene["audience"] in allowed]

    def score(scene):
        audience_bonus = 7 if scene["audience"] != "all" else 4
        overlap = len(scene["tags"] & quote_tokens) * 8
        return audience_bonus + overlap

    best_score = max(score(scene) for scene in candidates)
    best = [scene for scene in candidates if score(scene) == best_score]
    return best[(max(day, 1) - 1) % len(best)]


def _load_scene(scene: dict, width: int, height: int) -> Image.Image:
    sprite = load_pastel_sprite()
    tile = int(scene["tile"])
    left = (tile % 4) * TILE_W
    top = (tile // 4) * TILE_H
    crop = sprite.crop((left, top, left + TILE_W, top + TILE_H))

    scale = max(width / crop.width, height / crop.height)
    resized = crop.resize(
        (round(crop.width * scale), round(crop.height * scale)),
        Image.Resampling.LANCZOS,
    )
    x = max(0, (resized.width - width) // 2)
    y = max(0, (resized.height - height) // 2)
    result = resized.crop((x, y, x + width, y + height))
    return result.filter(ImageFilter.UnsharpMask(radius=0.7, percent=40, threshold=3))


def _soft_text_veil(canvas: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    veil_h = int(canvas.height * 0.48)
    for y in range(veil_h):
        t = y / max(1, veil_h - 1)
        alpha = round(176 * (1 - t) + 32 * t)
        draw.line((0, y, canvas.width, y), fill=(255, 251, 247, alpha))
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


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
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=QUOTE_LINE_SPACING, align="center")
        width = box[2] - box[0]
        height = box[3] - box[1]
        fallback = (wrapped, font, width, height)
        if len(lines) <= MAX_QUOTE_LINES and height <= 440:
            return fallback
    return fallback


def _attribution(row: dict[str, str]) -> str:
    source_type = (row.get("SourceType") or "").strip().lower()
    author = (row.get("Author") or "").strip()
    inspired_by = (row.get("InspiredBy") or "").strip()
    if source_type == "inspired_by" and (inspired_by or author):
        return f"Inspired by {inspired_by or author}"
    if author:
        return f"— {author}"
    return ""


def _prepare_placeholder(build_reel):
    build_reel.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = build_reel.OUTPUT_DIR / ".pastel_visual_placeholder.png"
    build_reel.Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(placeholder)
    build_reel.ILLUSTRATION_DIR = Path(build_reel.OUTPUT_DIR)
    build_reel.ILLUSTRATIONS = [placeholder.name]


def apply_pastel_visual_theme(build_reel, *, stream: str):
    """Install the locked no-API pastel scene renderer."""
    _prepare_placeholder(build_reel)

    def compose_post(quote, illustration_path, output_jpg):
        output_jpg = Path(output_jpg)
        day = _day_from_output(output_jpg) or 1
        row = _row_for_output(build_reel, output_jpg)
        scene = _choose_scene(stream, row, quote, day)

        canvas = _load_scene(scene, build_reel.CANVAS_W, build_reel.CANVAS_H)
        canvas = _soft_text_veil(canvas)
        draw = build_reel.ImageDraw.Draw(canvas)

        wrapped, quote_font, quote_w, quote_h = _fit_quote(build_reel, draw, quote)
        author_line = _attribution(row)
        author_font = build_reel.find_font(31, serif=True)
        handle_font = build_reel.find_font(25, serif=False)

        quote_y = 245
        draw.multiline_text(
            ((build_reel.CANVAS_W - quote_w) / 2, quote_y),
            wrapped,
            fill=QUOTE_COLOUR,
            font=quote_font,
            spacing=QUOTE_LINE_SPACING,
            align="center",
        )

        cursor_y = quote_y + quote_h + 40
        if author_line:
            box = draw.textbbox((0, 0), author_line, font=author_font)
            author_w = box[2] - box[0]
            draw.text(((build_reel.CANVAS_W - author_w) / 2, cursor_y), author_line, fill=QUOTE_COLOUR, font=author_font)
            cursor_y += (box[3] - box[1]) + 30
        else:
            cursor_y += 8

        handle = build_reel.HANDLE.lower()
        hbox = draw.textbbox((0, 0), handle, font=handle_font)
        handle_w = hbox[2] - hbox[0]
        handle_h = hbox[3] - hbox[1]
        draw.text(((build_reel.CANVAS_W - handle_w) / 2, cursor_y), handle, fill=HANDLE_COLOUR, font=handle_font)
        cursor_y += handle_h + 14

        logo = load_logo()
        logo.thumbnail((LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS)
        logo_x = (build_reel.CANVAS_W - logo.width) // 2
        canvas.paste(logo, (logo_x, int(cursor_y)), logo)

        output_jpg.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_jpg, "JPEG", quality=94, optimize=True, progressive=True)
        print(f"Pastel scene: {scene['name']}")

    build_reel.compose_post = compose_post
