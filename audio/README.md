# Talk N Walks audio library

Audio selection is rights-aware and topic-aware.

## Production audio paths

### 1. Rights-cleared remote library
`data/rights_cleared_audio.csv` contains stock tracks whose license permits use in social-media video. These tracks are downloaded during the GitHub Actions build, embedded into the Reel, and are not committed as binary files to the repository.

Current source: Mixkit free stock music. Mixkit states its free stock music can be used in social-media projects under the Mixkit license.

The selector scores mood + quote topic + audience, varies Women and Men selections, and uses every eligible track in that stream before repeating one.

### 2. `auto` catalogue
`data/audio_catalog.csv` can also contain music that we own or have separately confirmed reusable rights for.

For repository-hosted approved tracks use:
- `Lane=auto`
- `RightsStatus=rights_cleared`, `owned`, `original`, or `public_domain`
- a real repository `FilePath`
- `Active=true`

### 3. `instagram_library`
Commercial/trending songs are recommendation-only. They are never downloaded or embedded in the MP4 by this pipeline.

This lane is for songs that may be available through Instagram's licensed music library, including current hits and nostalgic tracks. The build records the recommended track and artist in `publish.env` so it can be reviewed or attached natively in Instagram where permitted.

## Moods
`energy`, `bold`, `joyful`, `bright`, `warm`, `calm`, `reflective`, `cinematic`

Theme-to-mood mapping lives in `data/audio_mappings.csv`.

## Fallback order
1. Rights-cleared remote track from `data/rights_cleared_audio.csv`
2. Approved repository-hosted/legacy audio
3. Original Talk N Walks generated cue

The generated cue is only a reliability fallback now; it is not the preferred soundtrack.

Supported embedded formats: WAV, MP3, M4A, AAC, FLAC, OGG.

Never download or commit copyrighted commercial music merely because it is popular, purchased, streamed, or available on Instagram. The `instagram_library` lane is metadata/recommendation only.
