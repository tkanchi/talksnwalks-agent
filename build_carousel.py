"""Build Talk N Walks editorial carousel slides from the carousel library.

This stream is intentionally independent from the daily Women/Men builders.
It produces 1080x1350 (4:5) JPEG slides plus caption/manifest metadata.
"""

from __future__ import annotations

import json
import os
import textwrap
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_W = 1080
CANVAS_H = 1350
HANDLE = "@talksnwalks101"
LIBRARY_FILE = Path(os.getenv("CAROUSEL_LIBRARY", "data/carousels/carousel_library.json"))
OUTPUT_ROOT = Path(os.getenv("CAROUSEL_OUTPUT_DIR", "outputs/carousels"))
PUBLIC_ROOT = Path(os.getenv("CAROUSEL_PUBLIC_DIR", "public/carousels"))
START_DATE = date.fromisoformat(os.getenv("CAROUSEL_START_DATE", "2026-09-16"))
SCHEDULE_WEEKDAYS = {2, 5}  # Wednesday, Saturday

PALETTES = {
    "dusty_blue": {"hook": (211, 224, 233), "base": (242, 246, 247), "glow": (252, 249, 242), "accent": (90, 111, 125), "text": (54, 59, 61)},
    "sage": {"hook": (218, 229, 218), "base": (243, 247, 240), "glow": (253, 250, 241), "accent": (96, 116, 95), "text": (57, 61, 55)},
    "warm_peach": {"hook": (239, 217, 203), "base": (250, 241, 233), "glow": (255, 250, 242), "accent": (145, 99, 79), "text": (63, 55, 51)},
    "soft_lilac": {"hook": (226, 219, 236), "base": (247, 243, 249), "glow": (253, 250, 243), "accent": (111, 94, 128), "text": (59, 55, 64)},
    "ice_blue": {"hook": (216, 232, 240), "base": (242, 249, 251), "glow": (254, 251, 243), "accent": (82, 115, 132), "text": (51, 61, 65)},
    "sky_lilac": {"hook": (218, 226, 243), "base": (244, 246, 252), "glow": (253, 249, 244), "accent": (92, 105, 146), "text": (54, 57, 70)},
    "sand_blue": {"hook": (220, 221, 216), "base": (245, 244, 239), "glow": (251, 248, 239), "accent": (86, 103, 111), "text": (52, 56, 56)},
    "blush_cream": {"hook": (238, 220, 218), "base": (250, 243, 239), "glow": (255, 250, 241), "accent": (141, 96, 95), "text": (64, 54, 54)},
}


def find_font(size: int, serif: bool = True, bold: bool = False):
    if serif:
        names = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        ]
    else:
        names = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def editorial_background(palette, *, hook=False):
    """Create a soft editorial background with a restrained center glow."""
    edge = palette["hook"] if hook else palette["base"]
    glow = palette["glow"]
    image = Image.new("RGB", (CANVAS_W, CANVAS_H), edge)
    px = image.load()
    cx, cy = CANVAS_W / 2, CANVAS_H * 0.45
    max_dist = ((CANVAS_W / 2) ** 2 + (CANVAS_H * 0.62) ** 2) ** 0.5
    for y in range(CANVAS_H):
        for x in range(CANVAS_W):
            dist = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / max_dist
            strength = max(0.0, 1.0 - min(1.0, dist))
            strength = strength * strength * (0.78 if hook else 0.9)
            px[x, y] = mix(edge, glow, strength)
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


def fit_text(draw, text, *, max_width, max_height, start_size, min_size, serif=True, bold=False, spacing=12):
    for size in range(start_size, min_size - 1, -2):
        font = find_font(size, serif=serif, bold=bold)
        wrapped = wrap_to_width(draw, text, font, max_width)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align="center")
        if box[2] - box[0] <= max_width and box[3] - box[1] <= max_height:
            return wrapped, font, box
    font = find_font(min_size, serif=serif, bold=bold)
    wrapped = wrap_to_width(draw, text, font, max_width)
    box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=spacing, align="center")
    return wrapped, font, box


def draw_centered_multiline(draw, text, font, y, fill, spacing=12):
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    width = box[2] - box[0]
    draw.multiline_text(((CANVAS_W - width) / 2, y), text, font=font, fill=fill, spacing=spacing, align="center")
    return box[3] - box[1]


def render_slide(carousel, slide, index, total, output_path):
    palette = PALETTES.get(carousel.get("Palette"), PALETTES["dusty_blue"])
    kind = slide.get("kind", "lesson")
    hook = kind == "hook"
    closing = kind == "closing"
    image = editorial_background(palette, hook=hook)
    draw = ImageDraw.Draw(image)

    accent = palette["accent"]
    text_color = palette["text"]
    eyebrow_font = find_font(22, serif=False, bold=True)
    handle_font = find_font(22, serif=False, bold=False)

    if hook:
        eyebrow = "TALK N WALKS • SWIPE →"
    elif closing:
        eyebrow = "KEEP THIS ONE"
    else:
        eyebrow = f"{index:02d} / {total - 2:02d}"
    eb = draw.textbbox((0, 0), eyebrow, font=eyebrow_font)
    draw.text(((CANVAS_W - (eb[2] - eb[0])) / 2, 120), eyebrow, font=eyebrow_font, fill=accent)

    max_title_h = 520 if hook else 380
    title_start = 82 if hook else 66
    title_min = 52 if hook else 44
    title, title_font, title_box = fit_text(
        draw,
        slide["title"],
        max_width=860,
        max_height=max_title_h,
        start_size=title_start,
        min_size=title_min,
        serif=True,
        bold=hook,
        spacing=18,
    )
    title_h = title_box[3] - title_box[1]
    title_y = 310 if hook else 330
    draw_centered_multiline(draw, title, title_font, title_y, text_color, spacing=18)

    # Fine editorial divider.
    divider_y = title_y + title_h + 58
    draw.rounded_rectangle((440, divider_y, 640, divider_y + 3), radius=2, fill=accent)

    body = slide.get("body", "").strip()
    if body:
        body_text, body_font, body_box = fit_text(
            draw,
            body,
            max_width=800,
            max_height=360,
            start_size=38 if hook else 34,
            min_size=28,
            serif=False,
            bold=False,
            spacing=14,
        )
        body_h = body_box[3] - body_box[1]
        body_y = divider_y + 55
        draw_centered_multiline(draw, body_text, body_font, body_y, text_color, spacing=14)

        # Tiny accent mark below the copy keeps the slides visually related without clutter.
        mark_y = min(1120, body_y + body_h + 72)
        draw.ellipse((CANVAS_W / 2 - 4, mark_y, CANVAS_W / 2 + 4, mark_y + 8), fill=accent)

    handle_box = draw.textbbox((0, 0), HANDLE, font=handle_font)
    draw.text(((CANVAS_W - (handle_box[2] - handle_box[0])) / 2, 1250), HANDLE, font=handle_font, fill=accent)

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
        # Public copy is kept separate so future Meta publishing can use raw GitHub URLs.
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
        "slide_count": len(slides),
        "public_files": [f"public/carousels/{carousel_id}/slide_{i:02d}.jpg" for i in range(1, len(slides) + 1)],
        "publish_ready": False,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "publish.env").write_text(
        f"CAROUSEL_ID={carousel_id}\nCAROUSEL_SLIDE_COUNT={len(slides)}\nCAROUSEL_PUBLISH_READY=false\n",
        encoding="utf-8",
    )
    print(f"Built {carousel_id}: {len(slides)} slides -> {output_dir}")


if __name__ == "__main__":
    main()
