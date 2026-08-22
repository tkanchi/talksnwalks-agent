"""Deterministic illustration rotation for Talk N Walks.

All PNGs in a stream's illustration folder are auto-detected. Exact duplicate
files are removed by SHA-256, then filenames are spread across topic/category
keys so the feed gets variety. Because build_reel indexes this list by Day,
every unique image is used once before any image repeats.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from pathlib import Path


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _topic_key(filename: str) -> str:
    parts = Path(filename).stem.lower().split("_")
    if parts and parts[0] in {"women", "men", "kids", "teens", "all"} and len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else "other"


def unique_illustration_names(directory: Path) -> list[str]:
    """Return all unique PNGs in a deterministic, category-spread order."""
    directory = Path(directory)
    paths = sorted(directory.glob("*.png"), key=lambda path: path.name.lower())
    if not paths:
        raise FileNotFoundError(f"No PNG illustrations found in {directory}")

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


def apply_illustration_pool(build_reel, directory: Path | None = None) -> list[str]:
    """Apply the auto-detected non-repeating illustration pool to build_reel."""
    target = Path(directory or build_reel.ILLUSTRATION_DIR)
    names = unique_illustration_names(target)
    build_reel.ILLUSTRATION_DIR = target
    build_reel.ILLUSTRATIONS = names
    return names
