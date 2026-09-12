"""AI landscape artwork for Talk N Walks carousel posts.

Carousel artwork is deliberately isolated from the daily quote visual system.
One landscape is generated per carousel and reused with subtle slide-level crops.
Landscape families rotate with the carousel library so the same family cannot
repeat within the previous four sequential carousel posts.
"""

from __future__ import annotations

import base64
import hashlib
import io
import os
from pathlib import Path

import requests
from PIL import Image


API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = os.getenv("AI_IMAGE_MODEL", "gpt-image-2")
TIMEOUT_SECONDS = 240
RECENT_REPEAT_BLOCK = 4

# Keep this pool longer than the repeat-block window. Sequential library items
# therefore receive different scenery, while a carousel can still retain one
# cohesive landscape across all of its slides.
LANDSCAPE_FAMILIES = [
    "misty_mountains",
    "quiet_lake",
    "open_meadow",
    "soft_shoreline",
    "rolling_valley",
    "dawn_field",
    "forest_path",
    "desert_dunes",
    "snowy_peaks",
    "cliff_coast",
]

FAMILY_DIRECTIONS = {
    "misty_mountains": (
        "Layered misty mountain ridges in cool blue-grey tones, atmospheric depth, "
        "a quiet valley below, soft cloud cover, no dramatic sunset."
    ),
    "quiet_lake": (
        "A calm reflective lake with distant low mountains and soft morning haze, "
        "subtle ripples, cool natural light, no obvious sun disc."
    ),
    "open_meadow": (
        "An expansive meadow with fine grasses and tiny understated wildflowers, "
        "distant tree line, pale open sky, gentle diffused daylight."
    ),
    "soft_shoreline": (
        "A peaceful shoreline with pale water, soft foamy edge, muted sand and a "
        "wide hazy sky; serene rather than tropical or postcard-bright."
    ),
    "rolling_valley": (
        "Layered rolling green-grey hills and a broad valley disappearing into haze, "
        "soft overcast light, elegant natural depth."
    ),
    "dawn_field": (
        "A spacious early-morning field with delicate fog and a pale luminous sky, "
        "light just beginning to warm the horizon without a strong visible sunrise."
    ),
    "forest_path": (
        "A quiet path through a refined misty forest, slender trees, soft filtered "
        "light and depth, peaceful and uncluttered rather than dark or dense."
    ),
    "desert_dunes": (
        "Minimal sculptural sand dunes in soft beige and dusty peach, long gentle "
        "curves, pale sky, refined editorial calm, no harsh orange sunset."
    ),
    "snowy_peaks": (
        "Distant icy mountain peaks with soft snow, pale blue atmosphere and broad "
        "open sky, crisp but gentle, premium and serene rather than dramatic."
    ),
    "cliff_coast": (
        "A muted coastal cliff and distant sea under a soft cloudy sky, elegant "
        "windswept grasses, large open atmospheric space, no tourist-postcard look."
    ),
}


def _stable_index(carousel_id: str, library: list[dict]) -> int:
    ids = [str(item.get("CarouselID", "")) for item in library]
    if carousel_id in ids:
        return ids.index(carousel_id)

    # Unknown/manual IDs still receive deterministic scenery without Python's
    # process-randomized hash().
    digest = hashlib.sha256(carousel_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def choose_landscape_family(carousel_id: str, library: list[dict]) -> str:
    """Return a deterministic family with a four-post no-repeat guarantee.

    For the normal sequential library this is a simple rotation through a pool
    of ten families. Because the pool is larger than RECENT_REPEAT_BLOCK, the
    current family cannot match any of the previous four sequential posts.
    """
    override = os.getenv("CAROUSEL_LANDSCAPE", "").strip()
    if override:
        if override not in LANDSCAPE_FAMILIES:
            allowed = ", ".join(LANDSCAPE_FAMILIES)
            raise ValueError(f"Unknown CAROUSEL_LANDSCAPE '{override}'. Allowed: {allowed}")
        return override

    index = _stable_index(carousel_id, library)
    family = LANDSCAPE_FAMILIES[index % len(LANDSCAPE_FAMILIES)]

    # Defensive assertion documents and enforces the no-repeat contract for
    # sequential carousel slots.
    recent = {
        LANDSCAPE_FAMILIES[(index - offset) % len(LANDSCAPE_FAMILIES)]
        for offset in range(1, RECENT_REPEAT_BLOCK + 1)
    }
    if family in recent:
        raise RuntimeError(f"Landscape rotation would repeat '{family}' inside the recent window")
    return family


def _scene_prompt(
    *,
    family: str,
    carousel_id: str,
    audience: str,
    topic: str,
) -> str:
    direction = FAMILY_DIRECTIONS[family]
    return f"""Create ONLY the background artwork for a premium Instagram carousel slide.

Carousel: {carousel_id}
Audience: {audience or 'All'}
Topic: {topic or 'Mindset'}
Landscape family: {family}
Specific scenery direction: {direction}

LOCKED TALK N WALKS CAROUSEL LANDSCAPE DIRECTION:
- Vertical 4:5 composition intended for a 1080x1350 Instagram carousel.
- Beautiful scenic LANDSCAPE only. No people, faces, bodies, animals, characters or portraits.
- Premium editorial fine-art photography / softly painterly photographic realism.
- Visually appealing, serene, sophisticated and emotionally warm; never flat vector art.
- Use real atmospheric depth, soft natural light, subtle texture and elegant muted colour.
- Keep the upper and upper-middle portion relatively calm and low-detail so dark typography can be added later.
- Place the strongest landscape detail mainly in the lower half and toward the outer edges.
- Avoid a large obvious sun disc unless the family specifically requires it. Avoid making every scene a sunset.
- Avoid oversaturated orange, neon colour, HDR, dramatic fantasy lighting, stock-photo clichés and travel-poster styling.
- No text, letters, numbers, logos, signs, captions, borders, frames, watermarks or social-media UI.
- No blank white canvas: the result must clearly read as an elegant landscape from edge to edge.
- Create a distinctive composition for this carousel rather than a generic repeated scenery template.

Return one polished finished landscape background only."""


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


def generate_landscape_background(
    *,
    family: str,
    carousel_id: str,
    audience: str = "All",
    topic: str = "Mindset",
    width: int = 1080,
    height: int = 1350,
    debug_path: Path | None = None,
) -> Image.Image:
    """Generate one text-free landscape background for a complete carousel."""
    if family not in FAMILY_DIRECTIONS:
        raise ValueError(f"Unsupported landscape family: {family}")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    required = os.getenv("CAROUSEL_AI_LANDSCAPE_REQUIRED", "true").lower() in {"1", "true", "yes"}
    if not api_key:
        message = "OPENAI_API_KEY is required for premium carousel landscape artwork"
        if required:
            raise RuntimeError(message)
        raise RuntimeError(message)

    body = {
        "model": DEFAULT_MODEL,
        "prompt": _scene_prompt(
            family=family,
            carousel_id=carousel_id,
            audience=audience,
            topic=topic,
        ),
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
            f"OpenAI carousel landscape generation failed ({response.status_code}): "
            f"{response.text[:500]}"
        )

    raw = _decode_image_response(response.json())
    generated = Image.open(io.BytesIO(raw)).convert("RGB")

    # Cover the 4:5 canvas and center-crop. The generated source is taller, so
    # this keeps high resolution while preserving a calm upper text area.
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
        result.save(debug_path, "JPEG", quality=94, optimize=True)
    return result
