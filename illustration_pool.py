"""Topic-aware illustration selection for Talk N Walks.

All illustrations live in one ``illustrations/`` folder and use:

    audience_topic_scene_XX.png

The selector uses the quote Topic plus ``data/topics.csv`` IllustrationTags to
prefer a relevant scene. Matching is a preference only: every eligible unique
image is exhausted before any image can repeat.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict, deque
from pathlib import Path


FILENAME_RE = re.compile(
    r"^(women|men|kids|teens|all|family)_([a-z0-9]+)_([a-z0-9_]+)_([0-9]{2})\.png$"
)

# Small semantic bridge between canonical taxonomy tags and the broad second
# token in illustration filenames. The taxonomy remains the source of truth;
# these aliases only help words such as "gym" find ``*_fitness_*`` artwork.
TOKEN_ALIASES = {
    "friend": {"friendship"},
    "friends": {"friendship"},
    "group": {"friendship"},
    "conversation": {"friendship"},
    "teamwork": {"friendship"},
    "couple": {"love", "relationships"},
    "partners": {"love", "relationships"},
    "married": {"love", "relationships"},
    "mother": {"motherhood", "family"},
    "mom": {"motherhood", "family"},
    "mother-child": {"motherhood", "family"},
    "father": {"fatherhood", "family"},
    "dad": {"fatherhood", "family"},
    "father-child": {"fatherhood", "family"},
    "parent-child": {"family", "togetherness"},
    "siblings": {"family", "togetherness"},
    "home": {"family", "togetherness"},
    "workout": {"fitness"},
    "gym": {"fitness"},
    "training": {"fitness", "sports"},
    "running": {"fitness", "sports"},
    "healthy-lifestyle": {"wellness", "fitness"},
    "water": {"wellness"},
    "sleep": {"wellness"},
    "rest": {"wellness", "nature"},
    "recovery": {"wellness"},
    "peace": {"wellness", "nature"},
    "reflection": {"wellness", "reading", "nature"},
    "meditation": {"wellness", "nature"},
    "quiet": {"wellness", "reading", "nature"},
    "healing": {"wellness", "nature"},
    "confidence": {"confidence"},
    "standing-tall": {"confidence"},
    "work": {"career"},
    "office": {"career"},
    "ceo": {"career"},
    "startup": {"career"},
    "planning": {"career"},
    "desk": {"career"},
    "leadership": {"career"},
    "finance": {"career"},
    "action": {"career", "fitness"},
    "books": {"reading", "study"},
    "book": {"reading", "study"},
    "reading": {"reading"},
    "learning": {"reading", "study", "school"},
    "study": {"study", "school", "reading"},
    "school": {"school", "study"},
    "kids": {"school", "friendship"},
    "teens": {"school", "friendship"},
    "helping": {"friendship", "family"},
    "respect": {"friendship", "family"},
    "equality": {"friendship", "school"},
    "journey": {"travel", "nature"},
    "roadtrip": {"travel"},
    "beach": {"travel", "nature"},
    "hiking": {"travel", "nature"},
    "climbing": {"travel", "fitness"},
    "sunrise": {"nature", "travel"},
    "coffee": {"lifestyle", "reading"},
    "laughter": {"lifestyle", "friendship"},
    "dancing": {"music", "lifestyle"},
    "music": {"music", "lifestyle"},
    "headphones": {"music", "lifestyle"},
    "sports": {"sports", "fitness"},
    "team": {"sports", "friendship"},
    "phone": {"school"},
}

QUOTE_KEYWORDS = {
    "gym": "fitness",
    "workout": "fitness",
    "book": "reading",
    "read": "reading",
    "study": "study",
    "school": "school",
    "friend": "friendship",
    "love": "love",
    "relationship": "relationships",
    "mother": "motherhood",
    "mom": "motherhood",
    "father": "fatherhood",
    "dad": "fatherhood",
    "family": "family",
    "career": "career",
    "business": "career",
    "travel": "travel",
    "adventure": "travel",
    "music": "music",
    "dance": "music",
    "peace": "wellness",
    "rest": "wellness",
    "heal": "wellness",
    "health": "wellness",
    "sport": "sports",
}


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalise_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _tokenise(value: str) -> set[str]:
    value = (value or "").lower().replace("&", " ")
    parts = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", value)
    tokens = set(parts)
    for token in list(tokens):
        tokens.update(TOKEN_ALIASES.get(token, set()))
    return tokens


def _parse_filename(filename: str) -> dict[str, str] | None:
    match = FILENAME_RE.fullmatch(filename.lower())
    if not match:
        return None
    audience, topic, scene, variant = match.groups()
    return {
        "audience": audience,
        "topic": topic,
        "scene": scene,
        "variant": variant,
    }


def _topic_key(filename: str) -> str:
    parsed = _parse_filename(filename)
    return parsed["topic"] if parsed else "other"


def _eligible_for_stream(filename: str, stream: str | None) -> bool:
    parsed = _parse_filename(filename)
    if not parsed:
        return False
    if not stream:
        return True

    audience = parsed["audience"]
    topic = parsed["topic"]
    stream = stream.lower()

    if stream == "women":
        return audience in {"women", "all", "family"}

    if stream == "men":
        return audience in {"men", "all", "family"}

    if stream in {"children", "kids", "teens"}:
        # Generic adult/couple all_* scenes are excluded. Neutral nature is safe.
        return audience in {"kids", "teens", "family"} or (
            audience == "all" and topic == "nature"
        )

    raise ValueError(f"Unknown illustration stream: {stream}")


def _unique_paths(directory: Path, stream: str | None = None) -> list[Path]:
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
        raise FileNotFoundError(
            f"No eligible, correctly named PNG illustrations found in {directory}{label}"
        )

    seen_hashes: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        fingerprint = _content_hash(path)
        if fingerprint in seen_hashes:
            continue
        seen_hashes.add(fingerprint)
        unique_paths.append(path)
    return unique_paths


def unique_illustration_names(directory: Path, stream: str | None = None) -> list[str]:
    """Return eligible unique PNGs in deterministic, topic-spread order."""
    unique_paths = _unique_paths(directory, stream=stream)

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


def _load_taxonomy_tags(topics_file: Path) -> dict[str, set[str]]:
    topics_file = Path(topics_file)
    if not topics_file.exists():
        return {}

    result: dict[str, set[str]] = {}
    with topics_file.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            topic = _normalise_label(row.get("Topic", ""))
            if not topic:
                continue
            tokens = _tokenise(row.get("Topic", ""))
            tokens.update(_tokenise(row.get("Category", "")))
            tokens.update(_tokenise(row.get("IllustrationTags", "")))
            result[topic] = tokens
    return result


def _quote_tokens(row: dict[str, str], taxonomy: dict[str, set[str]]) -> set[str]:
    topic = _normalise_label(row.get("Topic", ""))
    tokens = set(taxonomy.get(topic, set()))
    tokens.update(_tokenise(row.get("Topic", "")))
    tokens.update(_tokenise(row.get("Theme", "")))

    quote_words = set(re.findall(r"[a-z]+", row.get("Quote", "").lower()))
    for keyword, tag in QUOTE_KEYWORDS.items():
        if keyword in quote_words:
            tokens.add(tag)

    # Expand again after Topic/Theme and quote-keyword additions.
    for token in list(tokens):
        tokens.update(TOKEN_ALIASES.get(token, set()))
    return tokens


def _image_tokens(path: Path) -> set[str]:
    parsed = _parse_filename(path.name)
    if not parsed:
        return set()
    tokens = {parsed["topic"]}
    tokens.update(_tokenise(parsed["scene"].replace("_", " ")))
    for token in list(tokens):
        tokens.update(TOKEN_ALIASES.get(token, set()))
    return tokens


def _audience_score(audience: str, stream: str) -> int:
    stream = stream.lower()
    if stream == "women":
        return {"women": 30, "all": 18, "family": 12}.get(audience, 0)
    if stream == "men":
        return {"men": 30, "all": 18, "family": 12}.get(audience, 0)
    if stream in {"children", "kids", "teens"}:
        return {"kids": 30, "teens": 28, "family": 14, "all": 6}.get(audience, 0)
    return 0


def _candidate_score(
    path: Path,
    quote_tokens: set[str],
    stream: str,
) -> int:
    parsed = _parse_filename(path.name)
    if not parsed:
        return -10_000

    image_tokens = _image_tokens(path)
    score = _audience_score(parsed["audience"], stream)

    # A direct broad-topic match is strongest.
    if parsed["topic"] in quote_tokens:
        score += 120

    # Scene/taxonomy overlap then refines the match.
    overlap = quote_tokens & image_tokens
    score += min(60, 10 * len(overlap))

    # Nature remains a useful low-priority neutral fallback.
    if parsed["topic"] == "nature":
        score += 6

    return score


def matched_illustration_names(
    directory: Path,
    quote_file: Path,
    *,
    stream: str,
    topics_file: Path = Path("data/topics.csv"),
) -> list[str]:
    """Return one topic-aware illustration assignment per quote row.

    A complete eligible-image cycle is exhausted before any image can repeat.
    """
    pool = _unique_paths(directory, stream=stream)
    with Path(quote_file).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Quote file is empty: {quote_file}")

    taxonomy = _load_taxonomy_tags(topics_file)
    spread_order = unique_illustration_names(directory, stream=stream)
    spread_rank = {name: index for index, name in enumerate(spread_order)}

    available = list(pool)
    selected: list[str] = []
    last_name: str | None = None

    for row in rows:
        if not available:
            available = list(pool)

        quote_tokens = _quote_tokens(row, taxonomy)
        ranked = sorted(
            available,
            key=lambda path: (
                -_candidate_score(path, quote_tokens, stream),
                spread_rank[path.name],
                path.name.lower(),
            ),
        )

        chosen = ranked[0]
        # Avoid an immediate repeat across cycle boundaries when possible.
        if chosen.name == last_name and len(ranked) > 1:
            chosen = ranked[1]

        selected.append(chosen.name)
        last_name = chosen.name
        available.remove(chosen)

    return selected


def audit_illustrations(directory: Path) -> dict[str, object]:
    """Return naming counts and exact-content duplicate groups."""
    directory = Path(directory)
    paths = sorted(directory.glob("*.png"), key=lambda path: path.name.lower())

    invalid: list[str] = []
    audience_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    hashes: dict[str, list[str]] = defaultdict(list)

    for path in paths:
        parsed = _parse_filename(path.name)
        if not parsed:
            invalid.append(path.name)
        else:
            audience_counts[parsed["audience"]] += 1
            topic_counts[parsed["topic"]] += 1
        hashes[_content_hash(path)].append(path.name)

    duplicate_groups = [names for names in hashes.values() if len(names) > 1]
    return {
        "total_pngs": len(paths),
        "valid_pngs": len(paths) - len(invalid),
        "invalid_names": invalid,
        "audience_counts": dict(sorted(audience_counts.items())),
        "topic_counts": dict(sorted(topic_counts.items())),
        "duplicate_groups": duplicate_groups,
    }


def write_inventory_csv(directory: Path, destination: Path) -> Path:
    """Write a current inventory from filenames and exact file hashes."""
    directory = Path(directory)
    destination = Path(destination)
    paths = sorted(directory.glob("*.png"), key=lambda path: path.name.lower())

    first_by_hash: dict[str, str] = {}
    rows: list[dict[str, str]] = []
    for path in paths:
        parsed = _parse_filename(path.name)
        fingerprint = _content_hash(path)
        duplicate_of = first_by_hash.get(fingerprint, "")
        first_by_hash.setdefault(fingerprint, path.name)
        rows.append(
            {
                "Filename": path.name,
                "Audience": parsed["audience"] if parsed else "",
                "TopicTag": parsed["topic"] if parsed else "",
                "Scene": parsed["scene"] if parsed else "",
                "Variant": parsed["variant"] if parsed else "",
                "ValidName": "yes" if parsed else "no",
                "DuplicateOf": duplicate_of,
            }
        )

    fields = [
        "Filename", "Audience", "TopicTag", "Scene",
        "Variant", "ValidName", "DuplicateOf",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def apply_illustration_pool(
    build_reel,
    directory: Path | None = None,
    stream: str | None = None,
    quote_file: Path | None = None,
    topics_file: Path = Path("data/topics.csv"),
) -> list[str]:
    """Apply topic-aware assignments, or legacy topic-spread rotation."""
    target = Path(directory or build_reel.ILLUSTRATION_DIR)

    if quote_file is not None:
        if not stream:
            raise ValueError("stream is required when quote_file is supplied")
        names = matched_illustration_names(
            target,
            quote_file,
            stream=stream,
            topics_file=topics_file,
        )
        unique_count = len(_unique_paths(target, stream=stream))
        print(
            f"Illustration assignments [{stream}]: {len(names)} days "
            f"across {unique_count} unique eligible PNGs"
        )
    else:
        names = unique_illustration_names(target, stream=stream)
        print(f"Illustration pool [{stream or 'all'}]: {len(names)} unique PNGs")

    build_reel.ILLUSTRATION_DIR = target
    build_reel.ILLUSTRATIONS = names
    return names
