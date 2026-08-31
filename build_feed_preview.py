from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'data' / 'content_plan_month_01.csv'
ILLUSTRATION_DIR = ROOT / 'illustrations' / 'objects' / 'core'
OUTPUT_DIR = ROOT / 'outputs' / 'feed_preview'

CANVAS_W = 1080
CANVAS_H = 1350
HANDLE = '@talksnwalks101'
TEXT_PRIMARY = (78, 63, 54)
TEXT_SECONDARY = (110, 92, 82)
BACKGROUND_RGB = {
    'vanilla': (255, 248, 231),
    'seafoam': (232, 248, 241),
    'powder': (234, 244, 252),
    'blush': (252, 233, 237),
    'lavender': (243, 234, 251),
    'apricot': (255, 232, 209),
    'ice': (240, 249, 253),
    'mint': (233, 250, 239),
    'petal': (251, 229, 238),
    'sky': (231, 243, 252),
}


def find_font(size: int, serif: bool = True, italic: bool = False):
    if serif:
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf' if italic else '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf' if italic else '/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf',
        ]
    else:
        # The approved template uses a clean, slightly condensed sans-serif face.
        candidates = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
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
        font = find_font(size, serif=False)
        wrapped = wrap_text(draw, text, font, max_width)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align='center')
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return wrapped, font, box[2] - box[0], box[3] - box[1]
    font = find_font(min_size, serif=False)
    wrapped = wrap_text(draw, text, font, max_width)
    box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align='center')
    return wrapped, font, box[2] - box[0], box[3] - box[1]


def fit_art(path: Path, max_w: int = 150, max_h: int = 155) -> Image.Image:
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


def draw_divider(draw, y: int) -> None:
    """Approved thin divider with a small centered diamond."""
    center_x = CANVAS_W // 2
    inner_gap = 18
    half_line = 86
    draw.line((center_x - half_line, y, center_x - inner_gap, y), fill=TEXT_SECONDARY, width=1)
    draw.line((center_x + inner_gap, y, center_x + half_line, y), fill=TEXT_SECONDARY, width=1)
    diamond = [(center_x, y - 5), (center_x + 5, y), (center_x, y + 5), (center_x - 5, y)]
    draw.polygon(diamond, fill=TEXT_SECONDARY)


def compose(row: dict[str, str], output_path: Path) -> None:
    bg = BACKGROUND_RGB.get((row.get('BackgroundFamily') or '').strip(), BACKGROUND_RGB['vanilla'])
    canvas = Image.new('RGB', (CANVAS_W, CANVAS_H), bg)
    draw = ImageDraw.Draw(canvas)

    quote = (row.get('Quote') or '').strip()
    support = (row.get('SupportingText') or '').strip()
    source = (row.get('SourceLine') or '').strip()
    art_path = ILLUSTRATION_DIR / (row.get('Illustration') or '').strip()
    if not art_path.exists():
        raise FileNotFoundError(art_path)

    # Finalized main quote: clean condensed sans-serif, reduced scale, generous space.
    quote_wrapped, quote_font, _, quote_h = fit_wrapped(
        draw, quote, max_width=850, max_height=440, max_size=60, min_size=38, spacing=10
    )
    # Final review: supporting line and source line each increased by one point.
    support_font = find_font(31, serif=False)
    source_font = find_font(21, serif=False)
    handle_font = find_font(22, serif=False)

    support_wrapped = wrap_text(draw, support, support_font, 790) if support else ''
    source_wrapped = wrap_text(draw, source, source_font, 820) if source else ''
    support_box = draw.multiline_textbbox((0, 0), support_wrapped, font=support_font, spacing=8, align='center') if support_wrapped else (0, 0, 0, 0)
    source_box = draw.multiline_textbbox((0, 0), source_wrapped, font=source_font, spacing=6, align='center') if source_wrapped else (0, 0, 0, 0)
    support_h = support_box[3] - support_box[1]
    source_h = source_box[3] - source_box[1]

    art = fit_art(art_path)
    handle_w, handle_h = text_size(draw, HANDLE, handle_font)

    divider_gap_top = 28
    divider_h = 10
    divider_gap_bottom = 28
    support_gap_bottom = 30
    source_gap_bottom = 30
    art_gap_bottom = 18

    content_height = (
        quote_h + divider_gap_top + divider_h + divider_gap_bottom
        + support_h + (support_gap_bottom if support_h else 0)
        + source_h + (source_gap_bottom if source_h else 0)
        + art.height + art_gap_bottom + handle_h
    )

    # Keep the composition calm and centered with generous outer margins.
    y = max(85, int((CANVAS_H - content_height) / 2) - 8)

    y += draw_centered_multiline(draw, quote_wrapped, y, quote_font, TEXT_PRIMARY, spacing=10)
    y += divider_gap_top
    draw_divider(draw, int(y + divider_h / 2))
    y += divider_h + divider_gap_bottom

    if support_wrapped:
        y += draw_centered_multiline(draw, support_wrapped, y, support_font, TEXT_PRIMARY, spacing=8)
        y += support_gap_bottom

    if source_wrapped:
        y += draw_centered_multiline(draw, source_wrapped, y, source_font, TEXT_SECONDARY, spacing=6)
        y += source_gap_bottom

    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, int(y)), art)
    y += art.height + art_gap_bottom

    draw.text(((CANVAS_W - handle_w) / 2, y), HANDLE, font=handle_font, fill=TEXT_SECONDARY)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, 'PNG', optimize=True)


def main() -> None:
    with PLAN.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))[:8]
    if len(rows) != 8:
        raise RuntimeError(f'Expected at least 8 plan rows, found {len(rows)}')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(rows, start=1):
        qid = (row.get('QuoteID') or f'post_{index:02d}').strip()
        output = OUTPUT_DIR / f'{index:02d}_{qid}.png'
        compose(row, output)
        print(output)


if __name__ == '__main__':
    main()
