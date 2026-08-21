"""Topic-aware audio selection for Talk N Walks Reels.

If licensed audio files are present under audio/<mood>/, one is chosen
deterministically by day. Otherwise an original generated 8-second cue is
created so production never depends on external music availability.
"""

from __future__ import annotations

import csv
import math
import os
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

AUDIO_ROOT = Path(os.getenv("AUDIO_ROOT", "audio"))
MAPPING_FILE = Path(os.getenv("AUDIO_MAPPING_FILE", "data/audio_mappings.csv"))
SUPPORTED_AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
DEFAULT_MOOD = "reflective"

PROFILES = {
    "energy": {
        "bpm": 124,
        "roots": (50, 57, 59, 55),
        "melody": (0, 4, 7, 9, 7, 4, 2, 4),
        "pad": 0.028, "bass": 0.080, "lead": 0.060,
        "kick": 0.110, "snare": 0.045, "hat": 0.025,
    },
    "bold": {
        "bpm": 108,
        "roots": (45, 53, 48, 55),
        "melody": (0, 7, 5, 3, 0, 7, 10, 7),
        "pad": 0.032, "bass": 0.075, "lead": 0.052,
        "kick": 0.090, "snare": 0.032, "hat": 0.018,
    },
    "joyful": {
        "bpm": 118,
        "roots": (48, 55, 57, 53),
        "melody": (0, 4, 7, 12, 9, 7, 4, 7),
        "pad": 0.025, "bass": 0.060, "lead": 0.072,
        "kick": 0.085, "snare": 0.042, "hat": 0.030,
    },
    "bright": {
        "bpm": 112,
        "roots": (60, 67, 69, 65),
        "melody": (0, 4, 7, 11, 12, 7, 4, 2),
        "pad": 0.020, "bass": 0.045, "lead": 0.082,
        "kick": 0.055, "snare": 0.024, "hat": 0.028,
    },
    "warm": {
        "bpm": 88,
        "roots": (48, 57, 53, 55),
        "melody": (0, 4, 7, 4, 9, 7, 4, 2),
        "pad": 0.045, "bass": 0.035, "lead": 0.050,
        "kick": 0.030, "snare": 0.000, "hat": 0.008,
    },
    "calm": {
        "bpm": 72,
        "roots": (57, 53, 48, 55),
        "melody": (0, 7, 4, 2, 0, 4, 7, 4),
        "pad": 0.052, "bass": 0.022, "lead": 0.034,
        "kick": 0.012, "snare": 0.000, "hat": 0.004,
    },
    "reflective": {
        "bpm": 78,
        "roots": (57, 53, 48, 55),
        "melody": (0, 3, 7, 10, 7, 3, 5, 2),
        "pad": 0.046, "bass": 0.030, "lead": 0.040,
        "kick": 0.020, "snare": 0.000, "hat": 0.006,
    },
    "cinematic": {
        "bpm": 96,
        "roots": (45, 53, 48, 55),
        "melody": (0, 7, 12, 10, 7, 5, 3, 7),
        "pad": 0.052, "bass": 0.052, "lead": 0.045,
        "kick": 0.050, "snare": 0.018, "hat": 0.008,
    },
}


def _midi_to_hz(note: float) -> float:
    return 440.0 * (2.0 ** ((note - 69.0) / 12.0))


def load_theme_moods(path: Path = MAPPING_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {
            row["Theme"].strip(): row["Mood"].strip().lower()
            for row in csv.DictReader(f)
            if row.get("Theme") and row.get("Mood")
        }


def resolve_mood(theme: str) -> str:
    theme = theme.strip()
    mapped = load_theme_moods().get(theme)
    if mapped in PROFILES:
        return mapped

    text = theme.lower()
    keyword_rules = (
        (("fitness", "sport", "discipline", "action", "drive"), "energy"),
        (("dance", "fun", "happiness", "friendship", "lifestyle"), "joyful"),
        (("confidence", "courage", "justice", "standard"), "bold"),
        (("childhood", "innocence"), "bright"),
        (("love", "family", "mother", "father", "gratitude"), "warm"),
        (("peace", "spiritual", "rest", "balance", "letting go"), "calm"),
        (("growth", "resilience", "dream", "hope", "becoming", "keep going"), "cinematic"),
    )
    for needles, mood in keyword_rules:
        if any(needle in text for needle in needles):
            return mood
    return DEFAULT_MOOD


def choose_library_track(mood: str, day: int, audio_root: Path = AUDIO_ROOT) -> Path | None:
    folder = audio_root / mood
    if not folder.exists():
        return None
    candidates = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO
    )
    if not candidates:
        return None
    return candidates[(day - 1) % len(candidates)]


def _noise(sample_index: int) -> float:
    value = (sample_index * 1103515245 + 12345) & 0x7FFFFFFF
    return (value / 1073741824.0) - 1.0


