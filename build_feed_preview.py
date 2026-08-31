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

# Keep the month-one pastel families, but render them as very light warm-edged
# gradients rather than flat fills. Vanilla is the approved reference look.
BACKGROUND_RGB = {
    'vanilla': (251, 232, 204),
    'seafoam': (226, 242, 232),
    'powder': (226, 238, 248),
    'blush': (248, 226, 228),
    'lavender': (237, 228, 247),
    'apricot': (252, 224, 198),
    'ice': (235, 245, 250),
    'mint': (231, 246, 235),
    'petal': (247, 226, 237),
    'sky': (226, 239, 249),
}
CENTER_LIGHT = (255, 253, 247)


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


def fit_art(path: Path, max_w: int = 170, max_h: int = 195) -> Image.Image:
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
    """Render the approved visible warm vignette: pale center, warmer edges."""
    image = Image.new('RGB', (CANVAS_W, CANVAS_H), edge_rgb)
    pixels = image.load()

    # Slightly above visual center so the quote sits in the brightest area.
    cx = CANVAS_W / 2
    cy = CANVAS_H * 0.43
    radius_x = CANVAS_W * 0.68
    radius_y = CANVAS_H * 0.69

    for y in range(CANVAS_H):
        dy = (y - cy) / radius_y
        for x in range(CANVAS_W):
            dx = (x - cx) / radius_x
            distance = min(1.0, math.sqrt(dx * dx + dy * dy))

            # Strong enough to be visibly gradient, still subtle/premium.
            light_mix = 0.82 * (1.0 - distance) ** 1.45
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

    # Narrower quote block is intentional: the approved proof has a tall,
    # editorial quote shape rather than a wide three-line banner.
    quote_wrapped, quote_font, _, quote_h = fit_wrapped(
        draw,
        quote,
        max_width=730,
        max_height=430,
        max_size=54,
        min_size=36,
        spacing=13,
    )
    support_font = find_font(29)
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

    # Spacing copied from the approved visual rhythm rather than centering the
    # entire group. The quote begins high enough to preserve the large lower
    # breathing area seen in the reference.
    quote_gap_bottom = 44
    support_gap_bottom = 42
    source_gap_bottom = 25
    art_gap_bottom = 24
    divider_gap_bottom = 18

    y = 165

    y += draw_centered_multiline(
        draw, quote_wrapped, y, quote_font, TEXT_PRIMARY, spacing=13
    )
    y += quote_gap_bottom

    if support_wrapped:
        y += draw_centered_multiline(
            draw, support_wrapped, y, support_font, TEXT_PRIMARY, spacing=8
        )
        y += support_gap_bottom

    if source_wrapped:
        y += draw_centered_multiline(
            draw, source_wrapped, y, source_font, TEXT_SECONDARY, spacing=7
        )
        y += source_gap_bottom

    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, int(y)), art)
    y += art.height + art_gap_bottom

    draw_bottom_divider(draw, int(y))
    y += divider_gap_bottom

    draw.text(
        ((CANVAS_W - handle_w) / 2, y),
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
