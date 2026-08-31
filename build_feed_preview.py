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

# Final feed-post visual reference approved in chat:
# clean sans quote, soft cream/pastel gradient, brown attribution/divider/handle,
# centered illustration near the bottom, generous whitespace.
TEXT_PRIMARY = (24, 22, 20)
TEXT_SECONDARY = (111, 72, 48)
BACKGROUND_RGB = {
    'vanilla': (255, 245, 226),
    'seafoam': (235, 247, 240),
    'powder': (236, 244, 250),
    'blush': (251, 237, 237),
    'lavender': (244, 237, 249),
    'apricot': (255, 235, 215),
    'ice': (242, 248, 251),
    'mint': (238, 249, 241),
    'petal': (250, 235, 242),
    'sky': (234, 243, 250),
}
CENTER_LIGHT = (255, 253, 248)


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


def fit_art(path: Path, max_w: int = 170, max_h: int = 200) -> Image.Image:
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
    image = Image.new('RGB', (CANVAS_W, CANVAS_H), edge_rgb)
    pixels = image.load()
    cx = CANVAS_W / 2
    cy = CANVAS_H * 0.47
    max_distance = math.hypot(CANVAS_W * 0.64, CANVAS_H * 0.64)

    for y in range(CANVAS_H):
        for x in range(CANVAS_W):
            distance = min(1.0, math.hypot(x - cx, y - cy) / max_distance)
            center_strength = 0.38 * (1.0 - distance) ** 1.8
            pixels[x, y] = tuple(
                round(edge_rgb[i] * (1.0 - center_strength) + CENTER_LIGHT[i] * center_strength)
                for i in range(3)
            )
    return image


def draw_bottom_divider(draw, y: int) -> None:
    half_line = 126
    center_x = CANVAS_W // 2
    draw.line((center_x - half_line, y, center_x + half_line, y), fill=TEXT_SECONDARY, width=2)


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

    quote_wrapped, quote_font, _, quote_h = fit_wrapped(
        draw, quote, max_width=820, max_height=420, max_size=56, min_size=36, spacing=12
    )
    support_font = find_font(30)
    source_font = find_font(25)
    handle_font = find_font(22)

    support_wrapped = wrap_text(draw, support, support_font, 790) if support else ''
    source_wrapped = ''
    if source_type == 'inspired_by' and book and author:
        source_wrapped = f'— Inspired by {book}\nby {author}'

    support_box = draw.multiline_textbbox((0, 0), support_wrapped, font=support_font, spacing=8, align='center') if support_wrapped else (0, 0, 0, 0)
    source_box = draw.multiline_textbbox((0, 0), source_wrapped, font=source_font, spacing=7, align='center') if source_wrapped else (0, 0, 0, 0)
    support_h = support_box[3] - support_box[1]
    source_h = source_box[3] - source_box[1]

    art = fit_art(art_path)
    handle_w, handle_h = text_size(draw, HANDLE, handle_font)

    quote_gap_bottom = 46
    support_gap_bottom = 44
    source_gap_bottom = 24
    art_gap_bottom = 24
    divider_gap_bottom = 20

    content_height = (
        quote_h + quote_gap_bottom
        + support_h + (support_gap_bottom if support_h else 0)
        + source_h + (source_gap_bottom if source_h else 0)
        + art.height + art_gap_bottom
        + 2 + divider_gap_bottom + handle_h
    )

    y = max(92, int((CANVAS_H - content_height) / 2) - 10)

    y += draw_centered_multiline(draw, quote_wrapped, y, quote_font, TEXT_PRIMARY, spacing=12)
    y += quote_gap_bottom

    if support_wrapped:
        y += draw_centered_multiline(draw, support_wrapped, y, support_font, TEXT_PRIMARY, spacing=8)
        y += support_gap_bottom

    if source_wrapped:
        y += draw_centered_multiline(draw, source_wrapped, y, source_font, TEXT_SECONDARY, spacing=7)
        y += source_gap_bottom

    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, int(y)), art)
    y += art.height + art_gap_bottom

    draw_bottom_divider(draw, int(y))
    y += divider_gap_bottom

    draw.text(((CANVAS_W - handle_w) / 2, y), HANDLE, font=handle_font, fill=TEXT_SECONDARY)

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
