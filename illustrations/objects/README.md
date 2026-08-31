# Talk N Walks — Premium Object Illustration Library

This folder is the source location for the Phase 2 minimalist object illustration system.

## Visual direction

- Tiny symbolic objects instead of people.
- Premium editorial line art; refined rather than icon-like.
- Thin soft-dark-brown strokes on transparent backgrounds.
- No text, quote, username, border, frame or unnecessary scenery.
- No heavy fills, gradients, pencil texture, crosshatching or cartoon treatment.
- Keep generous negative space around the object.
- One object per asset.
- Objects must remain readable at small size on 1080×1920 quote posts.

## Master generation prompt

Create a tiny premium minimalist line-art illustration of **[OBJECT]**. Elegant thin soft-dark-brown monochrome outlines, modern editorial style, refined and sophisticated, clean smooth curves, minimal detail, no heavy shading, no crosshatching, no text, no frame, no background scenery. Isolated object only, transparent background, balanced negative space, suitable as a subtle accent on a luxury motivational Instagram quote design. Not cartoonish, not emoji-like, not clip-art, not childish.

Negative constraints: no people, no faces, no typography, no quote, no username, no border, no scene, no thick black strokes, no pencil texture, no crosshatching, no 3D rendering, no cartoon style.

## Naming

Final production PNGs should use:

`obj_<file_stem>_01.png`

Examples:

- `obj_sprout_01.png`
- `obj_open_book_01.png`
- `obj_compass_01.png`
- `obj_clock_01.png`

Future variants increment the suffix (`_02`, `_03`) without changing the semantic object name.

## Size and transparency

Preferred source canvas: 1024×1024 RGBA with transparent background. Keep the actual drawing compact and centered with substantial transparent margin. Phase 3 will control final placement/scale on the Instagram canvas.

## Source of truth

Object-to-topic mappings and approved placements live in `data/illustration_objects.csv`.

## Production safety

The legacy `illustrations/` scene assets remain in place until the new object renderer and selector pass build-only tests. Do not point live workflows at this folder until Phase 3 validation is complete.
