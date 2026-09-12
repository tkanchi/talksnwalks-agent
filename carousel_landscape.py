"""Landscape artwork for Talk N Walks carousel posts.

Carousel artwork is isolated from the daily quote visual system. One landscape
is generated per carousel and reused with subtle slide-level crops. Landscape
families rotate with the carousel library so the same family cannot repeat
within the previous four sequential carousel posts.
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import os
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageOps

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
    "misty_mountains": "Layered misty mountain ridges in cool blue-grey tones, atmospheric depth, a quiet valley below, soft cloud cover, no dramatic sunset.",
    "quiet_lake": "A calm reflective lake with distant low mountains and soft morning haze, subtle ripples, cool natural light, no obvious sun disc.",
    "open_meadow": "An expansive meadow with fine grasses and tiny understated wildflowers, distant tree line, pale open sky, gentle diffused daylight.",
    "soft_shoreline": "A peaceful shoreline with pale water, soft foamy edge, muted sand and a wide hazy sky; serene rather than tropical or postcard-bright.",
    "rolling_valley": "Layered rolling green-grey hills and a broad valley disappearing into haze, soft overcast light, elegant natural depth.",
    "dawn_field": "A spacious early-morning field with delicate fog and a pale luminous sky, light just beginning to warm the horizon without a strong visible sunrise.",
    "forest_path": "A quiet path through a refined misty forest, slender trees, soft filtered light and depth, peaceful and uncluttered rather than dark or dense.",
    "desert_dunes": "Minimal sculptural sand dunes in soft beige and dusty peach, long gentle curves, pale sky, refined editorial calm, no harsh orange sunset.",
    "snowy_peaks": "Distant icy mountain peaks with soft snow, pale blue atmosphere and broad open sky, crisp but gentle, premium and serene rather than dramatic.",
    "cliff_coast": "A muted coastal cliff and distant sea under a soft cloudy sky, elegant windswept grasses, large open atmospheric space, no tourist-postcard look.",
}

FALLBACK_PALETTES = {
    "misty_mountains": ((154, 181, 202), (238, 230, 216), (146, 167, 180), (105, 131, 146), (72, 99, 115), (130, 151, 158)),
    "quiet_lake": ((160, 190, 208), (241, 236, 222), (151, 173, 184), (107, 139, 153), (75, 108, 123), (139, 163, 169)),
    "open_meadow": ((180, 205, 199), (247, 238, 217), (168, 188, 162), (117, 147, 112), (80, 110, 76), (207, 218, 187)),
    "soft_shoreline": ((169, 199, 214), (247, 237, 219), (160, 187, 196), (112, 151, 163), (78, 116, 130), (228, 212, 187)),
    "rolling_valley": ((176, 197, 187), (243, 235, 218), (157, 181, 155), (108, 142, 106), (75, 108, 73), (199, 215, 185)),
    "dawn_field": ((207, 184, 195), (249, 231, 207), (190, 175, 160), (143, 129, 112), (103, 95, 82), (222, 210, 181)),
    "forest_path": ((164, 188, 179), (235, 231, 213), (136, 163, 147), (96, 130, 107), (63, 94, 74), (187, 201, 174)),
    "desert_dunes": ((219, 195, 178), (249, 231, 207), (217, 188, 159), (185, 149, 119), (148, 113, 89), (229, 198, 162)),
    "snowy_peaks": ((165, 197, 216), (239, 242, 236), (169, 190, 199), (116, 145, 160), (82, 111, 128), (220, 228, 224)),
    "cliff_coast": ((164, 194, 207), (240, 235, 218), (152, 178, 181), (104, 139, 145), (72, 103, 109), (196, 195, 168)),
}


def _stable_index(carousel_id: str, library: list[dict]) -> int:
    ids = [str(item.get("CarouselID", "")) for item in library]
    if carousel_id in ids:
        return ids.index(carousel_id)
    digest = hashlib.sha256(carousel_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def choose_landscape_family(carousel_id: str, library: list[dict]) -> str:
    override = os.getenv("CAROUSEL_LANDSCAPE", "").strip()
    if override:
        if override not in LANDSCAPE_FAMILIES:
            raise ValueError(f"Unknown CAROUSEL_LANDSCAPE '{override}'")
        return override
    index = _stable_index(carousel_id, library)
    family = LANDSCAPE_FAMILIES[index % len(LANDSCAPE_FAMILIES)]
    recent = {LANDSCAPE_FAMILIES[(index - n) % len(LANDSCAPE_FAMILIES)] for n in range(1, RECENT_REPEAT_BLOCK + 1)}
    if family in recent:
        raise RuntimeError(f"Landscape rotation would repeat '{family}' inside the recent window")
    return family


def _scene_prompt(*, family: str, carousel_id: str, audience: str, topic: str) -> str:
    return f"""Create ONLY the background artwork for a premium Instagram carousel slide.
