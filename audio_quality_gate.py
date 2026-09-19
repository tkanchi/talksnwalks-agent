"""Validate that an approved audio source was embedded in the built Reel."""

from pathlib import Path


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def require_real_audio(output_dir: Path, *, allow_generated: bool = False) -> None:
    env_path = Path(output_dir) / "publish.env"
    if not env_path.exists():
        raise FileNotFoundError(f"Missing audio build metadata: {env_path}")

    values = _read_env(env_path)
    if values.get("SKIP", "").lower() == "true":
        return

    source = values.get("AUDIO_SOURCE", "")
    track = values.get("AUDIO_TRACK", "")
    artist = values.get("AUDIO_ARTIST", "")
    track_id = values.get("AUDIO_TRACK_ID", "")

    approved_sources = {"rights_cleared_remote"}
    if allow_generated:
        approved_sources.add("generated_v2")

    if source not in approved_sources:
        expected = ", ".join(sorted(approved_sources))
        raise RuntimeError(
            f"Audio quality gate failed: expected one of [{expected}], "
            f"got {source or 'missing'}. Track={artist} - {track}. "
            "Do not treat this build as audio-approved."
        )

    if source == "rights_cleared_remote" and (not track_id or not track):
        raise RuntimeError("Audio quality gate failed: selected remote track metadata is missing.")

    if source == "generated_v2" and (not track or not artist):
        raise RuntimeError("Audio quality gate failed: generated track metadata is missing.")

    print(f"Audio verified: {source} | {track_id} | {artist} - {track}")
