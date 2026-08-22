"""Apply rights-aware, topic-aware audio to an already-built Talk N Walks Reel."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from audio_engine import prepare_audio, replace_reel_audio


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

    audio_info = prepare_audio(
        theme=theme,
        day=day,
        output_path=generated_audio,
        duration=duration,
        stream=stream,
        topic=topic,
        history_contexts=contexts[:day],
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
        f"source={audio_info['source']} file={audio_path}{recommendation}"
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
