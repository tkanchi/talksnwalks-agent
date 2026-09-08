from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

# Standalone 4:5 background generator for Talk N Walks feed posts.
# Patterns stay intentionally very light so quote text and illustrations remain the focus.
DEFAULT_SIZE = (1080, 1350)

PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "vanilla": {"base": (255, 255, 255), "ink": (232, 232, 232), "accent": (248, 243, 230)},
    "seafoam": {"base": (253, 255, 254), "ink": (222, 238, 231), "accent": (239, 248, 244)},
    "powder": {"base": (253, 254, 255), "ink": (224, 233, 242), "accent": (239, 245, 250)},
    "blush": {"base": (255, 253, 253), "ink": (241, 225, 228), "accent": (250, 240, 242)},
    "lavender": {"base": (254, 253, 255), "ink": (232, 226, 242), "accent": (245, 241, 250)},
    "apricot": {"base": (255, 254, 252), "ink": (241, 230, 217), "accent": (251, 244, 235)},
    "ice": {"base": (253, 255, 255), "ink": (224, 236, 239), "accent": (240, 248, 249)},
    "mint": {"base": (253, 255, 253), "ink": (226, 239, 228), "accent": (241, 249, 242)},
    "petal": {"base": (255, 253, 254), "ink": (240, 226, 234), "accent": (250, 241, 246)},
    "sky": {"base": (253, 254, 255), "ink": (224, 233, 244), "accent": (239, 245, 252)},
}

PATTERNS = (
    "grid",
    "dots",
    "pinstripe",
    "diagonal",
    "checker",
    "notebook",
    "wide_grid",
    "waves",
)


def _stable_index(family: str, index: int) -> int:
    token = f"{family}:{index}".encode("utf-8")
    digest = hashlib.sha256(token).digest()
    return int.from_bytes(digest[:4], "big")


def _grid(draw: ImageDraw.ImageDraw, size: tuple[int, int], ink, spacing: int = 52) -> None:
    width, height = size
    for x in range(10, width, spacing):
        draw.line((x, 0, x, height), fill=ink, width=2)
    for y in range(0, height, spacing):
        draw.line((0, y, width, y), fill=ink, width=2)


def _dots(draw: ImageDraw.ImageDraw, size: tuple[int, int], ink, spacing: int = 54) -> None:
    width, height = size
    radius = 2
    for y in range(spacing // 2, height, spacing):
        for x in range(spacing // 2, width, spacing):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=ink)


def _pinstripe(draw: ImageDraw.ImageDraw, size: tuple[int, int], ink, spacing: int = 42) -> None:
    width, height = size
    for x in range(0, width, spacing):
        draw.line((x, 0, x, height), fill=ink, width=2)


def _diagonal(draw: ImageDraw.ImageDraw, size: tuple[int, int], ink, spacing: int = 58) -> None:
    width, height = size
    for start in range(-height, width + height, spacing):
        draw.line((start, height, start + height, 0), fill=ink, width=2)


def _checker(draw: ImageDraw.ImageDraw, size: tuple[int, int], accent, cell: int = 90) -> None:
    width, height = size
    for row, y in enumerate(range(0, height, cell)):
        for col, x in enumerate(range(0, width, cell)):
            if (row + col) % 2 == 0:
                draw.rectangle((x, y, x + cell, y + cell), fill=accent)


def _notebook(draw: ImageDraw.ImageDraw, size: tuple[int, int], ink, accent) -> None:
    width, height = size
    spacing = 48
    for y in range(spacing, height, spacing):
        draw.line((0, y, width, y), fill=ink, width=2)
    margin_x = 88
    draw.line((margin_x, 0, margin_x, height), fill=accent, width=2)


def _wide_grid(draw: ImageDraw.ImageDraw, size: tuple[int, int], ink) -> None:
    _grid(draw, size, ink, spacing=84)


def _waves(draw: ImageDraw.ImageDraw, size: tuple[int, int], ink) -> None:
    width, height = size
    band = 86
    for y in range(-band, height + band, band):
        for x in range(-band, width + band, band * 2):
            draw.arc((x, y, x + band * 2, y + band), 0, 180, fill=ink, width=2)


def generate_background(
    width: int = DEFAULT_SIZE[0],
    height: int = DEFAULT_SIZE[1],
    *,
    family: str = "vanilla",
    index: int = 0,
    pattern: str | None = None,
) -> Image.Image:
    """Return a deterministic, subtle patterned RGB background."""
    family_key = (family or "vanilla").strip().lower()
    palette = PALETTES.get(family_key, PALETTES["vanilla"])

    if pattern is None:
        seed = _stable_index(family_key, index)
        pattern = PATTERNS[seed % len(PATTERNS)]
    pattern = pattern.strip().lower()
    if pattern not in PATTERNS:
        raise ValueError(f"Unknown background pattern: {pattern}")

    canvas = Image.new("RGB", (width, height), palette["base"])
    draw = ImageDraw.Draw(canvas)
    size = (width, height)

    if pattern == "grid":
        _grid(draw, size, palette["ink"])
    elif pattern == "dots":
        _dots(draw, size, palette["ink"])
    elif pattern == "pinstripe":
        _pinstripe(draw, size, palette["ink"])
    elif pattern == "diagonal":
        _diagonal(draw, size, palette["ink"])
    elif pattern == "checker":
        _checker(draw, size, palette["accent"])
    elif pattern == "notebook":
        _notebook(draw, size, palette["ink"], palette["accent"])
    elif pattern == "wide_grid":
        _wide_grid(draw, size, palette["ink"])
    elif pattern == "waves":
        _waves(draw, size, palette["ink"])

    return canvas


def save_background(
    output_path: str | Path,
    *,
    width: int = DEFAULT_SIZE[0],
    height: int = DEFAULT_SIZE[1],
    family: str = "vanilla",
    index: int = 0,
    pattern: str | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = generate_background(
        width,
        height,
        family=family,
        index=index,
        pattern=pattern,
    )
    image.save(output, "PNG", optimize=True)
    return output


if __name__ == "__main__":
    preview_dir = Path("outputs/background_preview")
    families = list(PALETTES)
    for i, name in enumerate(PATTERNS):
        output = save_background(
            preview_dir / f"{i + 1:02d}_{name}.png",
            family=families[i % len(families)],
            index=i,
            pattern=name,
        )
        print(output)
