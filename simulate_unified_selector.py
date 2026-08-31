from __future__ import annotations

import argparse
import json
import shutil
from datetime import timedelta
from pathlib import Path

from PIL import Image

from select_next_post import (
    append_history,
    build_selection,
    clean,
    history_entries,
    is_book_eligible,
    load_history,
    output_payload,
    parse_iso_date,
    safe_for_youth_context,
    write_history,
)
from build_feed_preview import CANVAS_H, CANVAS_W, compose

ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "outputs" / "unified_selector"
PREVIEW_DIR = OUTPUT_ROOT / "previews"
SELECTION_DIR = OUTPUT_ROOT / "selections"
HISTORY_FILE = OUTPUT_ROOT / "simulation_history.json"
MANIFEST_FILE = OUTPUT_ROOT / "simulation_manifest.json"


def reset_outputs() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    SELECTION_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build-only simulation of consecutive unified post selections."
    )
    parser.add_argument("--start-date", default="")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()

    if args.count < 1:
        raise RuntimeError("count must be at least 1")

    reset_outputs()
    start = parse_iso_date(args.start_date)
    history = load_history(HISTORY_FILE)
    manifest: list[dict] = []

    for index in range(args.count):
        selection_date = start + timedelta(days=index)
        selection = build_selection(selection_date, history)

        if not is_book_eligible(selection):
            raise RuntimeError(f"Ineligible quote selected: {selection.get('QuoteID')}")

        payload = output_payload(selection)
        if payload["audience"] in {"Kids", "Teens", "Kids|Teens"}:
            if not safe_for_youth_context(selection):
                raise RuntimeError(f"Youth safety failed: {selection.get('QuoteID')}")

        selection_path = SELECTION_DIR / f"{index + 1:02d}_{payload['quote_id']}.json"
        selection_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        preview_path = PREVIEW_DIR / (
            f"{index + 1:02d}_{selection_date.isoformat()}_{payload['quote_id']}.png"
        )
        compose(selection, preview_path, index=index)

        with Image.open(preview_path) as image:
            if image.size != (CANVAS_W, CANVAS_H):
                raise RuntimeError(
                    f"Unexpected preview dimensions for {preview_path}: {image.size}"
                )

        append_history(history, selection)
        manifest.append(payload)

    write_history(HISTORY_FILE, history)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    quote_ids = [item["quote_id"] for item in manifest]
    if len(set(quote_ids)) != len(quote_ids):
        raise RuntimeError("Simulation selected duplicate QuoteIDs")

    object_ids = [item["object_id"] for item in manifest]
    for previous, current in zip(object_ids, object_ids[1:]):
        if previous == current:
            raise RuntimeError(f"Immediate illustration repeat: {current}")

    if len(history_entries(history)) != args.count:
        raise RuntimeError("Simulation history count does not match requested count")

    print(f"Simulated {len(manifest)} unified next-post selections")
    print(f"Start date: {start.isoformat()}")
    print(f"Unique QuoteIDs: {len(set(quote_ids))}")
    print(f"Unique books: {len({item['book'] for item in manifest})}")
    print(f"Unique topics: {len({item['topic'] for item in manifest})}")
    print(f"Unique illustrations: {len(set(object_ids))}")
    print(f"Occasion selections: {sum(1 for item in manifest if item['event_id'])}")
    print(MANIFEST_FILE)


if __name__ == "__main__":
    main()
