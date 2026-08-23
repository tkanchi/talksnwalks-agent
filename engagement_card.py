"""Add the Talks N Walks follow outro and engagement CTA without changing the core builder."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTRO_SECONDS = 1.5
CREAM = (252, 248, 240)
INK = (35, 36, 39)
SAGE = (116, 123, 93)
PEACH = (205, 133, 111)
SOFT_SAGE = (190, 193, 169)
SOFT_PEACH = (239, 193, 176)
GOLD = (207, 169, 91)


def _font(size: int, *, italic: bool = False, sans: bool = False):
    if sans:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    elif italic:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _center_text(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill, width: int) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    text_w = box[2] - box[0]
    draw.text(((width - text_w) / 2, y), text, font=font, fill=fill)
    return box[3] - box[1]


def _leaf(draw: ImageDraw.ImageDraw, cx: float, cy: float, rx: float, ry: float, angle: float, fill):
    points = []
    for step in range(24):
        theta = 2 * math.pi * step / 24
        x = rx * math.cos(theta)
        y = ry * math.sin(theta)
        ca, sa = math.cos(angle), math.sin(angle)
        points.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    draw.polygon(points, fill=fill)


def _botanical_branch(draw: ImageDraw.ImageDraw, start, end, *, mirror: bool = False):
    draw.line((*start, *end), fill=(115, 122, 96, 145), width=4)
    sx, sy = start
    ex, ey = end
    for idx, t in enumerate((0.18, 0.34, 0.51, 0.68, 0.84)):
        x = sx + (ex - sx) * t
        y = sy + (ey - sy) * t
        side = -1 if (idx + (1 if mirror else 0)) % 2 else 1
        leaf_color = (181, 188, 159, 175) if idx % 2 == 0 else (236, 181, 159, 165)
        _leaf(draw, x + side * 33, y - 12, 14, 38, side * 0.65, leaf_color)


def _build_follow_card(width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), CREAM)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # Full-resolution recreation of the supplied card avoids another blurry binary-asset path.
    odraw.ellipse((width - 330, -130, width + 140, 430), fill=(245, 205, 187, 44))
    odraw.ellipse((-170, height - 520, 310, height + 70), fill=(245, 205, 187, 42))
    _botanical_branch(odraw, (width - 38, 25), (width - 245, 335), mirror=True)
    _botanical_branch(odraw, (38, height - 30), (235, height - 370))
    for x, y in ((width - 250, 300), (width - 205, 360), (205, height - 360), (260, height - 305)):
        odraw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(*GOLD, 150))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    _center_text(draw, "TW", 250, _font(74), INK, width)
    _center_text(draw, "T A L K   N   W A L K S", 337, _font(19, sans=True), INK, width)
    draw.line((width / 2 - 70, 382, width / 2 - 18, 382), fill=(150, 150, 140), width=2)
    _center_text(draw, "♥", 366, _font(24, sans=True), INK, width)
    draw.line((width / 2 + 18, 382, width / 2 + 70, 382), fill=(150, 150, 140), width=2)

    _center_text(draw, "Follow", 510, _font(132), INK, width)
    _center_text(draw, "for more ♡", 680, _font(88, italic=True), SAGE, width)
    draw.line((315, 805, 765, 805), fill=PEACH, width=4)

    draw.line((width / 2 - 150, 905, width / 2 - 42, 905), fill=SOFT_PEACH, width=2)
    _center_text(draw, "♡", 878, _font(42), PEACH, width)
    draw.line((width / 2 + 42, 905, width / 2 + 150, 905), fill=SOFT_PEACH, width=2)

    body_font = _font(43)
    for line, y in (
        ("More real thoughts,", 1010),
        ("daily motivation &", 1080),
        ("relatable quotes", 1150),
        ("coming your way.", 1220),
    ):
        _center_text(draw, line, y, body_font, INK, width)

    handle_font = _font(34)
    handle = "@talksnwalks101"
    box = draw.textbbox((0, 0), handle, font=handle_font)
    handle_w = box[2] - box[0]
    pill_w = handle_w + 90
    pill_x = (width - pill_w) / 2
    draw.rounded_rectangle((pill_x, 1390, pill_x + pill_w, 1468), radius=35, fill=SOFT_SAGE)
    _center_text(draw, handle, 1407, handle_font, INK, width)

    return canvas


def _prepare_follow_card(build_reel) -> Path:
    path = Path(build_reel.OUTPUT_DIR) / ".follow_for_more_outro.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    card = _build_follow_card(build_reel.CANVAS_W, build_reel.CANVAS_H)
    card.save(path, "JPEG", quality=94, optimize=True, progressive=True)
    return path


def apply_engagement_card(build_reel) -> None:
    """Add a 1.5-second follow outro and a comment/follow CTA to every stream."""
    original_caption = build_reel.build_caption

    def build_caption(rows, day, quote, theme):
        base = original_caption(rows, day, quote, theme)
        marker = f"\n\n{build_reel.HANDLE}\n"
        cta = (
            "\n\nWhat do you think? Comment below 💬\n"
            f"Follow {build_reel.HANDLE} for more real thoughts & daily motivation.\n"
        )
        if marker in base:
            return base.replace(marker, cta, 1)
        return base + cta

    def make_mp4(image_path, audio_path, output_mp4):
        output_mp4 = Path(output_mp4)
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        card_path = _prepare_follow_card(build_reel)
        outro = min(OUTRO_SECONDS, max(0.8, build_reel.REEL_SECONDS * 0.25))
        quote_seconds = build_reel.REEL_SECONDS - outro
        w, h = build_reel.CANVAS_W, build_reel.CANVAS_H
        filter_complex = (
            f"[0:v]scale={w}:{h},setsar=1,fps=30,trim=duration={quote_seconds},"
            "setpts=PTS-STARTPTS,format=yuv420p[v0];"
            f"[1:v]scale={w}:{h},setsar=1,fps=30,trim=duration={outro},"
            "setpts=PTS-STARTPTS,format=yuv420p[v1];"
            "[v0][v1]concat=n=2:v=1:a=0[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30", "-i", str(image_path),
            "-loop", "1", "-framerate", "30", "-i", str(card_path),
            "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "2:a:0",
            "-t", str(build_reel.REEL_SECONDS),
            "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-crf", "25",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-ar", "48000", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart",
            str(output_mp4),
        ]
        subprocess.run(cmd, check=True)

    build_reel.build_caption = build_caption
    build_reel.make_mp4 = make_mp4
