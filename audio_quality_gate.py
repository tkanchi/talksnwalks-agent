"""Fail build-only validation if a configured real audio track was not embedded."""

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


def require_real_audio(output_dir: Path) -> None:
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

    if source != "rights_cleared_remote":
        raise RuntimeError(
            "Real audio quality gate failed: expected rights_cleared_remote, "
            f"got {source or 'missing'}. Track={artist} - {track}. "
            "Do not treat this build as audio-approved."
        )

    if not track_id or not track:
        raise RuntimeError("Real audio quality gate failed: selected track metadata is missing.")

    print(f"Real audio verified: {track_id} | {artist} - {track}")
