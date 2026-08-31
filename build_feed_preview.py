from __future__ import annotations

import csv
import math
import os
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
# - visible warm cream vignette/gradient
# - generous margins and vertical breathing room
# - readable supporting line
# - brown attribution, divider and handle
# - illustration centered above the divider
TEXT_PRIMARY = (23, 22, 20)
BROWN = (118, 76, 48)

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
CENTER_LIGHT = (255, 252, 246)


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


def wrap_text(draw, text: str, font, max_width: int) -> str:
    words = text.split()
    lines: list[str] = []
    current = ''
    for word in words:
        test = word if not current else f'{current} {word}'
        box = draw.textbbox((0, 0), test, font=font)
        if box[2] - box[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return '\n'.join(lines)


def fit_wrapped(draw, text: str, *, max_width: int, max_height: int, max_size: int, min_size: int, spacing: int):
    for size in range(max_size, min_size - 1, -1):
        font = find_font(size)
        wrapped = wrap_text(draw, text, font, max_width)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align='center')
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return wrapped, font, box[2] - box[0], box[3] - box[1]
    font = find_font(min_size)
    wrapped = wrap_text(draw, text, font, max_width)
    box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align='center')
    return wrapped, font, box[2] - box[0], box[3] - box[1]


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
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align='center')
    w = box[2] - box[0]
    draw.multiline_text(((CANVAS_W - w) / 2, y), text, font=font, fill=fill, spacing=spacing, align='center')
    return box[3] - box[1]


def build_background(edge_rgb: tuple[int, int, int]) -> Image.Image:
    """Soft luminous gradient with a near-white center and warm pastel perimeter."""
    image = Image.new('RGB', (CANVAS_W, CANVAS_H), edge_rgb)
    pixels = image.load()

    cx = CANVAS_W / 2
    cy = CANVAS_H * 0.44
    radius_x = CANVAS_W * 0.62
    radius_y = CANVAS_H * 0.72

    for y in range(CANVAS_H):
        dy = (y - cy) / radius_y
        for x in range(CANVAS_W):
            dx = (x - cx) / radius_x
            distance = min(1.0, math.sqrt(dx * dx + dy * dy))
            # Strong center lift, with a gentle warm falloff toward all edges.
            center_mix = 0.94 * (1.0 - distance) ** 1.55
            pixels[x, y] = tuple(
                round(edge_rgb[i] * (1.0 - center_mix) + CENTER_LIGHT[i] * center_mix)
                for i in range(3)
            )
    return image


def draw_attribution(draw, book: str, author: str, y: int, size: int = 25) -> int:
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
    draw.text(((CANVAS_W - author_w) / 2, author_y), author_text, font=regular, fill=BROWN)
    return line_h + 8 + author_h


def draw_bottom_divider(draw, y: int) -> None:
    half_line = 132
    center_x = CANVAS_W // 2
    draw.line(
        (center_x - half_line, y, center_x + half_line, y),
        fill=BROWN,
        width=2,
    )


def compose(row: dict[str, str], output_path: Path) -> None:
    bg = BACKGROUND_RGB.get((row.get('BackgroundFamily') or '').strip(), BACKGROUND_RGB['vanilla'])
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

    quote_wrapped, quote_font, _, _ = fit_wrapped(
        draw,
        quote,
        max_width=760,
        max_height=430,
        max_size=58,
        min_size=38,
        spacing=14,
    )
    support_font = find_font(30)
    handle_font = find_font(25)

    support_wrapped = wrap_text(draw, support, support_font, 760) if support else ''
    art = fit_art(art_path)
    handle_w, _ = text_size(draw, HANDLE, handle_font)

    # Match the approved reference proportions: generous top margin and stable
    # horizontal margins, without compressing the lower visual group upward.
    y = 150
    y += draw_centered_multiline(draw, quote_wrapped, y, quote_font, TEXT_PRIMARY, spacing=14)
    y += 50

    if support_wrapped:
        y += draw_centered_multiline(draw, support_wrapped, y, support_font, TEXT_PRIMARY, spacing=9)
        y += 46

    if source_type == 'inspired_by' and book and author:
        y += draw_attribution(draw, book, author, y, size=25)

    # Anchor the illustration independently so attribution length cannot squeeze it.
    art_y = max(y + 30, 825)
    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, art_y), art)

    divider_y = min(max(1115, art_y + art.height + 30), 1182)
    draw_bottom_divider(draw, divider_y)

    handle_y = divider_y + 22
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
        compose(row, output)
        print(output)


if __name__ == '__main__':
    main()
