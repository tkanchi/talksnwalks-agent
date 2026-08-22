"""Deterministic illustration rotation for Talk N Walks.

All illustrations live in one ``illustrations/`` folder. The filename convention
identifies the audience and topic, for example::

    women_fitness_deadlift_01.png
    men_friendship_beach_group_01.png
    kids_friendship_cycling_01.png
    teens_wellness_meditation_circle_01.png
    all_love_beach_walk_01.png
    family_fatherhood_reading_with_child_01.png

The selector filters that single folder for the requested publishing stream,
removes exact duplicate files by SHA-256, then spreads filenames across topic
keys. Because build_reel indexes this ordered list by Day, every eligible unique
image is used once before an image repeats.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from pathlib import Path


KNOWN_PREFIXES = {"women", "men", "kids", "teens", "all", "family"}


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _filename_parts(filename: str) -> list[str]:
    return [part for part in Path(filename).stem.lower().split("_") if part]


def _topic_key(filename: str) -> str:
    parts = _filename_parts(filename)
    if parts and parts[0] in KNOWN_PREFIXES and len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else "other"


def _eligible_for_stream(filename: str, stream: str | None) -> bool:
    if not stream:
        return True

    parts = _filename_parts(filename)
    if not parts:
        return False

    audience = parts[0]
    topic = parts[1] if len(parts) >= 2 else ""
    stream = stream.lower()

    if stream == "women":
        return audience in {"women", "all", "family"}

    if stream == "men":
        return audience in {"men", "all", "family"}

    if stream in {"children", "kids", "teens"}:
        # Do not feed generic adult/couple ``all_*`` scenes to children. Neutral
        # nature art is the only ``all`` category admitted to this stream.
        return audience in {"kids", "teens", "family"} or (
            audience == "all" and topic == "nature"
        )

    raise ValueError(f"Unknown illustration stream: {stream}")


def unique_illustration_names(directory: Path, stream: str | None = None) -> list[str]:
    """Return eligible unique PNGs in deterministic, category-spread order."""
    directory = Path(directory)
    paths = sorted(
        (
            path
            for path in directory.glob("*.png")
            if _eligible_for_stream(path.name, stream)
        ),
        key=lambda path: path.name.lower(),
    )
    if not paths:
        label = f" for stream '{stream}'" if stream else ""
        raise FileNotFoundError(f"No eligible PNG illustrations found in {directory}{label}")

    seen_hashes: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        fingerprint = _content_hash(path)
        if fingerprint in seen_hashes:
            continue
        seen_hashes.add(fingerprint)
        unique_paths.append(path)

    groups: dict[str, deque[str]] = defaultdict(deque)
    for path in unique_paths:
        groups[_topic_key(path.name)].append(path.name)

    ordered: list[str] = []
    keys = sorted(groups)
    while any(groups[key] for key in keys):
        for key in keys:
            if groups[key]:
                ordered.append(groups[key].popleft())

    return ordered


def apply_illustration_pool(
    build_reel,
    directory: Path | None = None,
    stream: str | None = None,
) -> list[str]:
    """Apply the single-folder, non-repeating illustration pool to build_reel."""
    target = Path(directory or build_reel.ILLUSTRATION_DIR)
    names = unique_illustration_names(target, stream=stream)
    build_reel.ILLUSTRATION_DIR = target
    build_reel.ILLUSTRATIONS = names
    print(f"Illustration pool [{stream or 'all'}]: {len(names)} unique PNGs")
    return names
