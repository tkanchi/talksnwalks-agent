# Talk N Walks audio library

Audio selection is now rights-aware and topic-aware.

## Two lanes

### 1. `auto`
Only music that we own or have confirmed reusable rights for may be embedded in automatically published Reels.

Add each approved track to `data/audio_catalog.csv` with:
- `Lane=auto`
- `RightsStatus=rights_cleared`, `owned`, `original`, or `public_domain`
- a real repository `FilePath`
- `Active=true`

The selector scores mood + quote topic + audience and uses every eligible track in that stream before reusing one.

### 2. `instagram_library`
Commercial/trending songs are recommendation-only. They are never embedded in the MP4 by this pipeline.

This lane is for songs that may be available through Instagram's licensed music library, including current hits and nostalgic tracks. The build records the recommended track and artist in `publish.env` so it can be reviewed or attached natively in Instagram where permitted.

## Moods
`energy`, `bold`, `joyful`, `bright`, `warm`, `calm`, `reflective`, `cinematic`

Theme-to-mood mapping lives in `data/audio_mappings.csv`.

## Catalogue
`data/audio_catalog.csv`

Important fields:
`TrackID, Track, Artist, Mood, Audience, Topics, Era, Lane, RightsStatus, FilePath, TrendScore, PopularityScore, NostalgiaScore, Active, Notes`

`TrendScore` is intended to be refreshed as trend research changes. `PopularityScore` and `NostalgiaScore` are slower-moving ranking inputs.

## Fallback
If no active rights-cleared `auto` track exists, the pipeline first checks the legacy `audio/<mood>/` folder and otherwise generates an original Talk N Walks instrumental cue. This preserves build reliability.

Supported embedded formats: WAV, MP3, M4A, AAC, FLAC, OGG.

Never download or commit copyrighted commercial music merely because it is popular, purchased, streamed, or available on Instagram. The `instagram_library` lane is metadata/recommendation only.
