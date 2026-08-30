"""Approved pastel daily backgrounds for Talk N Walks reels.

Keeps the existing quote, illustration, handle and publishing behavior intact.
Backgrounds use only the approved light pastel families. Quote/source/handle text
uses soft brown ink rather than black or charcoal. No botanical shapes, fake
leaves, gradients, watercolor blobs or busy textures are drawn.
"""

from __future__ import annotations

import csv
from pathlib import Path

import legacy_visual_theme as legacy


BACKGROUND_VERSION = "approved-pastel-v3"

# User-approved light pastel palette. Keep these shades light; do not introduce
# darker variants, black, charcoal or muddy near-neutrals as backgrounds.
PALETTE = (
    {"name": "vanilla", "hex": "#F8F3D9", "rgb": (248, 243, 217)},
    {"name": "butter", "hex": "#F7E7A9", "rgb": (247, 231, 169)},
    {"name": "lemon", "hex": "#F9F2B3", "rgb": (249, 242, 179)},
    {"name": "daffodil", "hex": "#F7ED9C", "rgb": (247, 237, 156)},
    {"name": "apricot", "hex": "#F9D8B0", "rgb": (249, 216, 176)},
    {"name": "peach", "hex": "#F8D0B0", "rgb": (248, 208, 176)},
    {"name": "melon", "hex": "#F7C7A8", "rgb": (247, 199, 168)},
    {"name": "seafoam", "hex": "#DDF3E4", "rgb": (221, 243, 228)},
    {"name": "mint", "hex": "#DDF7E3", "rgb": (221, 247, 227)},
    {"name": "aqua", "hex": "#D9F2F0", "rgb": (217, 242, 240)},
    {"name": "salmon", "hex": "#F8C1B4", "rgb": (248, 193, 180)},
    {"name": "coral", "hex": "#F7B7A8", "rgb": (247, 183, 168)},
    {"name": "blush", "hex": "#F8DADF", "rgb": (248, 218, 223)},
    {"name": "petal", "hex": "#F9D6E2", "rgb": (249, 214, 226)},
    {"name": "rose", "hex": "#F6C9D8", "rgb": (246, 201, 216)},
    {"name": "wisteria", "hex": "#E7DDF6", "rgb": (231, 221, 246)},
    {"name": "lavender", "hex": "#EADCF8", "rgb": (234, 220, 248)},
    {"name": "lilac", "hex": "#E4D8F5", "rgb": (228, 216, 245)},
    {"name": "ice", "hex": "#E8F4FB", "rgb": (232, 244, 251)},
    {"name": "powder", "hex": "#DDECF9", "rgb": (221, 236, 249)},
    {"name": "sky", "hex": "#D7EAFB", "rgb": (215, 234, 251)},
    {"name": "azure", "hex": "#D6E8FA", "rgb": (214, 232, 250)},
)
PALETTE_BY_NAME = {item["name"]: item for item in PALETTE}

WOMEN_BACKGROUNDS = tuple(item["name"] for item in PALETTE)
MEN_BACKGROUNDS = (
    "vanilla",
    "butter",
    "lemon",
    "daffodil",
    "apricot",
    "peach",
    "seafoam",
    "mint",
    "aqua",
    "ice",
    "powder",
    "sky",
    "azure",
)

# Soft brown ink: deliberately not black/charcoal.
TEXT_PRIMARY = (78, 63, 54)
TEXT_SECONDARY = (110, 92, 82)
SEPARATOR_COLOR = (140, 125, 115)

SOURCE_FONT_SIZE = 20
QUOTE_TO_SEPARATOR_GAP = 18
SEPARATOR_WIDTH = 6
SEPARATOR_HEIGHT = 6
SEPARATOR_TO_SOURCE_GAP = 14
SOURCE_TO_ART_GAP = 28
_SOURCE_METADATA_CACHE = None


def _preset_for(stream: str, output_jpg, art=None):
    """Rotate deterministically through the approved stream-specific palette."""
    day = max(1, legacy._day_number(output_jpg))
    normalized = (stream or "women").strip().lower()
    family = MEN_BACKGROUNDS if normalized == "men" else WOMEN_BACKGROUNDS
    stream_offset = sum(ord(char) for char in normalized) % len(family)
    name = family[((day - 1) + stream_offset) % len(family)]
    return PALETTE_BY_NAME[name]


def _build_background(build_reel, preset):
    """Create a plain solid approved pastel background."""
    return build_reel.Image.new(
        "RGB",
        (build_reel.CANVAS_W, build_reel.CANVAS_H),
        preset["rgb"],
    )


def _source_metadata():
    """Load source metadata once without changing the production quote selector."""
    global _SOURCE_METADATA_CACHE
    if _SOURCE_METADATA_CACHE is not None:
        return _SOURCE_METADATA_CACHE

    metadata = {}
    library_dir = Path("data/library")
    if library_dir.exists():
        for path in sorted(library_dir.glob("*.csv")):
            try:
                with path.open(newline="", encoding="utf-8") as handle:
                    for row in csv.DictReader(handle):
                        quote_id = (row.get("QuoteID") or "").strip()
                        if quote_id:
                            metadata[quote_id] = {
                                "SourceType": (row.get("SourceType") or "").strip(),
                                "InspiredBy": (row.get("InspiredBy") or "").strip(),
                                "Author": (row.get("Author") or "").strip(),
                            }
            except (OSError, csv.Error):
                continue

    _SOURCE_METADATA_CACHE = metadata
    return metadata


