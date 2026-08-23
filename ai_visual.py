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
from PIL import Image


API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = os.getenv("AI_IMAGE_MODEL", "gpt-image-2")
TIMEOUT_SECONDS = 240


def _scene_prompt(quote: str, audience: str = "All", topic: str = "Mindset") -> str:
    audience = (audience or "All").strip()
    topic = (topic or "Mindset").strip()
    neutral = audience.lower() in {"all", "adults", "general", ""}

    if neutral:
        audience_rule = (
            "This quote is universal. Make the visual genuinely unisex. Prefer a "
            "beautiful environment or elegant visual metaphor such as a balcony, "
            "road, workspace, travel scene, car, bicycle, journal, coffee, books, "
            "ocean, mountains, architecture, accessories or nature. Use a person "
            "only when the quote clearly benefits from one; do not default to a woman."
        )
    else:
        audience_rule = (
            f"The intended audience is {audience}. A person may appear when it "
            "meaningfully improves the quote. Keep people natural, inclusive and "
            "age-appropriate, and vary setting, pose, clothing and composition."
        )

    return f"""Create ONLY the background artwork for a premium vertical Instagram motivational post.

Quote to interpret visually: {quote}
Audience: {audience}
Topic: {topic}

LOCKED TALKS N WALKS VISUAL DIRECTION — MATCH THIS FEEL CONSISTENTLY:
- Vertical 2:3 artwork that will be center-cropped to 9:16.
- A rich, polished digital lifestyle illustration with cinematic depth — the feeling of an elegant editorial illustration or beautifully rendered storybook scene, NOT a flat graphic.
- Peaceful, aspirational and emotionally warm. Colourful but sophisticated rather than loud.
- Palette may use lavender, blush, peach, cream, sage, powder blue, muted teal, warm gold and sunset/sunrise light.
- Full-frame visual storytelling: the scene should feel complete and luxurious, with meaningful foreground/midground/background detail.
- Allow attractive framing details along the sides and lower half: plants, furniture, architecture, landscape, books, a desk, travel objects, fabric, windows, railings, city or nature details when appropriate.
- Reserve a CLEAN, naturally lighter text window across roughly the upper-middle 30–40 percent. It can be sky, softly lit wall, mist, distant view or window light, but it must still belong to the illustrated scene.
- Do NOT make most of the canvas empty. Do NOT create a plain gradient with a few geometric shapes.
- Do NOT use flat-vector mountains, minimalist poster art, clip-art, icon-style scenery, children's flat illustration, or generic stock-background composition.
- Use soft natural/cinematic lighting, gentle texture, refined detail and realistic depth while retaining an illustrated finish.
- Interpret the meaning of THIS quote and design a different setting when the idea changes. Avoid repeating the same balcony, woman, flowers, coffee or books composition every day.
- {audience_rule}
- No words, letters, numbers, captions, quote text, author names, usernames, watermarks, logos, readable signs, readable book covers or readable screens anywhere in the generated artwork.
- Do NOT generate the Talks N Walks logo. Branding is added afterward from a fixed asset.
- Keep enough contrast in the text window for dark charcoal serif typography without placing a dark overlay there.

The desired overall impression is: serene + detailed + premium + colourful illustrated lifestyle scene, with the quote naturally floating over a calm part of the artwork.

Return one polished finished background scene only."""


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
        raise RuntimeError(
            "OPENAI_API_KEY is required for Talks N Walks AI artwork, including "
            "build-only visual tests. Configure the GitHub Actions secret; a generic "
            "fallback image will not be substituted."
        )

    body = {
        "model": DEFAULT_MODEL,
        "prompt": _scene_prompt(quote, audience=audience, topic=topic),
        "size": os.getenv("AI_IMAGE_SIZE", "1024x1536"),
        "quality": os.getenv("AI_IMAGE_QUALITY", "medium"),
        "output_format": "png",
    }

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
