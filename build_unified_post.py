from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from build_feed_preview import compose

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "data" / "content_plan_month_01.csv"
OUTPUT_ROOT = ROOT / "outputs" / "unified_preview"


def normalize(value: str) -> str:
    return (value or "").strip().lower()


def audience_tokens(audience: str) -> set[str]:
    return {
        token.strip().lower()
        for token in (audience or "").replace(",", "|").split("|")
        if token.strip()
    }


def stream_for_audience(audience: str) -> str:
    tokens = audience_tokens(audience)
    if tokens & {"kids", "teens", "children"}:
        return "children"
    if "men" in tokens:
        return "men"
    if "women" in tokens:
        return "women"
    return "general"


def row_matches(row: dict[str, str], audience_filter: str | None) -> bool:
    if not audience_filter:
        return True

    tokens = audience_tokens(row.get("Audience", ""))
    wanted = normalize(audience_filter)

    if wanted == "children":
        return bool(tokens & {"kids", "teens", "children"})
    if wanted == "general":
        return bool(tokens & {"all", "adults", "general"})
    return wanted in tokens


def load_rows(audience_filter: str | None) -> list[dict[str, str]]:
    with PLAN.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row_matches(row, audience_filter)]


def main() -> None:
    audience_filter = os.getenv("AUDIENCE", "").strip() or None
    count = max(1, int(os.getenv("COUNT", "8") or "8"))
    start_index = max(1, int(os.getenv("START_INDEX", "1") or "1"))
    rows = load_rows(audience_filter)

    if not rows:
        raise RuntimeError(f"No rows found for audience={audience_filter!r}")

    selected = rows[start_index - 1 : start_index - 1 + count]
    if len(selected) < count:
        raise RuntimeError(
            f"Requested {count} rows from start index {start_index}, "
            f"only {len(selected)} available"
        )

    if OUTPUT_ROOT.exists():
        for old in OUTPUT_ROOT.rglob("*.png"):
            old.unlink()
        manifest_file = OUTPUT_ROOT / "manifest.json"
        if manifest_file.exists():
            manifest_file.unlink()

    manifest: list[dict[str, str]] = []

    for row_index, row in enumerate(selected, start=start_index):
        audience = row.get("Audience", "All")
        stream = stream_for_audience(audience)
        quote_id = (row.get("QuoteID") or f"post_{row_index:03d}").strip()
        post_number = (row.get("PostNumber") or f"{row_index:03d}").strip()

        out_dir = OUTPUT_ROOT / stream
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{post_number}_{quote_id}.png"

        # Reuse the approved 4:5 renderer exactly; this wrapper adds no visual logic.
        compose(row, output_path, index=row_index - 1)

        manifest.append(
            {
                "output": str(output_path.relative_to(ROOT)),
                "post_number": post_number,
                "quote_id": quote_id,
                "audience": audience,
                "stream": stream,
                "topic_category": row.get("TopicCategory", ""),
                "topic": row.get("Topic", ""),
                "source_type": row.get("SourceType", ""),
                "illustration": row.get("Illustration", ""),
                "background": row.get("BackgroundFamily", ""),
            }
        )

    manifest_path = OUTPUT_ROOT / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Built {len(manifest)} unified 4:5 preview posts")
    print(manifest_path)


if __name__ == "__main__":
    main()
