from __future__ import annotations

import csv
import os
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'data' / 'content_plan_month_01.csv'
ILLUSTRATION_DIR = ROOT / 'illustrations' / 'objects' / 'core'
OUTPUT_DIR = ROOT / 'outputs' / 'feed_preview'

CANVAS_W = 1080
CANVAS_H = 1080
HANDLE = '@talksnwalks101'

# Approved simplified square feed-post direction:
# - quote only; no supporting text
# - smaller main quote with longer line wrapping
# - quote -> illustration -> book/author -> handle
# - very light cream/ivory base with subtle uneven pastel patches
TEXT_PRIMARY = (23, 22, 20)
BROWN = (118, 76, 48)

GAP_QUOTE_TO_ART = 54
GAP_ART_TO_SOURCE = 40
GAP_SOURCE_TO_HANDLE = 38

# Unified daily-post background is locked to pure white.
BACKGROUND_RGB = {
    'vanilla': (255, 255, 255),
    'seafoam': (255, 255, 255),
    'powder': (255, 255, 255),
    'blush': (255, 255, 255),
    'lavender': (255, 255, 255),
    'apricot': (255, 255, 255),
    'ice': (255, 255, 255),
    'mint': (255, 255, 255),
    'petal': (255, 255, 255),
    'sky': (255, 255, 255),
}
BACKGROUND_KEYS = list(BACKGROUND_RGB.keys())
BASE_IVORY = (255, 252, 246)


def resolve_background(family: str | None, index: int) -> tuple[int, int, int]:
    key = (family or '').strip().lower()
    if key in BACKGROUND_RGB:
        return BACKGROUND_RGB[key]
    return BACKGROUND_RGB[BACKGROUND_KEYS[index % len(BACKGROUND_KEYS)]]


def find_font(size: int, *, italic: bool = False):
    candidates = [
        '/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf' if italic else '/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf' if italic else '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_by_chars(text: str, width: int) -> str:
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


def fit_art(path: Path, max_w: int = 205, max_h: int = 230) -> Image.Image:
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


def build_background(patch_rgb: tuple[int, int, int]) -> Image.Image:
    """Build the locked pure-white unified post background."""
    return Image.new('RGB', (CANVAS_W, CANVAS_H), (255, 255, 255))


def measure_attribution_height(draw, book: str, author: str, size: int = 25) -> int:
    regular = find_font(size)
    italic = find_font(size, italic=True)
    _, prefix_h = text_size(draw, 'Inspired by Book: ', regular)
    _, book_h = text_size(draw, book, italic)
    _, author_h = text_size(draw, f'{book} — {author}', regular)
    return max(prefix_h, book_h) + 8 + author_h


def draw_attribution(draw, book: str, author: str, y: int, size: int = 25) -> int:
    regular = find_font(size)
    italic = find_font(size, italic=True)
    label = 'Inspired by Book:'
    label_w, label_h = text_size(draw, label, italic)
    draw.text(((CANVAS_W - label_w) / 2, y), label, font=italic, fill=BROWN)

    source_text = f'{book} — {author}'
    source_w, source_h = text_size(draw, source_text, regular)
    source_y = y + label_h + 8
    draw.text(
        ((CANVAS_W - source_w) / 2, source_y),
        source_text,
        font=regular,
        fill=BROWN,
    )
    return label_h + 8 + source_h


def validate_quote_585(quote: str) -> None:
    words = re.findall(r"\b[\w]+(?:['’][\w]+)?\b", quote)
    count = len(words)
    if count < 5:
        raise ValueError(
            f"585 rule: quote has {count} words; single-post quotes need 5-8 words."
        )
    if count > 8:
        raise ValueError(
            f"585 rule: quote has {count} words; more than 8 words requires a carousel with a hook slide."
        )


def compose(row: dict[str, str], output_path: Path, index: int = 0) -> None:
    bg = resolve_background(row.get('BackgroundFamily'), index)
    canvas = build_background(bg)
    draw = ImageDraw.Draw(canvas)

    quote = (row.get('Quote') or '').strip()
    validate_quote_585(quote)
    source_type = (row.get('SourceType') or '').strip().lower()
    book = (row.get('InspiredBy') or '').strip()
    author = (row.get('Author') or '').strip()
    art_path = ILLUSTRATION_DIR / (row.get('Illustration') or '').strip()
    if not art_path.exists():
        raise FileNotFoundError(art_path)

    quote_wrapped, quote_font, quote_h = fit_char_wrapped(
        draw,
        quote,
        char_width=40,
        max_height=330,
        max_size=48,
        min_size=36,
        spacing=12,
    )
    art = fit_art(art_path)
    handle_font = find_font(22)
    handle_w, handle_h = text_size(draw, HANDLE, handle_font)

    has_source = source_type == 'inspired_by' and book and author
    source_h = measure_attribution_height(draw, book, author, size=25) if has_source else 0

    total_h = quote_h + GAP_QUOTE_TO_ART + art.height
    if has_source:
        total_h += GAP_ART_TO_SOURCE + source_h
    total_h += GAP_SOURCE_TO_HANDLE + handle_h

    y = max(30, (CANVAS_H - total_h) // 2)

    y += draw_centered_multiline(
        draw,
        quote_wrapped,
        y,
        quote_font,
        TEXT_PRIMARY,
        spacing=12,
    )

    art_y = y + GAP_QUOTE_TO_ART
    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, art_y), art)
    y = art_y + art.height

    if has_source:
        y += GAP_ART_TO_SOURCE
        y += draw_attribution(draw, book, author, y, size=25)

    handle_y = y + GAP_SOURCE_TO_HANDLE
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