Carousel: {carousel_id}
Audience: {audience or 'All'}
Topic: {topic or 'Mindset'}
Landscape family: {family}
Specific scenery direction: {FAMILY_DIRECTIONS[family]}

LOCKED TALK N WALKS CAROUSEL LANDSCAPE DIRECTION:
- Vertical 4:5 composition intended for 1080x1350.
- Beautiful scenic LANDSCAPE only. No people, faces, bodies, animals or characters.
- Premium editorial fine-art photography / softly painterly photographic realism.
- Serene, sophisticated, muted, atmospheric and visually rich without becoming busy.
- Keep the upper and upper-middle portion relatively calm and low-detail for typography.
- Put strongest landscape detail mainly in the lower half and outer edges.
- Avoid a large obvious sun disc. Avoid turning every scene into a sunset.
- No oversaturated orange, neon colour, HDR, fantasy lighting or stock-photo clichés.
- No text, letters, numbers, logos, signs, captions, borders, frames or watermarks.
- Edge-to-edge landscape, not a blank white canvas.
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
    return image.convert("RGBA")


def _organic_profile(width: int, height: int, base: float, amplitude: float, seed: int, *, controls: int = 30, peaks: int = 4):
    rng = random.Random(seed)
    xs = [i * width / (controls - 1) for i in range(controls)]
    values = [base + rng.uniform(-amplitude * .10, amplitude * .10) for _ in range(controls)]
    centers = rng.sample(range(2, controls - 2), min(peaks, controls - 4))
    for center in centers:
        peak_height = rng.uniform(.42, .92) * amplitude
        spread = rng.uniform(2.2, 5.2)
        for i in range(controls):
            values[i] -= peak_height * math.exp(-((i - center) / spread) ** 2)
    phase = rng.random() * math.tau
    for i in range(controls):
        values[i] += amplitude * .12 * math.sin(i * .31 + phase)
    for _ in range(2):
        values = [values[0]] + [(values[i-1] + 2*values[i] + values[i+1]) / 4 for i in range(1, controls-1)] + [values[-1]]
    return [(round(x), round(v * height)) for x, v in zip(xs, values)]


