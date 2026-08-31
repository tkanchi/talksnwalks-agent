from __future__ import annotations

import csv
import math
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'data' / 'content_plan_month_01.csv'
ILLUSTRATION_DIR = ROOT / 'illustrations' / 'objects' / 'core'
OUTPUT_DIR = ROOT / 'outputs' / 'feed_preview'

CANVAS_W = 1080
CANVAS_H = 1350
HANDLE = '@talksnwalks101'

# Locked 4:5 feed-post proof direction from the approved reference:
# - clean regular sans-serif quote
# - visible soft pastel vignette/gradient
# - vertically centered full content block
# - larger quote, support and attribution typography
# - brown attribution, divider and handle
# - illustration centered above the divider
TEXT_PRIMARY = (23, 22, 20)
BROWN = (118, 76, 48)

# Keep a consistent rhythm through the lower content blocks, with a deliberately
# larger pause between the main quote and supporting line.
GAP_QUOTE_TO_SUPPORT = 72
GAP_SUPPORT_TO_SOURCE = 44
GAP_SOURCE_TO_ART = 44
GAP_ART_TO_DIVIDER = 44
GAP_DIVIDER_TO_HANDLE = 44

# The center stays very light while the perimeter carries a visible warm pastel tint.
BACKGROUND_RGB = {
    'vanilla': (248, 220, 183),
    'seafoam': (216, 238, 224),
    'powder': (217, 233, 247),
    'blush': (247, 218, 222),
    'lavender': (232, 220, 246),
    'apricot': (250, 215, 183),
    'ice': (228, 241, 249),
    'mint': (223, 243, 231),
    'petal': (246, 219, 233),
    'sky': (217, 234, 248),
}
BACKGROUND_KEYS = list(BACKGROUND_RGB.keys())
CENTER_LIGHT = (255, 252, 246)


def resolve_background(family: str | None, index: int) -> tuple[int, int, int]:
    """Look up the requested background color, tolerating case/whitespace."""
    key = (family or '').strip().lower()
    if key in BACKGROUND_RGB:
        return BACKGROUND_RGB[key]
    return BACKGROUND_RGB[BACKGROUND_KEYS[index % len(BACKGROUND_KEYS)]]


