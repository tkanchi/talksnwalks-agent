import base64
import csv
import os
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo
from io import BytesIO

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

CANVAS = (1080, 1920)
HANDLE = "@talksnwalks101"
TZ = ZoneInfo("Asia/Kolkata")
START_DATE = date.fromisoformat(os.getenv("START_DATE", "2026-08-21"))
QUOTES_FILE = Path(os.getenv("QUOTES_FILE", "data/quotes.csv"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
SERIF_FONT = os.getenv("SERIF_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
SANS_FONT = os.getenv("SANS_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

SCENES = {
    "Believe in Yourself": ["a cozy woman reading with a small plant and tea mug", "a woman journaling quietly beside a small plant", "a woman standing confidently with a book held to her chest"],
    "Courage": ["a woman taking one small step up a simple staircase", "a woman walking forward into a light breeze", "a woman standing at the start of a path with calm confidence"],
    "Growth": ["a woman watering a tiny growing plant", "a woman reading beside a young leafy plant", "a woman tending a small indoor garden"],
    "Resilience": ["a woman sitting calmly under a simple umbrella after rain", "a woman resting with a mug, then looking ready to rise", "a woman beside a small plant bending gently in wind"],
    "Self-Worth": ["a woman hugging herself gently", "a woman looking into a small mirror with a peaceful expression", "a woman sitting comfortably alone with tea and a book"],
    "Dreams": ["a woman gazing upward at a few tiny stars", "a woman sketching ideas in a notebook", "a woman sitting by a window with a notebook and moon outside"],
    "Discipline & Action": ["a woman writing a short checklist at a clean desk", "a woman tying her shoes before a walk", "a woman focused at a small desk with notebook and mug"],
    "Peace & Letting Go": ["a woman sipping tea beside a window", "a woman meditating with a tiny plant nearby", "a woman sitting quietly with an open book resting beside her"],
    "Hope": ["a woman looking toward a small sunrise", "a woman holding a tiny sprouting plant", "a woman by a window with soft morning light"],
    "Happiness & Gratitude": ["a woman smiling gently while holding a warm mug", "a woman reading with a tiny flower vase nearby", "a woman noticing a small flower on a peaceful walk"],
    "Becoming": ["a woman walking along a simple path with a small bag", "a woman painting a small canvas", "a woman writing in a journal beside a growing plant"],
    "Keep Going": ["a woman walking steadily forward on a simple path", "a woman climbing one small step at a time", "a woman standing after a rest, ready to continue"],
}


def load_quotes():
    with QUOTES_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_day(rows):
    manual = os.getenv("DAY_NUMBER")
    if manual:
        day = int(manual)
    else:
        today_ist = datetime.now(TZ).date()
        day = (today_ist - START_DATE).days + 1
    if day < 1:
        day = 1
    return ((day - 1) % len(rows)) + 1


def pick_scene(theme, day):
    choices = SCENES.get(theme, SCENES["Believe in Yourself"])
    return choices[(day - 1) % len(choices)]


def generate_illustration(quote, theme, scene):
    client = OpenAI()
    prompt = f"""Generate ONE isolated minimalist black line-art illustration for an inspirational Instagram quote post.

Theme: {theme}
Emotional idea: {quote}
Scene: {scene}

STRICT STYLE CONTRACT:
- delicate hand-drawn black ink line art only
- transparent background
- no text, no letters, no numbers, no logos, no watermark
- no color, no gray fill, no gradient, no border
- cozy, calm, elegant, feminine, modern
- compact composition designed to appear very small in the center of a 9:16 white poster
- simple details; avoid clutter
- the drawing must remain legible when reduced to roughly 300 px wide
"""
    response = client.responses.create(
        model=os.getenv("OPENAI_TEXT_MODEL", "gpt-5.6-luna"),
        input=prompt,
        tools=[{
            "type": "image_generation",
            "model": os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
            "background": "transparent"
        }],
    )
    image_call = next((x for x in response.output if x.type == "image_generation_call"), None)
    if not image_call or not image_call.result:
        raise RuntimeError("Image generation returned no image result")
    return Image.open(BytesIO(base64.b64decode(image_call.result))).convert("RGBA")


def trim_transparent(im):
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    return im.crop(bbox) if bbox else im


def fit_font(draw, text, font_path, start_size, min_size, max_width):
    for size in range(start_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return ImageFont.truetype(font_path, min_size)


def compose(quote, illustration):
    canvas = Image.new("RGB", CANVAS, "white")
    draw = ImageDraw.Draw(canvas)
    quote_font = fit_font(draw, quote, SERIF_FONT, 42, 18, 930)
    handle_font = ImageFont.truetype(SANS_FONT, 24)

    illustration = trim_transparent(illustration)
    illustration.thumbnail((310, 330), Image.Resampling.LANCZOS)

    qbox = draw.textbbox((0, 0), quote, font=quote_font)
    qh = qbox[3] - qbox[1]
    hbox = draw.textbbox((0, 0), HANDLE, font=handle_font)
    hh = hbox[3] - hbox[1]

    gap_quote_image = 58
    gap_image_handle = 46
    total_h = qh + gap_quote_image + illustration.height + gap_image_handle + hh
    top = (CANVAS[1] - total_h) // 2

    draw.text((CANVAS[0] // 2, top), quote, font=quote_font, fill="black", anchor="ma", align="center")
    iy = top + qh + gap_quote_image
    ix = (CANVAS[0] - illustration.width) // 2
    canvas.paste(illustration, (ix, iy), illustration)
    hy = iy + illustration.height + gap_image_handle
    draw.text((CANVAS[0] // 2, hy), HANDLE, font=handle_font, fill="black", anchor="ma")
    return canvas


def guardian_check(image, quote):
    if image.size != CANVAS:
        raise AssertionError(f"Wrong canvas size: {image.size}")
    if "\n" in quote:
        raise AssertionError("Quote contains a line break; template requires one line")
    if not quote.strip():
        raise AssertionError("Quote is empty")
    return True


def main():
    rows = load_quotes()
    day = resolve_day(rows)
    item = rows[day - 1]
    quote = item["Quote"].strip()
    theme = item["Theme"].strip()
    scene = pick_scene(theme, day)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    illustration = generate_illustration(quote, theme, scene)
    final = compose(quote, illustration)
    guardian_check(final, quote)

    output = OUTPUT_DIR / f"day_{day:03d}.png"
    final.save(output, quality=95)
    metadata = OUTPUT_DIR / f"day_{day:03d}.txt"
    metadata.write_text(f"Day: {day}\nQuote: {quote}\nTheme: {theme}\nScene: {scene}\nStatus: READY_FOR_REVIEW\n", encoding="utf-8")
    print(f"Created {output}")
    print(f"Quote: {quote}")
    print(f"Theme: {theme}")
    print("Status: READY_FOR_REVIEW")


if __name__ == "__main__":
    main()
