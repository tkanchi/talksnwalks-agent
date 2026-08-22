"""Apply rights-aware, topic-aware audio to an already-built Talk N Walks Reel."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import requests

from audio_engine import prepare_audio, replace_reel_audio, resolve_mood


RIGHTS_AUDIO_FILE = Path("data/rights_cleared_audio.csv")
STREAM_OFFSETS = {"women": 0, "men": 1, "children": 2, "kids": 2, "teens": 2}
RIGHTS_SHORTLIST = 4


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"Build metadata not found: {path}")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def update_env_file(path: Path, additions: dict[str, str]) -> None:
    values = read_env_file(path)
    values.update(additions)
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
        encoding="utf-8",
    )


def load_quote_contexts(quotes_file: Path) -> list[dict[str, str]]:
    with quotes_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No quote rows found in {quotes_file}")
    return [
        {
            "Theme": (row.get("Theme") or "").strip(),
            "Topic": (row.get("Topic") or "").strip(),
        }
        for row in rows
    ]


def load_rights_audio(path: Path = RIGHTS_AUDIO_FILE) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [
            dict(row)
            for row in csv.DictReader(f)
            if (row.get("Active") or "").strip().lower() in {"1", "true", "yes", "y"}
        ]


def _audience_matches(audience: str, stream: str) -> bool:
    audience = (audience or "All").strip().lower()
    stream = stream.strip().lower()
    if audience in {"", "all"}:
        return True
    if audience == "adults":
        return stream in {"women", "men", "all", "adults"}
    if stream == "children":
        return audience in {"kids", "teens", "children"}
    return audience == stream


def _topic_set(row: dict[str, str]) -> set[str]:
    return {
        item.strip().lower()
        for item in (row.get("Topics") or "").split(";")
        if item.strip()
    }


def _rights_score(row: dict[str, str], mood: str, topic: str) -> int:
    score = 0
    if (row.get("Mood") or "").strip().lower() == mood.lower():
        score += 60

    topic_lower = topic.strip().lower()
    topics = _topic_set(row)
    if topic_lower and topic_lower in topics:
        score += 45
    elif topic_lower and any(topic_lower in value or value in topic_lower for value in topics):
        score += 20

    return score


def choose_rights_track(
    rows: list[dict[str, str]],
    *,
    contexts: list[dict[str, str]],
    day: int,
    stream: str,
) -> dict[str, str] | None:
    """Use every eligible rights-cleared track once per stream before repeating."""
    eligible = [row for row in rows if _audience_matches(row.get("Audience", "All"), stream)]
    if not eligible:
        return None

    used: set[str] = set()
    chosen: dict[str, str] | None = None
    stream_offset = STREAM_OFFSETS.get(stream.strip().lower(), 0)

    for index in range(day):
        if len(used) >= len(eligible):
            used.clear()

        context = contexts[index] if index < len(contexts) else contexts[-1]
        mood = resolve_mood(context.get("Theme", ""))
        topic = context.get("Topic", "")
        available = [row for row in eligible if row.get("TrackID", "") not in used]
        available.sort(
            key=lambda row: (
                -_rights_score(row, mood, topic),
                row.get("TrackID", ""),
            )
        )

        shortlist = available[: min(RIGHTS_SHORTLIST, len(available))]
        chosen = shortlist[(stream_offset + index) % len(shortlist)]
        used.add(chosen.get("TrackID", ""))

    return chosen


def download_rights_track(
    row: dict[str, str],
    output_dir: Path,
    day_padded: str,
) -> Path:
    url = (row.get("DownloadURL") or "").strip()
    if not url.startswith("https://"):
        raise ValueError(f"Invalid rights-cleared audio URL for {row.get('TrackID', '')}")

    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix not in {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}:
        suffix = ".mp3"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    track_id = (row.get("TrackID") or "track").strip()
    destination = output_dir / f"day_{day_padded}_rights_{track_id}{suffix}"

    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    bytes_written = 0
    try:
        with destination.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    bytes_written += len(chunk)
        if bytes_written < 4096:
            raise RuntimeError(f"Downloaded audio is unexpectedly small: {bytes_written} bytes")
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return destination


def apply_audio_to_build(
    quotes_file: Path,
    output_dir: Path,
    duration: float = 8.0,
    *,
    stream: str = "all",
) -> None:
    env_path = Path(output_dir) / "publish.env"
    metadata = read_env_file(env_path)
    if metadata.get("SKIP", "").lower() == "true":
        print("Audio step skipped because no Reel is due.")
        return

    day = int(metadata["DAY_NUMBER"])
    day_padded = metadata.get("DAY_PADDED", f"{day:03d}")
    video_path = Path(metadata["VIDEO_FILE"])
    contexts = load_quote_contexts(Path(quotes_file))
    if day < 1 or day > len(contexts):
        raise ValueError(f"Day {day} is outside {quotes_file} range 1-{len(contexts)}")

    theme = contexts[day - 1]["Theme"]
    topic = contexts[day - 1]["Topic"]
    generated_audio = Path(output_dir) / f"day_{day_padded}_audio.wav"

    # Keep the existing recommendation engine and safe generated fallback.
    audio_info = prepare_audio(
        theme=theme,
        day=day,
        output_path=generated_audio,
        duration=duration,
        stream=stream,
        topic=topic,
        history_contexts=contexts[:day],
    )

    # Prefer a real rights-cleared stock track when available. These files are
    # downloaded only during the build and are not committed to the repository.
    rights_row = choose_rights_track(
        load_rights_audio(),
        contexts=contexts[:day],
        day=day,
        stream=stream,
    )
    if rights_row:
        try:
            rights_path = download_rights_track(rights_row, Path(output_dir), day_padded)
            audio_info.update(
                {
                    "path": rights_path,
                    "source": "rights_cleared_remote",
                    "track_id": rights_row.get("TrackID", ""),
                    "track": rights_row.get("Track", ""),
                    "artist": rights_row.get("Artist", ""),
                    "license_source": rights_row.get("Source", ""),
                    "license_url": rights_row.get("LicenseURL", ""),
                }
            )
            if generated_audio.exists() and generated_audio != rights_path:
                generated_audio.unlink()
        except Exception as exc:
            print(
                f"WARNING: rights-cleared audio download failed for "
                f"{rights_row.get('TrackID', '')}: {exc}. Using safe fallback."
            )

    audio_path = Path(audio_info["path"])
    replace_reel_audio(video_path, audio_path, duration=duration)

    update_env_file(
        env_path,
        {
            "AUDIO_MOOD": str(audio_info["mood"]),
            "AUDIO_SOURCE": str(audio_info["source"]),
            "AUDIO_FILE": audio_path.as_posix(),
            "AUDIO_TRACK_ID": str(audio_info.get("track_id", "")),
            "AUDIO_TRACK": str(audio_info.get("track", "")),
            "AUDIO_ARTIST": str(audio_info.get("artist", "")),
            "AUDIO_LICENSE_SOURCE": str(audio_info.get("license_source", "")),
            "AUDIO_LICENSE_URL": str(audio_info.get("license_url", "")),
            "AUDIO_RECOMMENDATION_ID": str(audio_info.get("recommendation_id", "")),
            "AUDIO_RECOMMENDATION_TRACK": str(audio_info.get("recommendation_track", "")),
            "AUDIO_RECOMMENDATION_ARTIST": str(audio_info.get("recommendation_artist", "")),
            "AUDIO_RECOMMENDATION_RIGHTS": str(audio_info.get("recommendation_rights", "")),
        },
    )

    recommendation = ""
    if audio_info.get("recommendation_track"):
        recommendation = (
            f" | Instagram recommendation={audio_info['recommendation_artist']} - "
            f"{audio_info['recommendation_track']}"
        )

    print(
        f"Audio applied: mood={audio_info['mood']} "
        f"source={audio_info['source']} "
        f"track={audio_info.get('artist', '')} - {audio_info.get('track', '')} "
        f"file={audio_path}{recommendation}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quotes-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--stream", default="all")
    args = parser.parse_args()
    apply_audio_to_build(
        args.quotes_file,
        args.output_dir,
        duration=args.duration,
        stream=args.stream,
    )


if __name__ == "__main__":
    main()
