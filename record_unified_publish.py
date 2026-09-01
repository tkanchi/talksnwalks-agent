from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_FILE = ROOT / "outputs" / "unified_live" / "package.json"
RESULT_FILE = ROOT / "outputs" / "unified_live" / "publish_result.json"
HISTORY_FILE = ROOT / "published_logs" / "unified" / "selection_history.json"
AUDIT_DIR = ROOT / "published_logs" / "unified"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    package = load_json(PACKAGE_FILE)
    result = load_json(RESULT_FILE)

    if result.get("status") != "PUBLISHED":
        raise RuntimeError(f"Publish result is not PUBLISHED: {result}")
    if package.get("mode") != "live_candidate":
        raise RuntimeError(f"Unexpected package mode: {package.get('mode')}")
    if package.get("published") is not False:
        raise RuntimeError("Candidate package must still say published=false before audit recording")

    package_id = str(package.get("package_id") or "").strip()
    selection_date = str(package.get("selection_date") or "").strip()
    quote_id = str(package.get("quote_id") or "").strip()
    if not package_id or not selection_date or not quote_id:
        raise RuntimeError("Package is missing package_id, selection_date, or quote_id")

    if HISTORY_FILE.exists():
        history = load_json(HISTORY_FILE)
    else:
        history = {"version": 1, "mode": "live", "selections": []}

    selections = history.setdefault("selections", [])
    if any(row.get("package_id") == package_id for row in selections):
        raise RuntimeError(f"Package already recorded: {package_id}")
    if any(row.get("quote_id") == quote_id for row in selections):
        raise RuntimeError(f"QuoteID already published in unified live history: {quote_id}")
    if any(row.get("selection_date") == selection_date for row in selections):
        raise RuntimeError(
            f"A unified live post is already recorded for {selection_date}; "
            "one-post-per-day protection is active"
        )

    history["version"] = 1
    history["mode"] = "live"
    history_entry = {
        "selection_date": selection_date,
        "quote_id": quote_id,
        "audience": package.get("audience", ""),
        "topic_category": package.get("topic_category", ""),
        "topic": package.get("topic", ""),
        "book": package.get("book", ""),
        "author": package.get("author", ""),
        "event_id": package.get("event_id", ""),
        "event": package.get("event", ""),
        "event_date": package.get("event_date", ""),
        "object_id": package.get("object_id", ""),
        "illustration": package.get("illustration", ""),
        "illustration_tags": package.get("illustration_tags", []),
        "placement": package.get("placement", ""),
        "background": package.get("background", ""),
        "reason": package.get("reason", ""),
        "mode": "live",
        "published": True,
        "package_id": package_id,
        "media_id": result.get("media_id", ""),
    }
    selections.append(history_entry)

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")

    audit = {
        "status": "PUBLISHED",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "package": {**package, "mode": "live", "published": True},
        "publish_result": result,
    }
    audit_path = AUDIT_DIR / f"{package_id}.json"
    if audit_path.exists():
        raise RuntimeError(f"Audit log already exists: {audit_path}")
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print(f"Recorded unified publish audit: {audit_path.relative_to(ROOT)}")
    print(f"Unified live history entries: {len(selections)}")


if __name__ == "__main__":
    main()
