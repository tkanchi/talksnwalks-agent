from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from build_feed_preview import compose
from build_unified_shadow import build_caption, build_hashtags, semantic_category
from select_next_post import build_selection, clean, load_history, output_payload

ROOT = Path(__file__).resolve().parent
LIVE_HISTORY = ROOT / "published_logs" / "unified" / "selection_history.json"
OUTPUT_DIR = ROOT / "outputs" / "unified_live"
TZ = ZoneInfo("Asia/Kolkata")


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def clear_output() -> None:
    if not OUTPUT_DIR.exists():
        return
    for path in sorted(OUTPUT_DIR.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build one unified live candidate without publishing or advancing live history."
    )
    parser.add_argument(
        "--selection-date",
        default="",
        help="Optional YYYY-MM-DD selection date; defaults to today in Asia/Kolkata.",
    )
    parser.add_argument("--history", type=Path, default=LIVE_HISTORY)
    args = parser.parse_args()

    on_date = parse_date(args.selection_date) if args.selection_date else datetime.now(TZ).date()
    history = load_history(args.history)
    selection = build_selection(on_date, history)

    clear_output()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_path = OUTPUT_DIR / "post.png"
    publish_image_path = OUTPUT_DIR / "post.jpg"
    caption_path = OUTPUT_DIR / "caption.txt"
    package_path = OUTPUT_DIR / "package.json"

    hashtags = build_hashtags(selection)
    if len(hashtags) != 5:
        raise RuntimeError(f"Expected exactly 5 hashtags, got {hashtags}")
    caption = build_caption(selection, hashtags)

    # Keep the approved renderer untouched. PNG is the canonical render; JPEG is
    # only the delivery copy required by Instagram's single-image publishing flow.
    compose(selection, image_path, index=len(history.get("selections", [])))
    with Image.open(image_path) as rendered:
        rendered.convert("RGB").save(
            publish_image_path,
            format="JPEG",
            quality=95,
            subsampling=0,
            optimize=True,
        )

    package_id = f"{clean(selection.get('SelectionDate'))}_{clean(selection.get('QuoteID'))}"
    payload = output_payload(selection)
    payload.update(
        {
            "mode": "live_candidate",
            "published": False,
            "package_id": package_id,
            "image": image_path.relative_to(ROOT).as_posix(),
            "publish_image": publish_image_path.relative_to(ROOT).as_posix(),
            "public_path": f"public/unified/{package_id}.jpg",
            "caption_category": semantic_category(selection),
            "caption": caption,
            "hashtags": hashtags,
        }
    )

    caption_path.write_text(caption + "\n", encoding="utf-8")
    package_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))
    print("Built unified live candidate only; published=false; live history unchanged")


if __name__ == "__main__":
    main()