def _pluck(t_since: float, freq: float, level: float, bright: bool = False) -> float:
    if t_since < 0 or t_since > 0.55:
        return 0.0
    env = math.exp(-6.5 * t_since)
    sample = math.sin(2 * math.pi * freq * t_since)
    sample += 0.35 * math.sin(2 * math.pi * freq * 2 * t_since)
    if bright:
        sample += 0.22 * math.sin(2 * math.pi * freq * 3 * t_since)
        sample += 0.12 * math.sin(2 * math.pi * freq * 4 * t_since)
    return level * env * sample / (1.69 if bright else 1.35)


def write_generated_track(
    path: Path,
    mood: str,
    day: int,
    duration: float = 8.0,
    sample_rate: int = 48000,
) -> None:
    """Generate a small original instrumental cue for the requested mood."""
    profile = PROFILES.get(mood, PROFILES[DEFAULT_MOOD])
    variant = (day - 1) % 4
    bpm = profile["bpm"] + (variant - 1.5) * 2
    beat_seconds = 60.0 / bpm
    half_beat = beat_seconds / 2.0
    bar_seconds = beat_seconds * 4.0
    roots = profile["roots"]
    melody = profile["melody"]

    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(duration * sample_rate)
    fade_seconds = 0.35

    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        frames = bytearray()
        for i in range(frame_count):
            t = i / sample_rate
            bar_index = int(t / bar_seconds)
            root_note = roots[(bar_index + variant) % len(roots)]
            root_freq = _midi_to_hz(root_note)

            chord_notes = (root_note, root_note + 3 + (bar_index % 2), root_note + 7)
            pad = 0.0
            for note in chord_notes:
                freq = _midi_to_hz(note)
                pad += math.sin(2 * math.pi * freq * t)
                pad += 0.16 * math.sin(2 * math.pi * freq * 2 * t)
            pad *= profile["pad"] / 3.48

            beat_pos = t % beat_seconds
            bass_env = math.exp(-5.5 * beat_pos)
            bass = profile["bass"] * bass_env * math.sin(2 * math.pi * (root_freq / 2.0) * t)

            step = int(t / half_beat)
            step_time = step * half_beat
            melody_degree = melody[(step + variant * 2) % len(melody)]
            lead_note = root_note + 12 + melody_degree
            lead_freq = _midi_to_hz(lead_note)
            bright = mood in {"bright", "joyful", "energy"}
            lead = _pluck(t - step_time, lead_freq, profile["lead"], bright=bright)

            kick = 0.0
            kick_pos = t % beat_seconds
            if kick_pos < 0.16:
                kick_freq = 70.0 - 35.0 * (kick_pos / 0.16)
                kick = profile["kick"] * math.exp(-18.0 * kick_pos) * math.sin(
                    2 * math.pi * kick_freq * kick_pos
                )

            snare = 0.0
            snare_offset = (t + beat_seconds * 0.5) % (beat_seconds * 2.0)
            if snare_offset < 0.10 and profile["snare"]:
                snare = profile["snare"] * math.exp(-28.0 * snare_offset) * _noise(i)

            hat = 0.0
            hat_pos = t % half_beat
            if hat_pos < 0.045 and profile["hat"]:
                hat = profile["hat"] * math.exp(-55.0 * hat_pos) * _noise(i * 7 + 17)

            sample = pad + bass + lead + kick + snare + hat
            fade = min(1.0, t / fade_seconds, max(0.0, (duration - t) / fade_seconds))
            sample *= fade * 0.92
            sample = max(-0.92, min(0.92, sample))
            frames.extend(struct.pack("<h", int(sample * 32767)))

        wav.writeframes(frames)


def prepare_audio(
    theme: str,
    day: int,
    output_path: Path,
    duration: float = 8.0,
) -> dict[str, str | Path]:
    """Pick a licensed library track when available, else create original audio."""
    mood = resolve_mood(theme)
    library_track = choose_library_track(mood, day)
    if library_track:
        return {"path": library_track, "mood": mood, "source": "library"}

    write_generated_track(output_path, mood=mood, day=day, duration=duration)
    return {"path": output_path, "mood": mood, "source": "generated"}


def replace_reel_audio(video_path: Path, audio_path: Path, duration: float = 8.0) -> None:
    """Replace only the Reel audio track, preserving the rendered video stream."""
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    with tempfile.NamedTemporaryFile(
        suffix=".mp4", prefix="talksnwalks_audio_", dir=video_path.parent, delete=False
    ) as tmp:
        temp_path = Path(tmp.name)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-t", str(duration),
        "-c:v", "copy",
        "-c:a", "aac",
        "-ar", "48000",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(temp_path),
    ]
    try:
        subprocess.run(cmd, check=True)
        os.replace(temp_path, video_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
