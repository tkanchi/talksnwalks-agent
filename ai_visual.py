"""Generate a fresh Talk N Walks background for each quote.

The image model creates scene artwork only. Quote text, attribution, handle and
brand mark are added later by ``visual_theme.py`` so they remain deterministic.
No pre-uploaded illustration library is used.
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw


API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.getenv("AI_IMAGE_MODEL", "gpt-image-2")
TIMEOUT_SECONDS = 180


def _scene_prompt(quote: str, audience: str = "All", topic: str = "Mindset") -> str:
    audience = (audience or "All").strip()
    topic = (topic or "Mindset").strip()
    neutral = audience.lower() in {"all", "adults", ""}

    audience_rule = (
        "Make the scene gender-neutral and age-neutral. Prefer scenery, objects, travel, books, coffee, roads, desks, windows, nature, accessories or other universal visual metaphors; do not include a person unless truly necessary."
        if neutral
        else f"The intended audience is {audience}. People may appear when they genuinely improve the meaning, but avoid repetitive portrait poses and keep the scene inclusive and natural."
    )

    return f"""Create ONLY the background artwork for a premium vertical Instagram motivational post.

Quote meaning to interpret visually: {quote}
Audience: {audience}
Topic: {topic}

Locked Talk N Walks visual direction:
- 9:16 vertical composition, calm premium lifestyle/editorial illustration.
- Colourful but peaceful: soft lavender, blush, peach, cream, sage, powder blue and warm sunset/sunrise tones. Avoid neon, harsh saturation and black gradients.
- Cozy, aspirational, detailed scene with gentle natural light and depth; polished illustration with a soft realistic finish.
- The upper 48 percent must remain visually quiet and uncluttered for quote typography. Use soft sky, wall, window light or subtle gradient there.
- Put the main scene and richer detail mostly in the lower half.
- Vary the scene intelligently to fit the quote rather than repeating the same woman, balcony, flowers or books every day.
- {audience_rule}
- No words, letters, numbers, captions, quotes, author names, usernames, watermarks, logos, signs, readable book covers or readable screens anywhere in the artwork.
- Do not draw the Talk N Walks logo. Branding is added separately after generation.
- No dark overlay at the top. Ensure the quiet text area has strong contrast for dark charcoal text.

Return one polished finished background image only."""


def _extract_image_b64(payload: dict) -> str:
    for item in payload.get("output", []):
        if item.get("type") == "image_generation_call" and item.get("result"):
            return item["result"]
    raise RuntimeError("OpenAI image response did not contain an image_generation_call result")


def _procedural_fallback(width: int, height: int, quote: str) -> Image.Image:
    """Safe no-secret fallback: fresh pastel canvas, never a stored illustration."""
    palettes = [
        ((244, 229, 238), (251, 223, 193)),
        ((226, 232, 249), (251, 218, 225)),
        ((229, 241, 235), (249, 228, 205)),
        ((237, 230, 247), (224, 239, 247)),
    ]
    choice = sum(quote.encode("utf-8")) % len(palettes)
    top, bottom = palettes[choice]
    image = Image.new("RGB", (width, height))
    px = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        for x in range(width):
            px[x, y] = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))

    draw = ImageDraw.Draw(image)
    horizon = int(height * 0.70)
    draw.ellipse((int(width * 0.70), horizon - 140, int(width * 0.82), horizon - 20), fill=(255, 244, 199))
    draw.polygon([(0, horizon + 80), (width * .25, horizon - 40), (width * .45, horizon + 55), (width * .68, horizon - 15), (width, horizon + 95), (width, height), (0, height)], fill=(190, 183, 205))
    draw.polygon([(0, horizon + 150), (width * .22, horizon + 45), (width * .48, horizon + 135), (width * .78, horizon + 40), (width, horizon + 120), (width, height), (0, height)], fill=(162, 173, 190))
    return image


def generate_background(
    quote: str,
    *,
    audience: str = "All",
    topic: str = "Mindset",
    width: int = 1080,
    height: int = 1920,
    debug_path: Path | None = None,
) -> Image.Image:
    """Generate a quote-aware scene, falling back safely if no API key exists."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY is not configured; using procedural pastel fallback.")
        return _procedural_fallback(width, height, quote)

    body = {
        "model": os.getenv("AI_PROMPT_MODEL", "gpt-5.6-luna"),
        "input": _scene_prompt(quote, audience=audience, topic=topic),
        "tools": [
            {
                "type": "image_generation",
                "model": DEFAULT_MODEL,
                "size": "1024x1536",
                "quality": os.getenv("AI_IMAGE_QUALITY", "medium"),
                "output_format": "png",
                "background": "opaque",
            }
        ],
        "tool_choice": {"type": "image_generation"},
    }
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=TIMEOUT_SECONDS,
    )
    if not response.ok:
        raise RuntimeError(f"OpenAI image generation failed ({response.status_code}): {response.text[:500]}")

    raw = base64.b64decode(_extract_image_b64(response.json()))
    generated = Image.open(io.BytesIO(raw)).convert("RGB")
    # 1024x1536 -> cover 1080x1920, then center crop.
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
        result.save(debug_path, "JPEG", quality=92)
    return result