def find_font(size: int, *, italic: bool = False):
    candidates = [
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf' if italic else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf' if italic else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_by_chars(text: str, width: int) -> str:
    """Wrap on word boundaries while keeping each line close to a character target."""
    return '\n'.join(
        textwrap.wrap(
            text,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def fit_char_wrapped(
    draw,
    text: str,
    *,
    char_width: int,
    max_height: int,
    max_size: int,
    min_size: int,
    spacing: int,
):
    wrapped = wrap_by_chars(text, char_width)
    for size in range(max_size, min_size - 1, -1):
        font = find_font(size)
        box = draw.multiline_textbbox(
            (0, 0), wrapped, font=font, spacing=spacing, align='center'
        )
        if box[3] - box[1] <= max_height:
            return wrapped, font, box[3] - box[1]
    font = find_font(min_size)
    box = draw.multiline_textbbox(
        (0, 0), wrapped, font=font, spacing=spacing, align='center'
    )
    return wrapped, font, box[3] - box[1]


def fit_art(path: Path, max_w: int = 225, max_h: int = 260) -> Image.Image:
    art = Image.open(path).convert('RGBA')
    bbox = art.getchannel('A').getbbox()
    if bbox:
        art = art.crop(bbox)
    ratio = min(max_w / art.width, max_h / art.height)
    size = (max(1, round(art.width * ratio)), max(1, round(art.height * ratio)))
    return art.resize(size, Image.Resampling.LANCZOS)


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_centered_multiline(draw, text, y, font, fill, spacing=10):
    box = draw.multiline_textbbox(
        (0, 0), text, font=font, spacing=spacing, align='center'
    )
    w = box[2] - box[0]
    draw.multiline_text(
        ((CANVAS_W - w) / 2, y),
        text,
        font=font,
        fill=fill,
        spacing=spacing,
        align='center',
    )
    return box[3] - box[1]


def measure_multiline_height(draw, text, font, spacing=10):
    if not text:
        return 0
    box = draw.multiline_textbbox(
        (0, 0), text, font=font, spacing=spacing, align='center'
    )
    return box[3] - box[1]


def build_background(edge_rgb: tuple[int, int, int]) -> Image.Image:
    """Soft luminous gradient with a broad light center and slimmer dark perimeter."""
    image = Image.new('RGB', (CANVAS_W, CANVAS_H), edge_rgb)
    pixels = image.load()

    cx = CANVAS_W / 2
    cy = CANVAS_H * 0.48
    radius_x = CANVAS_W * 0.82
    radius_y = CANVAS_H * 0.92

    for y in range(CANVAS_H):
        dy = (y - cy) / radius_y
        for x in range(CANVAS_W):
            dx = (x - cx) / radius_x
            distance = min(1.0, math.sqrt(dx * dx + dy * dy))
            center_mix = 0.97 * (1.0 - distance) ** 1.25
            pixels[x, y] = tuple(
                round(
                    edge_rgb[i] * (1.0 - center_mix)
                    + CENTER_LIGHT[i] * center_mix
                )
                for i in range(3)
            )
    return image


def measure_attribution_height(draw, book: str, author: str, size: int = 28) -> int:
    regular = find_font(size)
    italic = find_font(size, italic=True)
    _, prefix_h = text_size(draw, '— Inspired by ', regular)
    _, book_h = text_size(draw, book, italic)
    _, author_h = text_size(draw, f'by {author}', regular)
    return max(prefix_h, book_h) + 8 + author_h


def draw_attribution(draw, book: str, author: str, y: int, size: int = 28) -> int:
    regular = find_font(size)
    italic = find_font(size, italic=True)
    prefix = '— Inspired by '
    prefix_w, _ = text_size(draw, prefix, regular)
    book_w, line_h = text_size(draw, book, italic)
    total_w = prefix_w + book_w
    x = (CANVAS_W - total_w) / 2
    draw.text((x, y), prefix, font=regular, fill=BROWN)
    draw.text((x + prefix_w, y), book, font=italic, fill=BROWN)

    author_text = f'by {author}'
    author_w, author_h = text_size(draw, author_text, regular)
    author_y = y + line_h + 8
    draw.text(
        ((CANVAS_W - author_w) / 2, author_y),
        author_text,
        font=regular,
        fill=BROWN,
    )
    return line_h + 8 + author_h


def draw_bottom_divider(draw, y: int) -> None:
    half_line = 132
    center_x = CANVAS_W // 2
    draw.line(
        (center_x - half_line, y, center_x + half_line, y),
        fill=BROWN,
        width=2,
    )


def compose(row: dict[str, str], output_path: Path, index: int = 0) -> None:
    bg = resolve_background(row.get('BackgroundFamily'), index)
    canvas = build_background(bg)
    draw = ImageDraw.Draw(canvas)

    quote = (row.get('Quote') or '').strip()
    support = (row.get('SupportingText') or '').strip()
    source_type = (row.get('SourceType') or '').strip().lower()
    book = (row.get('InspiredBy') or '').strip()
    author = (row.get('Author') or '').strip()
    art_path = ILLUSTRATION_DIR / (row.get('Illustration') or '').strip()
    if not art_path.exists():
        raise FileNotFoundError(art_path)

    quote_wrapped, quote_font, quote_h = fit_char_wrapped(
        draw,
        quote,
        char_width=10,
        max_height=560,
        max_size=66,
        min_size=48,
        spacing=16,
    )
    support_font = find_font(34)
    handle_font = find_font(25)

    support_wrapped = wrap_by_chars(support, 20) if support else ''
    support_h = (
        measure_multiline_height(draw, support_wrapped, support_font, spacing=10)
        if support_wrapped
        else 0
    )
    art = fit_art(art_path)
    handle_w, handle_h = text_size(draw, HANDLE, handle_font)

    has_source = source_type == 'inspired_by' and book and author
    source_h = measure_attribution_height(draw, book, author, size=28) if has_source else 0

    total_h = quote_h
    if support_wrapped:
        total_h += GAP_QUOTE_TO_SUPPORT + support_h
    if has_source:
        total_h += GAP_SUPPORT_TO_SOURCE + source_h
    total_h += GAP_SOURCE_TO_ART + art.height
    total_h += GAP_ART_TO_DIVIDER + 2
    total_h += GAP_DIVIDER_TO_HANDLE + handle_h

    # Vertically center the complete composition rather than anchoring blocks separately.
    y = max(24, (CANVAS_H - total_h) // 2)

    y += draw_centered_multiline(
        draw,
        quote_wrapped,
        y,
        quote_font,
        TEXT_PRIMARY,
        spacing=16,
    )

    if support_wrapped:
        y += GAP_QUOTE_TO_SUPPORT
        y += draw_centered_multiline(
            draw,
            support_wrapped,
            y,
            support_font,
            TEXT_PRIMARY,
            spacing=10,
        )

    if has_source:
        y += GAP_SUPPORT_TO_SOURCE
        y += draw_attribution(draw, book, author, y, size=28)

    art_y = y + GAP_SOURCE_TO_ART
    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, art_y), art)

    divider_y = art_y + art.height + GAP_ART_TO_DIVIDER
    draw_bottom_divider(draw, divider_y)

    handle_y = divider_y + GAP_DIVIDER_TO_HANDLE
    draw.text(
        ((CANVAS_W - handle_w) / 2, handle_y),
        HANDLE,
        font=handle_font,
        fill=BROWN,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, 'PNG', optimize=True)


def main() -> None:
    count = max(1, int(os.getenv('PREVIEW_COUNT', '1')))
    with PLAN.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))[:count]
    if len(rows) != count:
        raise RuntimeError(f'Expected at least {count} plan rows, found {len(rows)}')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_DIR.glob('*.png'):
        old.unlink()

    for index, row in enumerate(rows, start=1):
        qid = (row.get('QuoteID') or f'post_{index:02d}').strip()
        output = OUTPUT_DIR / f'{index:02d}_{qid}.png'
        compose(row, output, index=index - 1)
        print(output)


if __name__ == '__main__':
    main()
