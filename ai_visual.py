"""Generate a fresh background scene for every Talks N Walks quote.

The image model creates scene artwork only. Quote text, attribution, handle and
the fixed brand mark are composited later by ``visual_theme.py`` so generated
art can never distort the branding. The old illustration library is not used
for post scene selection.
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw


API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = os.getenv("AI_IMAGE_MODEL", "gpt-image-2")
TIMEOUT_SECONDS = 240


def _scene_prompt(quote: str, audience: str = "All", topic: str = "Mindset") -> str:
    audience = (audience or "All").strip()
    topic = (topic or "Mindset").strip()
    neutral = audience.lower() in {"all", "adults", "general", ""}

    if neutral:
        audience_rule = (
            "This quote is universal. Prefer a gender-neutral, age-neutral scene: "
            "scenery, travel, a road, window, desk, journal, coffee, books, shoes, "
            "bicycle, car, accessories, ocean, mountains, plants or another elegant "
            "visual metaphor. Do not default to a woman or man."
        )
    else:
        audience_rule = (
            f"The intended audience is {audience}. A person may appear only when it "
            "meaningfully improves the quote. Keep people natural, inclusive and "
            "age-appropriate, and avoid repeating the same pose every day."
        )

    return f"""Create ONLY the background artwork for a premium vertical Instagram motivational post.

Quote to interpret visually: {quote}
Audience: {audience}
Topic: {topic}

LOCKED TALKS N WALKS VISUAL DIRECTION:
- Vertical 2:3 artwork that will be cropped to 9:16.
- Colourful but peaceful and calming, not monochrome.
- Soft lavender, blush, peach, cream, sage, powder blue, muted teal and warm sunrise/sunset tones.
- Premium illustrated lifestyle/editorial finish with gentle realistic depth, soft natural light and a cozy aspirational mood.
- Rich visual detail belongs mainly in the LOWER 45 percent.
- Keep the UPPER 55 percent quiet, bright and uncluttered for separately overlaid quote typography: soft sky, wall, window light, mist or a subtle pastel gradient are ideal.
- No black or dark gradient at the top.
- Create a scene specifically for the meaning of this quote. Do not recycle the same balcony, woman, flowers, books or coffee composition every day.
- {audience_rule}
- No words, letters, numbers, captions, quote text, author names, usernames, watermarks, logos, readable signs, readable book covers or readable screens anywhere in the generated artwork.
- Do NOT generate the Talks N Walks logo. Branding is added afterward from a fixed asset.
- Avoid clutter behind the future quote area and maintain strong contrast for dark charcoal serif text.

Return one polished finished background scene only."""


def _procedural_fallback(width: int, height: int, quote: str) -> Image.Image:
    """Build-only fallback used only when AI visuals are not required."""
    palettes = [
        ((244, 229, 238), (251, 223, 193)),
        ((226, 232, 249), (251, 218, 225)),
        ((229, 241, 235), (249, 228, 205)),
        ((237, 230, 247), (224, 239, 247)),
    ]
    top, bottom = palettes[sum(quote.encode("utf-8")) % len(palettes)]
    image = Image.new("RGB", (width, height))
    px = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        colour = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(width):
            px[x, y] = colour

    draw = ImageDraw.Draw(image)
    horizon = int(height * 0.72)
    draw.ellipse(
        (int(width * 0.70), horizon - 140, int(width * 0.82), horizon - 20),
        fill=(255, 244, 199),
    )
    draw.polygon(
        [
            (0, horizon + 80),
            (width * .25, horizon - 40),
            (width * .45, horizon + 55),
            (width * .68, horizon - 15),
            (width, horizon + 95),
            (width, height),
            (0, height),
        ],
        fill=(190, 183, 205),
    )
    return image


def _required() -> bool:
    return os.getenv("AI_VISUAL_REQUIRED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _decode_image_response(payload: dict) -> bytes:
    data = payload.get("data") or []
    if not data:
        raise RuntimeError("OpenAI image response did not contain image data")
    item = data[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        response = requests.get(item["url"], timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.content
    raise RuntimeError("OpenAI image response contained neither b64_json nor url")


def generate_background(
    quote: str,
    *,
    audience: str = "All",
    topic: str = "Mindset",
    width: int = 1080,
    height: int = 1920,
    debug_path: Path | None = None,
) -> Image.Image:
    """Generate one fresh quote-aware scene; never select a stored illustration."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        if _required():
            raise RuntimeError(
                "OPENAI_API_KEY is required for production AI visuals. "
                "Add it as a GitHub Actions secret before publishing."
            )
        print("OPENAI_API_KEY is not configured; using build-only pastel fallback.")
        return _procedural_fallback(width, height, quote)

    body = {
        "model": DEFAULT_MODEL,
        "prompt": _scene_prompt(quote, audience=audience, topic=topic),
        "size": os.getenv("AI_IMAGE_SIZE", "1024x1536"),
        "quality": os.getenv("AI_IMAGE_QUALITY", "medium"),
        "output_format": "png",
    }

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
        if not response.ok:
            raise RuntimeError(
                f"OpenAI image generation failed ({response.status_code}): "
                f"{response.text[:500]}"
            )
        raw = _decode_image_response(response.json())
        generated = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        if _required():
            raise
        print("AI image generation failed; using build-only pastel fallback.")
        return _procedural_fallback(width, height, quote)

    # Cover the final 1080x1920 canvas and center-crop.
    scale = max(width / generated.width, height / generated.height)
    resized = generated.resize(
        (round(generated.width * scale), round(generated.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    result = resized.crop((left, top, left + width, top + height))

    if debug_path:
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(debug_path, "JPEG", quality=92, optimize=True)
    return result