def _add_clouds(base: Image.Image, opacity: int = 45) -> Image.Image:
    width, height = base.size
    noise = Image.effect_noise((max(1, width // 4), max(1, height // 4)), 28)
    noise = noise.resize((width, height), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(max(25, width / 20)))
    noise = ImageOps.autocontrast(noise)
    alpha = noise.point(lambda p: int(max(0, p - 148) * opacity / 107))
    cloud = Image.new("RGBA", (width, height), (250, 247, 240, 255))
    cloud.putalpha(alpha)
    return Image.alpha_composite(base, cloud)


def _add_fog(base: Image.Image, y: int, thickness: int, alpha: int) -> Image.Image:
    width, height = base.size
    fog = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fog)
    draw.rectangle((0, y-thickness, width, y+thickness), fill=(248, 246, 239, alpha))
    fog = fog.filter(ImageFilter.GaussianBlur(max(25, thickness * .7)))
    return Image.alpha_composite(base, fog)


def _add_textured_ridge(base: Image.Image, points, color, alpha: int, *, blur: int = 4) -> Image.Image:
    width, height = base.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(points + [(width, height), (0, height)], fill=alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    noise = Image.effect_noise((max(1, width // 3), max(1, height // 3)), 24)
    noise = noise.resize((width, height), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(8))
    noise = ImageOps.autocontrast(noise)
    dark = _mix(color, (35, 45, 50), .11)
    light = _mix(color, (245, 244, 238), .09)
    textured = ImageOps.colorize(noise, dark, light).convert("RGBA")
    textured.putalpha(mask)
    return Image.alpha_composite(base, textured)


def _fallback_landscape(family: str, width: int, height: int) -> Image.Image:
    """Soft painterly scenic fallback used when the image API secret is unavailable."""
    sky_top, sky_bottom, far, mid, near, ground = FALLBACK_PALETTES[family]
    base = _add_clouds(_vertical_gradient(width, height, sky_top, sky_bottom), 48)
    seed_base = LANDSCAPE_FAMILIES.index(family) * 1000 + 97

    if family in {"misty_mountains", "quiet_lake", "snowy_peaks"}:
        p1 = _organic_profile(width, height, .60, .18, seed_base + 1, controls=34, peaks=5)
        p2 = _organic_profile(width, height, .71, .16, seed_base + 2, controls=30, peaks=4)
        p3 = _organic_profile(width, height, .83, .12, seed_base + 3, controls=28, peaks=3)
        base = _add_textured_ridge(base, p1, far, 165, blur=5)
        base = _add_fog(base, int(height * .61), int(height * .045), 55)
        base = _add_textured_ridge(base, p2, mid, 195, blur=5)
        base = _add_fog(base, int(height * .72), int(height * .038), 42)
        base = _add_textured_ridge(base, p3, near, 220, blur=6)
        if family == "quiet_lake":
            lake = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lake)
            water = _mix(sky_top, (230, 237, 232), .45)
            ld.rectangle((0, int(height*.82), width, height), fill=(*water, 165))
            for frac in (.86, .90, .94):
                y = int(height * frac)
                ld.line((int(width*.08), y, int(width*.94), y-4), fill=(246, 244, 237, 42), width=3)
            lake = lake.filter(ImageFilter.GaussianBlur(5))
            base = Image.alpha_composite(base, lake)
        elif family == "snowy_peaks":
            snow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            sd = ImageDraw.Draw(snow)
            for x_frac, y_frac, size in ((.28,.48,.08),(.57,.43,.10),(.80,.51,.07)):
                x, y = int(width*x_frac), int(height*y_frac)
                sd.polygon([(x-int(width*size), y+int(height*.05)), (x,y), (x+int(width*size), y+int(height*.06))], fill=(246,247,244,150))
            snow = snow.filter(ImageFilter.GaussianBlur(3))
            base = Image.alpha_composite(base, snow)

    elif family in {"open_meadow", "rolling_valley", "dawn_field"}:
        p1 = _organic_profile(width, height, .67, .09, seed_base+1, controls=28, peaks=3)
        p2 = _organic_profile(width, height, .78, .075, seed_base+2, controls=26, peaks=3)
        p3 = _organic_profile(width, height, .88, .055, seed_base+3, controls=24, peaks=2)
        base = _add_textured_ridge(base, p1, far, 170, blur=6)
        base = _add_fog(base, int(height*.70), int(height*.035), 38)
        base = _add_textured_ridge(base, p2, mid, 190, blur=5)
        base = _add_textured_ridge(base, p3, ground, 220, blur=4)
        if family == "dawn_field":
            glow = Image.new("RGBA", (width,height),(0,0,0,0)); gd=ImageDraw.Draw(glow)
            cx,cy=int(width*.72),int(height*.34); r=int(width*.18)
            gd.ellipse((cx-r,cy-r,cx+r,cy+r), fill=(255,235,210,70))
            glow=glow.filter(ImageFilter.GaussianBlur(int(width*.09))); base=Image.alpha_composite(base,glow)
        detail = Image.new("RGBA", (width,height),(0,0,0,0)); dd=ImageDraw.Draw(detail)
        for x in range(int(width*.05), int(width*.96), max(25,width//34)):
            y=int(height*.88)+((x//17)%23)
            dd.line((x,y,x+random.Random(seed_base+x).randint(-4,7),y+random.Random(seed_base+x+1).randint(28,55)), fill=(*near,55), width=2)
        detail=detail.filter(ImageFilter.GaussianBlur(1)); base=Image.alpha_composite(base,detail)

    elif family == "forest_path":
        floor = _organic_profile(width,height,.83,.05,seed_base+4,controls=24,peaks=2)
        base = _add_textured_ridge(base, floor, ground, 215, blur=5)
        trees=Image.new("RGBA",(width,height),(0,0,0,0)); td=ImageDraw.Draw(trees)
        rng=random.Random(seed_base)
        for side in (0,1):
            for i in range(9):
                x=int(width*(rng.uniform(.02,.34) if side==0 else rng.uniform(.66,.98)))
                top=int(height*rng.uniform(.22,.42)); bottom=int(height*rng.uniform(.78,.98)); tw=max(5,int(width*rng.uniform(.006,.016)))
                td.rounded_rectangle((x,top,x+tw,bottom),radius=tw//2,fill=(*near,rng.randint(55,115)))
                crown_r=int(width*rng.uniform(.035,.075))
                td.ellipse((x-crown_r,top-crown_r//2,x+crown_r,top+crown_r),fill=(*mid,rng.randint(35,75)))
        path=[(int(width*.41),height),(int(width*.59),height),(int(width*.53),int(height*.60)),(int(width*.49),int(height*.60))]
        td.polygon(path,fill=(232,224,201,145))
        trees=trees.filter(ImageFilter.GaussianBlur(4)); base=Image.alpha_composite(base,trees)

    elif family in {"soft_shoreline", "cliff_coast"}:
        ocean=Image.new("RGBA",(width,height),(0,0,0,0)); od=ImageDraw.Draw(ocean)
        water=_mix(sky_top,(225,235,231),.43)
        od.rectangle((0,int(height*.58),width,height),fill=(*water,185))
        for frac in (.68,.73,.79,.84):
            y=int(height*frac); od.arc((int(width*.02),y-35,int(width*1.08),y+150),start=190,end=233,fill=(248,246,238,105),width=5)
        ocean=ocean.filter(ImageFilter.GaussianBlur(4)); base=Image.alpha_composite(base,ocean)
        shore=_organic_profile(width,height,.84,.035,seed_base+6,controls=26,peaks=2)
        base=_add_textured_ridge(base,shore,ground,205,blur=4)
        if family=="cliff_coast":
            cliff=Image.new("RGBA",(width,height),(0,0,0,0)); cd=ImageDraw.Draw(cliff)
            cliff_pts=[(0,int(height*.46)),(int(width*.16),int(height*.49)),(int(width*.29),int(height*.66)),(int(width*.25),height),(0,height)]
            cd.polygon(cliff_pts,fill=(*near,215)); cliff=cliff.filter(ImageFilter.GaussianBlur(5)); base=Image.alpha_composite(base,cliff)

    elif family == "desert_dunes":
        p1=_organic_profile(width,height,.73,.055,seed_base+7,controls=28,peaks=2)
        p2=_organic_profile(width,height,.86,.05,seed_base+8,controls=26,peaks=2)
        base=_add_textured_ridge(base,p1,far,190,blur=5)
        base=_add_textured_ridge(base,p2,ground,225,blur=4)
        shadow=Image.new("RGBA",(width,height),(0,0,0,0)); sd=ImageDraw.Draw(shadow)
        sd.arc((int(width*.10),int(height*.67),int(width*.95),int(height*1.02)),start=186,end=226,fill=(*near,55),width=6)
        shadow=shadow.filter(ImageFilter.GaussianBlur(4)); base=Image.alpha_composite(base,shadow)

    grain = Image.effect_noise((width, height), 2.8).convert("L")
    grain_layer = Image.new("RGBA", (width, height), (255,255,255,0))
    grain_layer.putalpha(grain.point(lambda p: max(0, min(8, abs(p-128)//10))))
    result = Image.alpha_composite(base, grain_layer).convert("RGB")
    result.info["source"] = "procedural_landscape"
    return result


def _crop_generated(generated: Image.Image, width: int, height: int) -> Image.Image:
    scale=max(width/generated.width,height/generated.height)
    resized=generated.resize((round(generated.width*scale),round(generated.height*scale)),Image.Resampling.LANCZOS)
    left=max(0,(resized.width-width)//2); top=max(0,(resized.height-height)//2)
    return resized.crop((left,top,left+width,top+height))


def generate_landscape_background(*, family: str, carousel_id: str, audience: str="All", topic: str="Mindset", width: int=1080, height: int=1350, debug_path: Path|None=None) -> Image.Image:
    if family not in FAMILY_DIRECTIONS:
        raise ValueError(f"Unsupported landscape family: {family}")
    api_key=os.getenv("OPENAI_API_KEY","").strip()
    required=os.getenv("CAROUSEL_AI_LANDSCAPE_REQUIRED","false").lower() in {"1","true","yes"}
    result: Image.Image
    if api_key:
        body={"model":DEFAULT_MODEL,"prompt":_scene_prompt(family=family,carousel_id=carousel_id,audience=audience,topic=topic),"size":os.getenv("AI_IMAGE_SIZE","1024x1536"),"quality":os.getenv("AI_IMAGE_QUALITY","medium"),"output_format":"png"}
        try:
            response=requests.post(API_URL,headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},json=body,timeout=TIMEOUT_SECONDS)
            if not response.ok:
                raise RuntimeError(f"OpenAI carousel landscape generation failed ({response.status_code}): {response.text[:500]}")
            raw=_decode_image_response(response.json())
            result=_crop_generated(Image.open(io.BytesIO(raw)).convert("RGB"),width,height)
            result.info["source"]="openai_generated"
        except Exception:
            if required: raise
            result=_fallback_landscape(family,width,height)
    else:
        if required:
            raise RuntimeError("OPENAI_API_KEY is required for premium carousel landscape artwork")
        result=_fallback_landscape(family,width,height)
    if debug_path:
        debug_path.parent.mkdir(parents=True,exist_ok=True)
        result.save(debug_path,"JPEG",quality=94,optimize=True)
    return result
