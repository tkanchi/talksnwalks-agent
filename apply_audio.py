"""Apply topic-aware audio to an already-built Talk N Walks Reel."""

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


def load_theme(quotes_file: Path, day: int) -> str:
    with quotes_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if day < 1 or day > len(rows):
        raise ValueError(f"Day {day} is outside {quotes_file} range 1-{len(rows)}")
    return rows[day - 1]["Theme"].strip()


def apply_audio_to_build(
    quotes_file: Path,
    output_dir: Path,
    duration: float = 8.0,
) -> None:
    env_path = Path(output_dir) / "publish.env"
    metadata = read_env_file(env_path)
    if metadata.get("SKIP", "").lower() == "true":
        print("Audio step skipped because no Reel is due.")
        return

    day = int(metadata["DAY_NUMBER"])
    day_padded = metadata.get("DAY_PADDED", f"{day:03d}")
    video_path = Path(metadata["VIDEO_FILE"])
    theme = load_theme(Path(quotes_file), day)
    generated_audio = Path(output_dir) / f"day_{day_padded}_audio.wav"

    audio_info = prepare_audio(
        theme=theme,
        day=day,
        output_path=generated_audio,
        duration=duration,
    )
    audio_path = Path(audio_info["path"])
    replace_reel_audio(video_path, audio_path, duration=duration)

    update_env_file(
        env_path,
        {
            "AUDIO_MOOD": str(audio_info["mood"]),
            "AUDIO_SOURCE": str(audio_info["source"]),
            "AUDIO_FILE": audio_path.as_posix(),
        },
    )

    print(
        f"Audio applied: mood={audio_info['mood']} "
        f"source={audio_info['source']} file={audio_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quotes-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--duration", type=float, default=8.0)
    args = parser.parse_args()
    apply_audio_to_build(args.quotes_file, args.output_dir, duration=args.duration)


if __name__ == "__main__":
    main()
