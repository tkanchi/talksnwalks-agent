"""Build Talk N Walks premium editorial carousel slides.

This stream is intentionally independent from the daily Women/Men builders.
It produces 1080x1350 (4:5) JPEG slides plus caption/manifest metadata.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

CANVAS_W = 1080
CANVAS_H = 1350
HANDLE = "@talksnwalks101"
LIBRARY_FILE = Path(os.getenv("CAROUSEL_LIBRARY", "data/carousels/carousel_library.json"))
OUTPUT_ROOT = Path(os.getenv("CAROUSEL_OUTPUT_DIR", "outputs/carousels"))
PUBLIC_ROOT = Path(os.getenv("CAROUSEL_PUBLIC_DIR", "public/carousels"))
START_DATE = date.fromisoformat(os.getenv("CAROUSEL_START_DATE", "2026-09-16"))
SCHEDULE_WEEKDAYS = {2, 5}  # Wednesday, Saturday
STYLE_VERSION = "premium-editorial-v2"

PALETTES = {
    "dusty_blue": {"hook": (205, 220, 230), "base": (247, 246, 241), "wash": (224, 234, 240), "accent": (81, 105, 121), "text": (48, 48, 46)},
    "sage": {"hook": (214, 226, 214), "base": (248, 247, 241), "wash": (227, 236, 224), "accent": (88, 108, 88), "text": (48, 50, 46)},
    "warm_peach": {"hook": (239, 216, 201), "base": (250, 246, 240), "wash": (247, 228, 216), "accent": (141, 92, 71), "text": (55, 47, 44)},
    "soft_lilac": {"hook": (224, 217, 235), "base": (249, 247, 243), "wash": (236, 229, 243), "accent": (105, 88, 124), "text": (52, 48, 55)},
    "ice_blue": {"hook": (213, 229, 237), "base": (247, 248, 244), "wash": (226, 238, 242), "accent": (75, 108, 126), "text": (47, 51, 52)},
    "sky_lilac": {"hook": (216, 225, 241), "base": (248, 247, 244), "wash": (229, 232, 246), "accent": (87, 99, 139), "text": (49, 49, 57)},
    "sand_blue": {"hook": (221, 221, 214), "base": (248, 246, 239), "wash": (230, 233, 231), "accent": (82, 99, 106), "text": (49, 50, 48)},
    "blush_cream": {"hook": (237, 219, 216), "base": (250, 246, 239), "wash": (247, 231, 226), "accent": (137, 89, 88), "text": (55, 47, 47)},
}

HOOK_WORDS = {"STOP", "DON'T", "DON’T", "NEVER", "BEFORE", "THIS", "NOBODY", "IF"}


def find_font(size: int, serif: bool = True, bold: bool = False, italic: bool = False):
    if serif:
        if bold:
            preferred = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
            fallback = "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf"
        elif italic:
            preferred = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
            fallback = "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf"
        else:
            preferred = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
            fallback = "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"
    else:
        preferred = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        fallback = "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"

    for name in (preferred, fallback):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def editorial_background(palette, *, hook=False, closing=False):
    """Create a warm editorial paper surface with one soft atmospheric wash."""
    base = palette["hook"] if hook else palette["base"]
    image = Image.new("RGB", (CANVAS_W, CANVAS_H), base)

    # A single restrained blurred wash gives depth without becoming decorative.
    wash_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    wash_draw = ImageDraw.Draw(wash_layer)
    wash = palette["wash"]
    if hook:
        wash_draw.ellipse((-280, 760, 850, 1630), fill=(*wash, 190))
    elif closing:
        wash_draw.ellipse((520, -260, 1370, 580), fill=(*wash, 145))
    else:
        wash_draw.ellipse((650, -240, 1320, 500), fill=(*wash, 105))
    wash_layer = wash_layer.filter(ImageFilter.GaussianBlur(95))
    image = Image.alpha_composite(image.convert("RGBA"), wash_layer).convert("RGB")

    # Very subtle paper grain so the background does not feel digitally flat.
    noise = Image.effect_noise((CANVAS_W, CANVAS_H), 5).convert("L")
    noise_rgba = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 0))
    noise_rgba.putalpha(noise.point(lambda p: max(0, min(15, abs(p - 128) // 6))))
    image = Image.alpha_composite(image.convert("RGBA"), noise_rgba).convert("RGB")
    return image


def wrap_to_width(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        box = draw.textbbox((0, 0), candidate, font=font)
        if box[2] - box[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def fit_text(draw, text, *, max_width, max_height, start_size, min_size, serif=True, bold=False, spacing=14):
    for size in range(start_size, min_size - 1, -2):
        font = find_font(size, serif=serif, bold=bold)
        wrapped = wrap_to_width(draw, text, font, max_width)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align="left")
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return wrapped, font, box
    font = find_font(min_size, serif=serif, bold=bold)
    wrapped = wrap_to_width(draw, text, font, max_width)
    box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align="left")
    return wrapped, font, box


def draw_left_multiline(draw, text, font, x, y, fill, spacing=14):
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=spacing, align="left")
    box = draw.multiline_textbbox((x, y), text, font=font, spacing=spacing, align="left")
    return box[3] - box[1]


def draw_footer(draw, palette):
    accent = palette["accent"]
    footer_font = find_font(21, serif=False)
    draw.line((104, 1215, 976, 1215), fill=mix(accent, (255, 255, 255), 0.55), width=2)
    draw.text((104, 1245), HANDLE, font=footer_font, fill=accent)


def render_hook(draw, carousel, slide, palette):
    text_color = palette["text"]
    accent = palette["accent"]
    topic_font = find_font(20, serif=False, bold=True)
    body_font = find_font(29, serif=False)

    topic = (carousel.get("Topic") or "TALK N WALKS").upper()
    draw.text((106, 112), topic, font=topic_font, fill=accent)
    draw.line((106, 158, 222, 158), fill=accent, width=3)

    title = slide["title"].strip()
    parts = title.split(maxsplit=1)
    first = parts[0].upper() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    y = 278
    if first in HOOK_WORDS and rest:
        hook_font = find_font(78, serif=False, bold=True)
        draw.text((106, y), parts[0], font=hook_font, fill=accent)
        y += 112
        wrapped, title_font, title_box = fit_text(
            draw,
            rest,
            max_width=820,
            max_height=480,
            start_size=76,
            min_size=54,
            serif=True,
            bold=True,
            spacing=16,
        )
    else:
        wrapped, title_font, title_box = fit_text(
            draw,
            title,
            max_width=820,
            max_height=560,
            start_size=78,
            min_size=54,
            serif=True,
            bold=True,
            spacing=16,
        )

    title_h = draw_left_multiline(draw, wrapped, title_font, 106, y, text_color, spacing=16)
    body_y = y + title_h + 70
    body = slide.get("body", "").strip()
    if body:
        body_wrapped = wrap_to_width(draw, body, body_font, 680)
        draw.multiline_text((106, body_y), body_wrapped, font=body_font, fill=mix(text_color, (255, 255, 255), 0.16), spacing=12)

    # Small swipe cue, deliberately quiet.
    cue_font = find_font(19, serif=False, bold=True)
    draw.text((806, 1245), "SWIPE  →", font=cue_font, fill=accent)


def render_lesson(draw, slide, index, total_lessons, palette):
    text_color = palette["text"]
    accent = palette["accent"]

    number_font = find_font(25, serif=False, bold=True)
    draw.text((106, 116), f"{index:02d}", font=number_font, fill=accent)
    draw.text((164, 116), f"/ {total_lessons:02d}", font=find_font(20, serif=False), fill=mix(accent, (255, 255, 255), 0.2))

    # Oversized ghost number adds editorial structure without an illustration.
    ghost_font = find_font(205, serif=True, bold=True)
    ghost = f"{index:02d}"
    ghost_fill = mix(palette["wash"], (255, 255, 255), 0.38)
    draw.text((770, 85), ghost, font=ghost_font, fill=ghost_fill)

    wrapped, title_font, title_box = fit_text(
        draw,
        slide["title"],
        max_width=760,
        max_height=360,
        start_size=64,
        min_size=48,
        serif=True,
        bold=False,
        spacing=16,
    )
    title_y = 340
    title_h = draw_left_multiline(draw, wrapped, title_font, 106, title_y, text_color, spacing=16)

    divider_y = title_y + title_h + 54
    draw.line((106, divider_y, 236, divider_y), fill=accent, width=4)

    body = slide.get("body", "").strip()
    if body:
        body_font = find_font(33, serif=False)
        body_wrapped = wrap_to_width(draw, body, body_font, 760)
        draw.multiline_text(
            (106, divider_y + 52),
            body_wrapped,
            font=body_font,
            fill=mix(text_color, (255, 255, 255), 0.12),
            spacing=16,
        )

    draw_footer(draw, palette)


def render_closing(draw, slide, palette):
    text_color = palette["text"]
    accent = palette["accent"]
    kicker_font = find_font(20, serif=False, bold=True)
    draw.text((106, 116), "KEEP THIS ONE", font=kicker_font, fill=accent)
    draw.line((106, 158, 222, 158), fill=accent, width=3)

    wrapped, title_font, title_box = fit_text(
        draw,
        slide["title"],
        max_width=820,
        max_height=450,
        start_size=74,
        min_size=54,
        serif=True,
        bold=True,
        spacing=17,
    )
    title_y = 350
    title_h = draw_left_multiline(draw, wrapped, title_font, 106, title_y, text_color, spacing=17)

    body = slide.get("body", "").strip()
    if body:
        body_font = find_font(31, serif=False)
        body_wrapped = wrap_to_width(draw, body, body_font, 720)
        draw.multiline_text((106, title_y + title_h + 72), body_wrapped, font=body_font, fill=accent, spacing=14)

    # A restrained closing rule anchors the composition.
    draw.line((106, 1120, 390, 1120), fill=accent, width=5)
    draw_footer(draw, palette)


def render_slide(carousel, slide, index, total, output_path):
    palette = PALETTES.get(carousel.get("Palette"), PALETTES["dusty_blue"])
    kind = slide.get("kind", "lesson")
    hook = kind == "hook"
    closing = kind == "closing"
    image = editorial_background(palette, hook=hook, closing=closing)
    draw = ImageDraw.Draw(image)

    if hook:
        render_hook(draw, carousel, slide, palette)
    elif closing:
        render_closing(draw, slide, palette)
    else:
        render_lesson(draw, slide, index, total - 2, palette)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "JPEG", quality=95, optimize=True, progressive=True)


def load_library():
    with LIBRARY_FILE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list) or not data:
        raise ValueError(f"Carousel library is empty: {LIBRARY_FILE}")
    return data


def scheduled_slot(target_date: date):
    if target_date < START_DATE:
        return 0
    count = 0
    cursor = START_DATE
    while cursor <= target_date:
        if cursor.weekday() in SCHEDULE_WEEKDAYS:
            count += 1
        cursor += timedelta(days=1)
    return max(0, count - 1)


def select_carousel(library):
    requested = os.getenv("CAROUSEL_ID", "").strip()
    if requested:
        for item in library:
            if item.get("CarouselID") == requested:
                return item
        raise ValueError(f"Unknown CAROUSEL_ID: {requested}")

    target_date = date.fromisoformat(os.getenv("CAROUSEL_DATE", date.today().isoformat()))
    return library[scheduled_slot(target_date) % len(library)]


def main():
    library = load_library()
    carousel = select_carousel(library)
    carousel_id = carousel["CarouselID"]
    slides = carousel.get("Slides") or []
    if len(slides) < 5 or len(slides) > 10:
        raise ValueError(f"{carousel_id} must contain 5-10 slides; found {len(slides)}")

    output_dir = OUTPUT_ROOT / carousel_id
    public_dir = PUBLIC_ROOT / carousel_id
    output_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    for idx, slide in enumerate(slides, start=1):
        filename = f"slide_{idx:02d}.jpg"
        render_slide(carousel, slide, idx - 1, len(slides), output_dir / filename)
        (public_dir / filename).write_bytes((output_dir / filename).read_bytes())

    caption = (carousel.get("Caption") or "").strip()
    (output_dir / "caption.txt").write_text(caption + "\n", encoding="utf-8")

    manifest = {
        "carousel_id": carousel_id,
        "audience": carousel.get("Audience"),
        "topic_category": carousel.get("TopicCategory"),
        "topic": carousel.get("Topic"),
        "goal": carousel.get("Goal"),
        "palette": carousel.get("Palette"),
        "style_version": STYLE_VERSION,
        "slide_count": len(slides),
        "public_files": [f"public/carousels/{carousel_id}/slide_{i:02d}.jpg" for i in range(1, len(slides) + 1)],
        "publish_ready": False,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "publish.env").write_text(
        f"CAROUSEL_ID={carousel_id}\nCAROUSEL_SLIDE_COUNT={len(slides)}\nCAROUSEL_PUBLISH_READY=false\n",
        encoding="utf-8",
    )
    print(f"Built {carousel_id}: {len(slides)} slides ({STYLE_VERSION}) -> {output_dir}")


if __name__ == "__main__":
    main()
