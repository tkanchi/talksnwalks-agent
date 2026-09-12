from __future__ import annotations

import csv
import os
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from background_generator import generate_background

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'data' / 'content_plan_month_01.csv'
ILLUSTRATION_DIR = ROOT / 'illustrations' / 'objects' / 'core'
OUTPUT_DIR = ROOT / 'outputs' / 'feed_preview'

CANVAS_W = 1080
CANVAS_H = 1350
HANDLE = '@talksnwalks101'

# Approved simplified 4:5 feed-post direction:
# - quote is the visual hero, with restrained keyword emphasis
# - illustration is a small supporting accent, never a large bottom block
# - selector placement (bottom_left / bottom_right / bottom_center) is respected
# - quote -> illustration -> book/author -> handle
# - very light cream/ivory base with subtle uneven pastel patches
TEXT_PRIMARY = (0, 0, 0)
BROWN = (0, 0, 0)
HIGHLIGHT_RGB = (143, 91, 68)

GAP_QUOTE_TO_ART = 46
GAP_ART_TO_SOURCE = 34
GAP_SOURCE_TO_HANDLE = 34
ART_SIDE_MARGIN = 92

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

HIGHLIGHT_PRIORITY = {
    'action', 'begin', 'believe', 'become', 'becoming', 'brave', 'bravery',
    'change', 'choice', 'choose', 'confidence', 'consistent', 'consistency',
    'courage', 'discipline', 'dream', 'dreams', 'enough', 'focus', 'freedom',
    'grow', 'growing', 'growth', 'heal', 'healing', 'hope', 'kindness',
    'learn', 'learning', 'love', 'peace', 'progress', 'purpose', 'resilience',
    'rest', 'start', 'strength', 'trust', 'worthy', 'worth',
}
HIGHLIGHT_STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'but', 'by', 'can',
    'do', 'for', 'from', 'had', 'has', 'have', 'he', 'her', 'his', 'i', 'if',
    'in', 'is', 'it', 'its', 'me', 'more', 'my', 'no', 'not', 'of', 'on',
    'or', 'our', 'she', 'so', 'than', 'that', 'the', 'their', 'them', 'then',
    'there', 'they', 'this', 'to', 'too', 'up', 'us', 'was', 'we', 'were',
    'what', 'when', 'where', 'which', 'who', 'will', 'with', 'you', 'your',
}


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
    max_width: int,
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
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return wrapped, font, box[3] - box[1]
    font = find_font(min_size)
    box = draw.multiline_textbbox(
        (0, 0), wrapped, font=font, spacing=spacing, align='center'
    )
    return wrapped, font, box[3] - box[1]


def fit_art(path: Path, max_w: int = 175, max_h: int = 190) -> Image.Image:
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


def normalized_word(token: str) -> str:
    match = re.search(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", token)
    return match.group(0).casefold() if match else ''


def choose_highlight_words(text: str, limit: int = 3) -> set[str]:
    ordered: list[str] = []
    for token in re.findall(r"\b[\w]+(?:['’][\w]+)?\b", text):
        word = token.casefold()
        if word not in ordered:
            ordered.append(word)

    chosen = [word for word in ordered if word in HIGHLIGHT_PRIORITY][:limit]

    if len(chosen) < min(2, limit):
        candidates = [
            word for word in ordered
            if word not in HIGHLIGHT_STOPWORDS
            and word not in chosen
            and len(word) >= 4
        ]
        candidates.sort(key=lambda word: (-len(word), ordered.index(word)))
        for word in candidates:
            chosen.append(word)
            if len(chosen) >= min(2, limit):
                break

    if len(chosen) < limit:
        candidates = [
            word for word in ordered
            if word not in HIGHLIGHT_STOPWORDS
            and word not in chosen
            and len(word) >= 5
        ]
        candidates.sort(key=lambda word: (-len(word), ordered.index(word)))
        for word in candidates:
            chosen.append(word)
            if len(chosen) >= limit:
                break

    return set(chosen[:limit])


def draw_highlighted_multiline(
    draw,
    text: str,
    y: int,
    font,
    *,
    spacing: int = 14,
    highlight_words: set[str] | None = None,
) -> int:
    highlights = highlight_words or set()
    lines = text.splitlines()
    sample_box = draw.textbbox((0, 0), 'Ag', font=font)
    line_h = sample_box[3] - sample_box[1]
    cursor_y = y

    for line in lines:
        tokens = re.findall(r'\S+|\s+', line)
        widths = [draw.textlength(token, font=font) for token in tokens]
        cursor_x = (CANVAS_W - sum(widths)) / 2
        for token, width in zip(tokens, widths):
            word = normalized_word(token)
            fill = HIGHLIGHT_RGB if word in highlights else TEXT_PRIMARY
            draw.text((cursor_x, cursor_y), token, font=font, fill=fill)
            cursor_x += width
        cursor_y += line_h + spacing

    return max(0, len(lines) * line_h + max(0, len(lines) - 1) * spacing)


def build_background(
    patch_rgb: tuple[int, int, int],
    *,
    family: str | None = None,
    index: int = 0,
) -> Image.Image:
    """Build a subtle deterministic pattern while preserving the existing API."""
    return generate_background(
        CANVAS_W,
        CANVAS_H,
        family=(family or 'vanilla'),
        index=index,
    )


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
            f"Feed quote has {count} words; use a complete thought rather than an overly short fragment."
        )
    if count > 32 or len(quote) > 180:
        raise ValueError(
            f"Feed quote is too long for the 4:5 single-post layout ({count} words, {len(quote)} characters)."
        )


def illustration_x(placement: str, art_width: int) -> int:
    placement = (placement or '').strip().lower()
    if placement == 'bottom_left':
        return ART_SIDE_MARGIN
    if placement == 'bottom_right':
        return CANVAS_W - ART_SIDE_MARGIN - art_width
    return (CANVAS_W - art_width) // 2


def compose(row: dict[str, str], output_path: Path, index: int = 0) -> None:
    family = (row.get('BackgroundFamily') or 'vanilla').strip().lower()
    bg = resolve_background(family, index)
    canvas = build_background(bg, family=family, index=index)
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
        char_width=34,
        max_width=900,
        max_height=390,
        max_size=60,
        min_size=42,
        spacing=14,
    )
    highlight_words = choose_highlight_words(quote)
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

    y += draw_highlighted_multiline(
        draw,
        quote_wrapped,
        y,
        quote_font,
        spacing=14,
        highlight_words=highlight_words,
    )

    art_y = y + GAP_QUOTE_TO_ART
    placement = (row.get('Placement') or 'bottom_center').strip().lower()
    art_x = illustration_x(placement, art.width)
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
