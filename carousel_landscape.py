"""Landscape artwork for Talk N Walks carousel posts.

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
from PIL import Image, ImageDraw, ImageFilter


API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = os.getenv("AI_IMAGE_MODEL", "gpt-image-2")
TIMEOUT_SECONDS = 240
RECENT_REPEAT_BLOCK = 4

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

FALLBACK_PALETTES = {
    "misty_mountains": ((173, 192, 207), (241, 235, 225), (158, 174, 184), (120, 139, 151), (91, 110, 122), (214, 218, 211)),
    "quiet_lake": ((168, 195, 211), (239, 239, 229), (163, 181, 188), (119, 145, 156), (84, 117, 130), (208, 220, 218)),
    "open_meadow": ((187, 205, 197), (248, 239, 219), (175, 190, 166), (127, 151, 120), (92, 119, 88), (216, 221, 196)),
    "soft_shoreline": ((178, 203, 215), (247, 239, 222), (169, 194, 201), (124, 159, 169), (92, 128, 140), (230, 216, 192)),
    "rolling_valley": ((183, 198, 188), (242, 236, 220), (164, 181, 158), (118, 143, 112), (85, 110, 82), (209, 217, 190)),
    "dawn_field": ((213, 190, 197), (250, 232, 210), (193, 177, 164), (147, 132, 116), (112, 103, 92), (224, 213, 185)),
    "forest_path": ((170, 188, 179), (235, 232, 214), (145, 166, 151), (104, 132, 111), (72, 99, 79), (191, 202, 176)),
    "desert_dunes": ((221, 197, 180), (249, 232, 208), (218, 190, 163), (188, 153, 124), (155, 121, 96), (230, 199, 163)),
    "snowy_peaks": ((174, 202, 218), (238, 242, 238), (174, 191, 198), (124, 149, 163), (91, 117, 132), (222, 229, 225)),
    "cliff_coast": ((170, 195, 205), (239, 235, 219), (158, 180, 181), (112, 141, 145), (79, 107, 111), (197, 196, 170)),
}


def _stable_index(carousel_id: str, library: list[dict]) -> int:
    ids = [str(item.get("CarouselID", "")) for item in library]
    if carousel_id in ids:
        return ids.index(carousel_id)
    digest = hashlib.sha256(carousel_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def choose_landscape_family(carousel_id: str, library: list[dict]) -> str:
    """Return a deterministic family with a four-post no-repeat guarantee."""
    override = os.getenv("CAROUSEL_LANDSCAPE", "").strip()
    if override:
        if override not in LANDSCAPE_FAMILIES:
            allowed = ", ".join(LANDSCAPE_FAMILIES)
            raise ValueError(f"Unknown CAROUSEL_LANDSCAPE '{override}'. Allowed: {allowed}")
        return override

    index = _stable_index(carousel_id, library)
    family = LANDSCAPE_FAMILIES[index % len(LANDSCAPE_FAMILIES)]
    recent = {
        LANDSCAPE_FAMILIES[(index - offset) % len(LANDSCAPE_FAMILIES)]
        for offset in range(1, RECENT_REPEAT_BLOCK + 1)
    }
    if family in recent:
        raise RuntimeError(f"Landscape rotation would repeat '{family}' inside the recent window")
    return family


def _scene_prompt(*, family: str, carousel_id: str, audience: str, topic: str) -> str:
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


def _mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _vertical_gradient(width: int, height: int, top, bottom) -> Image.Image:
    image = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        draw.line((0, y, width, y), fill=_mix(top, bottom, y / max(1, height - 1)))
    return image


def _scaled_points(points, width: int, height: int):
    return [(round(x * width), round(y * height)) for x, y in points]


def _fallback_landscape(family: str, width: int, height: int) -> Image.Image:
    """Create a soft scenic fallback when the image API secret is unavailable."""
    sky_top, sky_bottom, far, mid, near, ground = FALLBACK_PALETTES[family]
    image = _vertical_gradient(width, height, sky_top, sky_bottom).convert("RGBA")

    haze = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    hd = ImageDraw.Draw(haze, "RGBA")
    hd.rectangle((0, int(height * 0.33), width, int(height * 0.66)), fill=(250, 246, 237, 48))
    haze = haze.filter(ImageFilter.GaussianBlur(max(18, width // 35)))
    image = Image.alpha_composite(image, haze)

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    if family in {"misty_mountains", "quiet_lake", "snowy_peaks"}:
        far_pts = _scaled_points([(0, .53), (.12, .48), (.24, .52), (.37, .43), (.5, .50), (.64, .40), (.77, .49), (.9, .44), (1, .51), (1, 1), (0, 1)], width, height)
        mid_pts = _scaled_points([(0, .66), (.15, .59), (.29, .65), (.44, .54), (.6, .63), (.74, .54), (.88, .61), (1, .57), (1, 1), (0, 1)], width, height)
        near_pts = _scaled_points([(0, .79), (.17, .72), (.33, .78), (.48, .69), (.63, .77), (.79, .68), (.92, .75), (1, .72), (1, 1), (0, 1)], width, height)
        d.polygon(far_pts, fill=(*far, 155))
        d.polygon(mid_pts, fill=(*mid, 175))
        d.polygon(near_pts, fill=(*near, 165))
        if family == "snowy_peaks":
            snow = (246, 246, 241, 185)
            d.polygon(_scaled_points([(.28, .49), (.37, .43), (.45, .51)], width, height), fill=snow)
            d.polygon(_scaled_points([(.54, .48), (.64, .40), (.73, .50)], width, height), fill=snow)
        if family == "quiet_lake":
            water = _mix(sky_top, (236, 240, 235), .45)
            d.rectangle((0, int(height * .68), width, int(height * .93)), fill=(*water, 150))
            for frac in (.72, .76, .81, .86):
                y = int(height * frac)
                d.line((int(width * .08), y, int(width * .92), y - 5), fill=(247, 246, 238, 55), width=3)

    elif family in {"open_meadow", "rolling_valley", "dawn_field"}:
        hill1 = _scaled_points([(0, .58), (.18, .52), (.37, .57), (.58, .48), (.78, .55), (1, .50), (1, 1), (0, 1)], width, height)
        hill2 = _scaled_points([(0, .70), (.2, .64), (.42, .69), (.65, .61), (.84, .67), (1, .63), (1, 1), (0, 1)], width, height)
        floor = _scaled_points([(0, .83), (.22, .78), (.45, .83), (.7, .77), (.9, .82), (1, .80), (1, 1), (0, 1)], width, height)
        d.polygon(hill1, fill=(*far, 165))
        d.polygon(hill2, fill=(*mid, 178))
        d.polygon(floor, fill=(*ground, 205))
        if family == "dawn_field":
            glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow, "RGBA")
            cx, cy = int(width * .72), int(height * .33)
            r = int(width * .20)
            gd.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(255, 238, 211, 95))
            glow = glow.filter(ImageFilter.GaussianBlur(int(width * .08)))
            image = Image.alpha_composite(image, glow)
        for x in range(int(width * .06), int(width * .96), max(28, width // 28)):
            y = int(height * .83) + ((x // 13) % 19)
            d.line((x, y, x + 7, y + int(height * .035)), fill=(*near, 70), width=2)

    elif family == "forest_path":
        d.rectangle((0, int(height * .56), width, height), fill=(*ground, 190))
        for frac, alpha in ((.08, 135), (.18, 110), (.83, 110), (.93, 135)):
            x = int(width * frac)
            trunk_w = max(8, width // 80)
            d.rounded_rectangle((x, int(height*.27), x+trunk_w, int(height*.92)), radius=trunk_w//2, fill=(*near, alpha))
        path = _scaled_points([(.43, 1), (.57, 1), (.53, .61), (.49, .61)], width, height)
        d.polygon(path, fill=(231, 222, 198, 180))
        for frac in (.31, .39, .68, .76):
            x = int(width * frac)
            d.line((x, int(height*.44), x, int(height*.82)), fill=(*mid, 80), width=max(4, width//160))

    elif family in {"soft_shoreline", "cliff_coast"}:
        water = _mix(sky_top, (226, 236, 232), .38)
        d.rectangle((0, int(height * .57), width, int(height * .86)), fill=(*water, 165))
        d.polygon(_scaled_points([(0, .78), (.3, .73), (.55, .77), (.75, .72), (1, .75), (1, 1), (0, 1)], width, height), fill=(*ground, 200))
        for frac in (.67, .72, .78):
            y = int(height * frac)
            d.arc((int(width*.05), y-25, int(width*1.03), y+130), start=190, end=232, fill=(248, 246, 237, 150), width=5)
        if family == "cliff_coast":
            d.polygon(_scaled_points([(0, .48), (.22, .52), (.33, .69), (.28, 1), (0, 1)], width, height), fill=(*near, 200))
            for x in range(int(width*.05), int(width*.28), max(24, width//35)):
                d.line((x, int(height*.48), x+5, int(height*.43)), fill=(*ground, 90), width=2)

    elif family == "desert_dunes":
        d.polygon(_scaled_points([(0, .68), (.17, .61), (.38, .66), (.61, .57), (.82, .64), (1, .60), (1, 1), (0, 1)], width, height), fill=(*far, 180))
        d.polygon(_scaled_points([(0, .83), (.22, .75), (.44, .80), (.68, .70), (.86, .78), (1, .74), (1, 1), (0, 1)], width, height), fill=(*ground, 210))
        d.arc((int(width*.12), int(height*.69), int(width*.92), int(height*1.05)), start=186, end=226, fill=(*near, 75), width=5)

    layer = layer.filter(ImageFilter.GaussianBlur(max(1.5, width / 700)))
    image = Image.alpha_composite(image, layer)

    noise = Image.effect_noise((width, height), 4).convert("L")
    grain = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    grain.putalpha(noise.point(lambda p: max(0, min(12, abs(p - 128) // 7))))
    image = Image.alpha_composite(image, grain)
    result = image.convert("RGB")
    result.info["source"] = "procedural_landscape"
    return result


def _crop_generated(generated: Image.Image, width: int, height: int) -> Image.Image:
    scale = max(width / generated.width, height / generated.height)
    resized = generated.resize(
        (round(generated.width * scale), round(generated.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


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
    required = os.getenv("CAROUSEL_AI_LANDSCAPE_REQUIRED", "false").lower() in {"1", "true", "yes"}
    result: Image.Image

    if api_key:
        body = {
            "model": DEFAULT_MODEL,
            "prompt": _scene_prompt(family=family, carousel_id=carousel_id, audience=audience, topic=topic),
            "size": os.getenv("AI_IMAGE_SIZE", "1024x1536"),
            "quality": os.getenv("AI_IMAGE_QUALITY", "medium"),
            "output_format": "png",
        }
        try:
            response = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
                timeout=TIMEOUT_SECONDS,
            )
            if not response.ok:
                raise RuntimeError(
                    f"OpenAI carousel landscape generation failed ({response.status_code}): {response.text[:500]}"
                )
            raw = _decode_image_response(response.json())
            result = _crop_generated(Image.open(io.BytesIO(raw)).convert("RGB"), width, height)
            result.info["source"] = "openai_generated"
        except Exception:
            if required:
                raise
            result = _fallback_landscape(family, width, height)
    else:
        if required:
            raise RuntimeError("OPENAI_API_KEY is required for premium carousel landscape artwork")
        result = _fallback_landscape(family, width, height)

    if debug_path:
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(debug_path, "JPEG", quality=94, optimize=True)
    return result
