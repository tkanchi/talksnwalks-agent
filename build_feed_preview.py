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

# Final approved 4:5 feed-post direction:
# - clean regular sans-serif main quote
# - visible warm cream radial/vignette gradient
# - readable supporting line
# - brown source line, divider and handle
# - illustration centered near the bottom
TEXT_PRIMARY = (24, 22, 20)
TEXT_SECONDARY = (118, 74, 45)

# Very light edge tints. The center is intentionally near-white so every family
# keeps the same luminous gradient look as the approved cream reference.
BACKGROUND_RGB = {
    'vanilla': (254, 221, 181),
    'seafoam': (220, 241, 228),
    'powder': (220, 235, 249),
    'blush': (248, 220, 224),
    'lavender': (233, 221, 247),
    'apricot': (253, 218, 186),
    'ice': (230, 243, 250),
    'mint': (226, 246, 233),
    'petal': (247, 220, 235),
    'sky': (219, 236, 249),
}
CENTER_LIGHT = (255, 251, 244)


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


def fit_art(path: Path, max_w: int = 210, max_h: int = 245) -> Image.Image:
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
    """Visible premium vignette: near-white center and warm pastel perimeter."""
    image = Image.new('RGB', (CANVAS_W, CANVAS_H), edge_rgb)
    pixels = image.load()

    cx = CANVAS_W / 2
    cy = CANVAS_H * 0.47
    radius_x = CANVAS_W * 0.57
    radius_y = CANVAS_H * 0.64

    for y in range(CANVAS_H):
        dy = (y - cy) / radius_y
        for x in range(CANVAS_W):
            dx = (x - cx) / radius_x
            distance = min(1.0, math.sqrt(dx * dx + dy * dy))
            light_mix = 0.96 * (1.0 - distance) ** 1.30
            pixels[x, y] = tuple(
                round(edge_rgb[i] * (1.0 - light_mix) + CENTER_LIGHT[i] * light_mix)
                for i in range(3)
            )
    return image


def draw_bottom_divider(draw, y: int) -> None:
    half_line = 126
    center_x = CANVAS_W // 2
    draw.line(
        (center_x - half_line, y, center_x + half_line, y),
        fill=TEXT_SECONDARY,
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

    quote_wrapped, quote_font, _, quote_h = fit_wrapped(
        draw,
        quote,
        max_width=735,
        max_height=420,
        max_size=54,
        min_size=36,
        spacing=13,
    )
    support_font = find_font(30)
    source_font = find_font(24)
    handle_font = find_font(22)

    support_wrapped = wrap_text(draw, support, support_font, 760) if support else ''
    source_wrapped = ''
    if source_type == 'inspired_by' and book and author:
        source_wrapped = f'— Inspired by {book}\nby {author}'

    support_box = draw.multiline_textbbox(
        (0, 0), support_wrapped, font=support_font, spacing=8, align='center'
    ) if support_wrapped else (0, 0, 0, 0)
    source_box = draw.multiline_textbbox(
        (0, 0), source_wrapped, font=source_font, spacing=7, align='center'
    ) if source_wrapped else (0, 0, 0, 0)
    support_h = support_box[3] - support_box[1]
    source_h = source_box[3] - source_box[1]

    art = fit_art(art_path)
    handle_w, handle_h = text_size(draw, HANDLE, handle_font)

    # Upper typography follows the approved proof; the lower visual group is
    # deliberately anchored lower so the post does not collapse into the top half.
    y = 155
    y += draw_centered_multiline(
        draw, quote_wrapped, y, quote_font, TEXT_PRIMARY, spacing=13
    )
    y += 48

    if support_wrapped:
        y += draw_centered_multiline(
            draw, support_wrapped, y, support_font, TEXT_PRIMARY, spacing=8
        )
        y += 46

    if source_wrapped:
        y += draw_centered_multiline(
            draw, source_wrapped, y, source_font, TEXT_SECONDARY, spacing=7
        )

    # Keep the illustration in the lower-middle zone like the approved reference.
    natural_art_y = int(y + 36)
    art_y = max(natural_art_y, 790)
    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, art_y), art)

    # Bottom divider and handle are anchored, not squeezed directly after the art.
    divider_y = max(1095, art_y + art.height + 30)
    divider_y = min(divider_y, 1180)
    draw_bottom_divider(draw, divider_y)

    handle_y = divider_y + 22
    draw.text(
        ((CANVAS_W - handle_w) / 2, handle_y),
        HANDLE,
        font=handle_font,
        fill=TEXT_SECONDARY,
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