def _source_label(build_reel, output_jpg):
    """Return truthful book and author text for the selected inspired-by quote."""
    try:
        day = max(1, legacy._day_number(output_jpg))
        with build_reel.QUOTES_FILE.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if day > len(rows):
            return ""

        row = rows[day - 1]
        quote_id = (row.get("QuoteID") or "").strip()
        source_type = (row.get("SourceType") or "").strip().lower()
        metadata = _source_metadata().get(quote_id, {})
        book = (metadata.get("InspiredBy") or "").strip()
        author = (metadata.get("Author") or "").strip()

        if book and author and source_type == "inspired_by":
            return f"Inspired by Book: {book} — {author}"
        return ""
    except Exception:
        return ""


def apply_visual_theme(build_reel, *, stream: str = "women"):
    """Apply the finalized light pastel background system to the existing renderer."""
    legacy.apply_visual_theme(build_reel)

    # Keep even the legacy emergency fallback away from black/charcoal text.
    legacy.CHARCOAL = TEXT_PRIMARY
    legacy.SOFT_INK = TEXT_SECONDARY
    fallback_compose = build_reel.compose_post

    def compose_post(quote, illustration_path, output_jpg):
        try:
            source_art = legacy._remove_opaque_white_background(
                build_reel.Image.open(illustration_path)
            )
            preset = _preset_for(stream, output_jpg, source_art)
            primary, _ = legacy._palette_for_output(output_jpg)
            canvas = _build_background(build_reel, preset)

            draw = build_reel.ImageDraw.Draw(canvas)
            wrapped_quote, qfont, quote_w, quote_h = legacy._fit_quote(
                build_reel, draw, quote
            )
            hfont = build_reel.find_font(build_reel.HANDLE_SIZE, serif=False)
            source_font = build_reel.find_font(SOURCE_FONT_SIZE, serif=False)
            source_label = _source_label(build_reel, output_jpg)

            art = build_reel.fit_inside(
                source_art,
                build_reel.ILLUSTRATION_MAX_W,
                build_reel.ILLUSTRATION_MAX_H,
            )
            # Coloured illustrations are already approved artwork. Preserve their
            # original colours instead of re-tinting them with the legacy palette.

            hbox = draw.textbbox((0, 0), build_reel.HANDLE, font=hfont)
            handle_w = hbox[2] - hbox[0]
            handle_h = hbox[3] - hbox[1]

            source_h = 0
            if source_label:
                source_box = draw.textbbox((0, 0), source_label, font=source_font)
                source_h = source_box[3] - source_box[1]
                quote_to_art = (
                    QUOTE_TO_SEPARATOR_GAP
                    + SEPARATOR_HEIGHT
                    + SEPARATOR_TO_SOURCE_GAP
                    + source_h
                    + SOURCE_TO_ART_GAP
                )
            else:
                quote_to_art = build_reel.QUOTE_TO_ART_GAP

            total_height = (
                quote_h
                + quote_to_art
                + art.height
                + build_reel.ART_TO_HANDLE_GAP
                + handle_h
            )
            block_top = int(build_reel.BLOCK_CENTER_Y - total_height / 2)
            quote_y = block_top
            art_y = quote_y + quote_h + quote_to_art
            handle_y = art_y + art.height + build_reel.ART_TO_HANDLE_GAP

            draw.multiline_text(
                ((build_reel.CANVAS_W - quote_w) / 2, quote_y),
                wrapped_quote,
                fill=TEXT_PRIMARY,
                font=qfont,
                spacing=legacy.QUOTE_LINE_SPACING,
                align="center",
            )

            if source_label:
                separator_y = quote_y + quote_h + QUOTE_TO_SEPARATOR_GAP
                separator_x1 = (build_reel.CANVAS_W - SEPARATOR_WIDTH) // 2
                separator_x2 = separator_x1 + SEPARATOR_WIDTH
                draw.rounded_rectangle(
                    (
                        separator_x1,
                        separator_y,
                        separator_x2,
                        separator_y + SEPARATOR_HEIGHT,
                    ),
                    radius=3,
                    fill=SEPARATOR_COLOR,
                )

                source_box = draw.textbbox((0, 0), source_label, font=source_font)
                source_w = source_box[2] - source_box[0]
                source_y = (
                    separator_y
                    + SEPARATOR_HEIGHT
                    + SEPARATOR_TO_SOURCE_GAP
                )
                draw.text(
                    ((build_reel.CANVAS_W - source_w) / 2, source_y),
                    source_label,
                    fill=TEXT_SECONDARY,
                    font=source_font,
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
                fill=TEXT_SECONDARY,
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
                f"Approved pastel background: {preset['name']} "
                f"{preset['hex']} ({BACKGROUND_VERSION})"
            )
        except Exception as exc:
            print(f"Approved pastel background fallback: {exc}")
            fallback_compose(quote, illustration_path, output_jpg)

    build_reel.compose_post = compose_post
