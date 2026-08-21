# Talk N Walks audio library

Reels choose audio by content mood instead of using the same ambient pad every day.

## Moods
`energy`, `bold`, `joyful`, `bright`, `warm`, `calm`, `reflective`, `cinematic`

To use real licensed tracks, add audio files under:

`audio/<mood>/`

Supported formats: WAV, MP3, M4A, AAC, FLAC, OGG.

The builder rotates available files deterministically by Day. If a mood folder has no track, the pipeline generates an original instrumental cue so publishing can continue safely.

Only add music that @talksnwalks101 owns or is licensed to use. Do not download copyrighted/trending Instagram audio into this repository without explicit usage rights.

Theme-to-mood mapping lives in `data/audio_mappings.csv`.

Native Instagram/trending-audio attachment is a separate future integration and should not replace this reliable fallback until tested.
