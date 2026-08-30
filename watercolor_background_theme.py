"""Plain premium daily backgrounds for Talk N Walks reels.

Keeps the existing quote, illustration, handle and publishing behavior intact.
Backgrounds use quiet near-neutral solid fills chosen to support already-coloured
illustrations. No botanical shapes, fake leaves, gradients, watercolor blobs or
busy textures are drawn.
"""

from __future__ import annotations

import csv
from pathlib import Path

import legacy_visual_theme as legacy


BACKGROUND_VERSION = "muted-solid-v2"

# Finalized Talk N Walks palette. Coloured artwork uses the quieter neutrals
# below; sage/blush remain available for future controlled use but are not in
# the automatic production families.
PALETTE = (
    {"name": "warm_ivory", "hex": "#F3EFE7", "rgb": (243, 239, 231)},
    {"name": "soft_stone", "hex": "#E8E3DC", "rgb": (232, 227, 220)},
    {"name": "dusty_beige", "hex": "#E6DCCF", "rgb": (230, 220, 207)},
    {"name": "pale_taupe", "hex": "#DDD4CB", "rgb": (221, 212, 203)},
    {"name": "mist_grey", "hex": "#E4E6E3", "rgb": (228, 230, 227)},
    {"name": "muted_sage", "hex": "#DDE4DA", "rgb": (221, 228, 218)},
    {"name": "blue_grey", "hex": "#DEE4E8", "rgb": (222, 228, 232)},
    {"name": "soft_blush", "hex": "#E8DDDA", "rgb": (232, 221, 218)},
)
PALETTE_BY_NAME = {item["name"]: item for item in PALETTE}

SAFE_NEUTRALS = (
    "warm_ivory",
    "soft_stone",
    "dusty_beige",
    "pale_taupe",
    "mist_grey",
    "blue_grey",
)
WARM_ART_BACKGROUNDS = ("mist_grey", "blue_grey", "soft_stone")
COOL_ART_BACKGROUNDS = ("warm_ivory", "soft_stone", "dusty_beige", "pale_taupe")
BUSY_ART_BACKGROUNDS = ("warm_ivory", "mist_grey", "soft_stone")

SOURCE_FONT_SIZE = 20
SOURCE_TOP_GAP = 24
_SOURCE_METADATA_CACHE = None


def _classify_artwork(art):
    """Classify artwork broadly so the background supports rather than competes."""
    sample = art.convert("RGBA").copy()
    sample.thumbnail((96, 96))
    pixels = sample.load()

    warmth_total = 0.0
    saturation_total = 0.0
    count = 0

    for y in range(sample.height):
        for x in range(sample.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 24:
                continue
            if red > 245 and green > 245 and blue > 245:
                continue

            warmth_total += red - blue
            saturation_total += max(red, green, blue) - min(red, green, blue)
            count += 1

    if count == 0:
        return "neutral"

    average_warmth = warmth_total / count
    average_saturation = saturation_total / count

    if average_saturation >= 58:
        return "busy"
    if average_warmth >= 10:
        return "warm"
    if average_warmth <= -10:
        return "cool"
    return "neutral"


def _background_family(art):
    classification = _classify_artwork(art)
    if classification == "warm":
        return WARM_ART_BACKGROUNDS
    if classification == "cool":
        return COOL_ART_BACKGROUNDS
    if classification == "busy":
        return BUSY_ART_BACKGROUNDS
    return SAFE_NEUTRALS


def _preset_for(stream: str, output_jpg, art):
    """Rotate within an artwork-safe neutral family with a stable stream offset."""
    day = max(1, legacy._day_number(output_jpg))
    normalized = (stream or "women").strip().lower()
    family = _background_family(art)
    stream_offset = sum(ord(char) for char in normalized) % len(family)
    name = family[((day - 1) + stream_offset) % len(family)]
    return PALETTE_BY_NAME[name]


def _build_background(build_reel, preset):
    """Create a plain solid premium background with no decorative shapes."""
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
    """Return truthful on-art source text for the selected quote."""
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
            return f"Inspired by: {book} — {author}"
        return ""
    except Exception:
        return ""


def apply_visual_theme(build_reel, *, stream: str = "women"):
    """Apply the finalized plain muted background system to the existing renderer."""
    legacy.apply_visual_theme(build_reel)
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

            if source_label:
                source_box = draw.textbbox((0, 0), source_label, font=source_font)
                source_w = source_box[2] - source_box[0]
                source_y = quote_y + quote_h + SOURCE_TOP_GAP
                draw.text(
                    ((build_reel.CANVAS_W - source_w) / 2, source_y),
                    source_label,
                    fill=legacy.SOFT_INK,
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
                f"Finalized plain background: {preset['name']} "
                f"{preset['hex']} ({BACKGROUND_VERSION})"
            )
        except Exception as exc:
            print(f"Plain background fallback: {exc}")
            fallback_compose(quote, illustration_path, output_jpg)

    build_reel.compose_post = compose_post
