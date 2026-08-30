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


BACKGROUND_VERSION = "approved-pastel-v4"

# User-approved pastel families, intentionally lifted to cleaner/lighter tints.
# Do not introduce darker variants, black, charcoal or muddy near-neutrals as
# backgrounds. These values should stay pale enough for the quote to remain the
# visual focus while still giving each day a clear color identity.
PALETTE = (
    {"name": "vanilla", "hex": "#FFF8E7", "rgb": (255, 248, 231)},
    {"name": "butter", "hex": "#FFF2C2", "rgb": (255, 242, 194)},
    {"name": "lemon", "hex": "#FFF7C7", "rgb": (255, 247, 199)},
    {"name": "daffodil", "hex": "#FFF2B3", "rgb": (255, 242, 179)},
    {"name": "apricot", "hex": "#FFE8D1", "rgb": (255, 232, 209)},
    {"name": "peach", "hex": "#FFE2D2", "rgb": (255, 226, 210)},
    {"name": "melon", "hex": "#FFDCCA", "rgb": (255, 220, 202)},
    {"name": "seafoam", "hex": "#E8F8F1", "rgb": (232, 248, 241)},
    {"name": "mint", "hex": "#E9FAEF", "rgb": (233, 250, 239)},
    {"name": "aqua", "hex": "#E6F8F8", "rgb": (230, 248, 248)},
    {"name": "salmon", "hex": "#FFE0D8", "rgb": (255, 224, 216)},
    {"name": "coral", "hex": "#FFD9D1", "rgb": (255, 217, 209)},
    {"name": "blush", "hex": "#FCE9ED", "rgb": (252, 233, 237)},
    {"name": "petal", "hex": "#FBE5EE", "rgb": (251, 229, 238)},
    {"name": "rose", "hex": "#F8DFE7", "rgb": (248, 223, 231)},
    {"name": "wisteria", "hex": "#F1EAF9", "rgb": (241, 234, 249)},
    {"name": "lavender", "hex": "#F3EAFB", "rgb": (243, 234, 251)},
    {"name": "lilac", "hex": "#EEE7FA", "rgb": (238, 231, 250)},
    {"name": "ice", "hex": "#F0F9FD", "rgb": (240, 249, 253)},
    {"name": "powder", "hex": "#EAF4FC", "rgb": (234, 244, 252)},
    {"name": "sky", "hex": "#E7F3FC", "rgb": (231, 243, 252)},
    {"name": "azure", "hex": "#E5F1FB", "rgb": (229, 241, 251)},
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

SOURCE_FONT_SIZE = 20
QUOTE_TO_SOURCE_GAP = 24
SOURCE_TO_ART_GAP = 30
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
                quote_to_art = QUOTE_TO_SOURCE_GAP + source_h + SOURCE_TO_ART_GAP
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
                source_box = draw.textbbox((0, 0), source_label, font=source_font)
                source_w = source_box[2] - source_box[0]
                source_y = quote_y + quote_h + QUOTE_TO_SOURCE_GAP
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
