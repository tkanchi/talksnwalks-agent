import csv
import math
import os
import struct
import subprocess
import sys
import wave
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

CANVAS_W = 1080
CANVAS_H = 1920
HANDLE = "@talksnwalks101"
TZ = ZoneInfo("Asia/Kolkata")
START_DATE = date.fromisoformat(os.getenv("START_DATE", "2026-08-21"))
QUOTES_FILE = Path(os.getenv("QUOTES_FILE", "data/quotes.csv"))
ILLUSTRATION_DIR = Path(os.getenv("ILLUSTRATION_DIR", "illustrations"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
PUBLIC_DIR = Path(os.getenv("PUBLIC_DIR", "public"))

BLOCK_CENTER_Y = 940
QUOTE_TO_ART_GAP = 110
ART_TO_HANDLE_GAP = 38
ILLUSTRATION_MAX_W = 560
ILLUSTRATION_MAX_H = 520
MAX_QUOTE_WIDTH = 900
QUOTE_MAX_SIZE = 44
QUOTE_MIN_SIZE = 24
HANDLE_SIZE = 24
REEL_SECONDS = 8

ILLUSTRATIONS = [
    "reading_01.png", "reading_02.png",
    "dancing_01.png", "dancing_02.png",
    "music_01.png", "music_02.png",
    "workout_01.png", "workout_02.png",
    "sleeping_01.png", "sleeping_02.png",
    "laughing_01.png", "laughing_02.png",
]

SUPPORT_LINES = {
    "Believe in Yourself": [
        "Keep choosing the version of you that believes.",
        "A little self-trust changes everything.",
        "You already carry more strength than you realize.",
        "Back yourself today.",
        "Your next chapter begins with belief.",
        "Give your own voice more weight.",
    ],
    "Courage": [
        "One brave step is enough for today.",
        "You can move forward before fear disappears.",
        "Courage grows every time you use it.",
        "Choose the step that moves you closer.",
        "Bravery can be quiet too.",
        "Start scared. Keep going anyway.",
    ],
    "Growth": [
        "Small progress still changes your life.",
        "Keep becoming at your own pace.",
        "Growth rarely looks dramatic while it is happening.",
        "Your effort is adding up.",
        "Stay curious about who you can become.",
        "Slow growth is still growth.",
    ],
    "Resilience": [
        "Keep going gently if you need to.",
        "This moment is not your whole story.",
        "You have rebuilt before. You can rebuild again.",
        "Strength can look like simply continuing.",
        "Give yourself credit for making it this far.",
        "There is more strength in you than this day can measure.",
    ],
    "Self-Worth": [
        "Your value does not need outside approval.",
        "Choose yourself without explaining it.",
        "You deserve the kindness you give everyone else.",
        "Your worth stays intact, even on hard days.",
        "Take up your space.",
        "You do not need to earn the right to matter.",
    ],
    "Dreams": [
        "Keep making room for the life you imagine.",
        "Big dreams are built through small ordinary days.",
        "Protect the vision that keeps calling you.",
        "Give your dream another day of effort.",
        "Keep building what you can already see in your mind.",
        "Your future deserves your consistency.",
    ],
    "Discipline & Action": [
        "A small action today is enough.",
        "Keep the promise you made to yourself.",
        "Consistency is how quiet goals become real.",
        "Do the next useful thing.",
        "Progress begins when you show up again.",
        "Keep moving even when motivation is quiet.",
    ],
    "Peace & Letting Go": [
        "Not everything deserves access to your energy.",
        "Choose what leaves you lighter.",
        "Peace is a valid priority.",
        "Release what keeps asking you to abandon yourself.",
        "You are allowed to leave some things behind.",
        "Protect the calm you worked hard to create.",
    ],
    "Hope": [
        "Leave a little room for something good.",
        "The next chapter has not happened yet.",
        "Keep the door open to better days.",
        "Hope only needs a small place to begin.",
        "There is still more ahead of you.",
        "Tomorrow can look different.",
    ],
    "Happiness & Gratitude": [
        "Let the small moments count.",
        "You do not have to rush past today.",
        "Notice what is already beautiful.",
        "Joy is allowed in ordinary moments.",
        "Give yourself permission to enjoy your life.",
        "Pause long enough to notice the good.",
    ],
    "Becoming": [
        "You are allowed to become someone new.",
        "Keep choosing what feels more like you.",
        "Your evolution does not need permission.",
        "Let yourself change.",
        "There is no deadline on becoming.",
        "Keep growing into your own life.",
    ],
    "Keep Going": [
        "Just take the next step.",
        "You do not have to finish everything today.",
        "Keep showing up for the life you want.",
        "Another day is another chance.",
        "Your story still has somewhere to go.",
        "Keep moving at the pace you can sustain.",
    ],
}

HASHTAGS = {
    "Believe in Yourself": "#selfbelief #motivation #mindset #dailyquotes",
    "Courage": "#courage #motivation #mindset #dailyquotes",
    "Growth": "#growth #selfgrowth #mindset #dailyquotes",
    "Resilience": "#resilience #keepgoing #motivation #dailyquotes",
    "Self-Worth": "#selfworth #selflove #mindset #dailyquotes",
    "Dreams": "#dreambig #goals #motivation #dailyquotes",
    "Discipline & Action": "#discipline #consistency #motivation #dailyquotes",
    "Peace & Letting Go": "#innerpeace #lettinggo #mindset #dailyquotes",
    "Hope": "#hope #positivity #motivation #dailyquotes",
    "Happiness & Gratitude": "#gratitude #joy #positivity #dailyquotes",
    "Becoming": "#becoming #selfgrowth #mindset #dailyquotes",
    "Keep Going": "#keepgoing #motivation #mindset #dailyquotes",
}


def find_font(size: int, serif: bool = True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf" if serif else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf" if serif else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/georgia.ttf" if serif else "C:/Windows/Fonts/arial.ttf",
    ]
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_quotes():
    with QUOTES_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_day(rows):
    manual = os.getenv("DAY_NUMBER", "").strip()
    day = int(manual) if manual else (datetime.now(TZ).date() - START_DATE).days + 1
    if day < 1 or day > len(rows):
        return None
    return day


def adaptive_quote_font(draw, text):
    for size in range(QUOTE_MAX_SIZE, QUOTE_MIN_SIZE - 1, -1):
        font = find_font(size, serif=True)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= MAX_QUOTE_WIDTH:
            return font
    return find_font(QUOTE_MIN_SIZE, serif=True)


def trim_transparent(im):
    im = im.convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    return im.crop(bbox) if bbox else im


def fit_inside(im, max_w, max_h):
    im = trim_transparent(im)
    ratio = min(max_w / im.width, max_h / im.height)
    size = (max(1, round(im.width * ratio)), max(1, round(im.height * ratio)))
    return im.resize(size, Image.Resampling.LANCZOS)


def compose_post(quote, illustration_path, output_jpg):
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    draw = ImageDraw.Draw(canvas)
    qfont = adaptive_quote_font(draw, quote)
    hfont = find_font(HANDLE_SIZE, serif=False)

    qbox = draw.textbbox((0, 0), quote, font=qfont)
    quote_w = qbox[2] - qbox[0]
    quote_h = qbox[3] - qbox[1]

    art = fit_inside(Image.open(illustration_path), ILLUSTRATION_MAX_W, ILLUSTRATION_MAX_H)

    hbox = draw.textbbox((0, 0), HANDLE, font=hfont)
    handle_w = hbox[2] - hbox[0]
    handle_h = hbox[3] - hbox[1]

    total_height = quote_h + QUOTE_TO_ART_GAP + art.height + ART_TO_HANDLE_GAP + handle_h
    block_top = int(BLOCK_CENTER_Y - total_height / 2)
    quote_y = block_top
    art_y = quote_y + quote_h + QUOTE_TO_ART_GAP
    handle_y = art_y + art.height + ART_TO_HANDLE_GAP

    draw.text(((CANVAS_W - quote_w) / 2, quote_y), quote, fill="black", font=qfont)
    art_x = (CANVAS_W - art.width) // 2
    canvas.paste(art, (art_x, art_y), art)
    draw.text(((CANVAS_W - handle_w) / 2, handle_y), HANDLE, fill="black", font=hfont)

    output_jpg.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_jpg, "JPEG", quality=94, optimize=True, progressive=True)


def write_fallback_audio(path, duration=REEL_SECONDS, sample_rate=48000):
    """Creates a quiet original ambient pad so automated Reels always have audio."""
    chords = [
        (261.63, 329.63, 392.00),
        (220.00, 261.63, 329.63),
        (174.61, 220.00, 261.63),
        (196.00, 246.94, 293.66),
    ]
    frames = int(duration * sample_rate)
    chord_seconds = duration / len(chords)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(frames):
            t = i / sample_rate
            chord_index = min(int(t / chord_seconds), len(chords) - 1)
            local_t = t - chord_index * chord_seconds
            fade = min(1.0, local_t / 0.35, (chord_seconds - local_t) / 0.35)
            fade = max(0.0, fade)

            sample = 0.0
            for freq in chords[chord_index]:
                sample += math.sin(2 * math.pi * freq * t)
                sample += 0.18 * math.sin(2 * math.pi * freq * 2 * t)
            sample /= 3.54
            sample *= 0.075 * fade
            sample = max(-1.0, min(1.0, sample))
            wav.writeframesraw(struct.pack("<h", int(sample * 32767)))


def build_caption(rows, day, quote, theme):
    previous_same_theme = sum(1 for row in rows[: day - 1] if row["Theme"].strip() == theme)
    lines = SUPPORT_LINES.get(theme, ["Keep going, one day at a time."])
    support = lines[previous_same_theme % len(lines)]
    tags = HASHTAGS.get(theme, "#motivation #mindset #dailyquotes")
    return f"{quote}\n\n{support}\n\n{HANDLE}\n{tags}"


def make_mp4(image_path, audio_path, output_mp4):
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "30", "-i", str(image_path),
        "-i", str(audio_path),
        "-t", str(REEL_SECONDS),
        "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", "25",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart",
        str(output_mp4),
    ]
    subprocess.run(cmd, check=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_quotes()
    day = resolve_day(rows)
    env_path = OUTPUT_DIR / "publish.env"

    if day is None:
        env_path.write_text("SKIP=true\n", encoding="utf-8")
        print("No campaign post is due today.")
        return

    item = rows[day - 1]
    quote = item["Quote"].strip()
    theme = item["Theme"].strip()
    illustration_name = ILLUSTRATIONS[(day - 1) % len(ILLUSTRATIONS)]
    illustration_path = ILLUSTRATION_DIR / illustration_name

    if not illustration_path.exists():
        raise FileNotFoundError(
            f"Missing {illustration_path}. Add all 12 approved PNGs to the illustrations folder."
        )

    day_padded = f"{day:03d}"
    jpg_path = OUTPUT_DIR / f"day_{day_padded}.jpg"
    wav_path = OUTPUT_DIR / f"day_{day_padded}_fallback.wav"
    mp4_path = PUBLIC_DIR / f"day_{day_padded}.mp4"
    caption_path = OUTPUT_DIR / "caption.txt"

    compose_post(quote, illustration_path, jpg_path)
    write_fallback_audio(wav_path)
    make_mp4(jpg_path, wav_path, mp4_path)

    caption = build_caption(rows, day, quote, theme)
    caption_path.write_text(caption, encoding="utf-8")

    env_path.write_text(
        "\n".join([
            "SKIP=false",
            f"DAY_NUMBER={day}",
            f"DAY_PADDED={day_padded}",
            f"VIDEO_FILE={mp4_path.as_posix()}",
            f"IMAGE_FILE={jpg_path.as_posix()}",
            f"ILLUSTRATION={illustration_name}",
        ]) + "\n",
        encoding="utf-8",
    )

    print(f"Built Day {day}: {quote}")
    print(f"Illustration: {illustration_name}")
    print(f"Reel: {mp4_path}")
    print("Fallback audio: original ambient pad")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        print("ffmpeg failed. Make sure ffmpeg is installed and on PATH.", file=sys.stderr)
        raise
