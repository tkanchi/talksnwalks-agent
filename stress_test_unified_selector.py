from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import timedelta
from pathlib import Path

from PIL import Image

from build_feed_preview import CANVAS_H, CANVAS_W, compose
from build_unified_shadow import build_caption, build_hashtags
from select_next_post import (
    append_history,
    build_selection,
    clean,
    history_entries,
    is_book_eligible,
    load_history,
    output_payload,
    safe_for_youth_context,
    write_history,
)

ROOT = Path(__file__).resolve().parent
SEED_HISTORY = ROOT / 'shadow_logs' / 'unified' / 'selection_history_active.json'
OUTPUT_ROOT = ROOT / 'outputs' / 'unified_stress'
PREVIEW_DIR = OUTPUT_ROOT / 'previews'
MANIFEST_FILE = OUTPUT_ROOT / 'manifest.json'
REPORT_FILE = OUTPUT_ROOT / 'report.json'
STRESS_HISTORY_FILE = OUTPUT_ROOT / 'stress_history.json'
COUNT = 30
ROBOTIC_SUPPORT_PREFIXES = (
    'this perspective ', 'the book ', 'the lesson ', 'the takeaway ',
    'this takeaway ', 'the idea ',
)
MIN_UNIQUE_ILLUSTRATIONS = 20
MAX_ILLUSTRATION_USES = 3


def reset_outputs() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


def max_run(values: list[str]) -> int:
    best = current = 0
    previous = None
    for value in values:
        if value == previous:
            current += 1
        else:
            current = 1
            previous = value
        best = max(best, current)
    return best


def main() -> None:
    reset_outputs()
    seed = load_history(SEED_HISTORY)
    seed_entries = history_entries(seed)
    if not seed_entries:
        raise RuntimeError('Active shadow history is empty')

    history = json.loads(json.dumps(seed))
    last_seed_date = max(clean(row.get('selection_date')) for row in seed_entries)
    from datetime import datetime
    start = datetime.strptime(last_seed_date, '%Y-%m-%d').date() + timedelta(days=1)

    manifest: list[dict] = []
    for index in range(COUNT):
        on_date = start + timedelta(days=index)
        selection = build_selection(on_date, history)
        if not is_book_eligible(selection):
            raise RuntimeError(f'Ineligible selection: {selection.get("QuoteID")}')
        payload = output_payload(selection)
        if payload['audience'] in {'Kids', 'Teens', 'Kids|Teens'} and not safe_for_youth_context(selection):
            raise RuntimeError(f'Youth safety failed: {payload["quote_id"]}')

        support = payload['supporting_text'].casefold()
        if support.startswith(ROBOTIC_SUPPORT_PREFIXES):
            raise RuntimeError(f'Robotic SupportingText survived audit: {payload["quote_id"]}')

        hashtags = build_hashtags(selection)
        caption = build_caption(selection, hashtags)
        if len(hashtags) != 5 or not caption:
            raise RuntimeError(f'Caption package failed: {payload["quote_id"]}')
        payload['hashtags'] = hashtags
        payload['caption'] = caption

        preview_path = PREVIEW_DIR / f'{index + 1:02d}_{on_date.isoformat()}_{payload["quote_id"]}.png'
        compose(selection, preview_path, index=len(seed_entries) + index)
        with Image.open(preview_path) as image:
            if image.size != (CANVAS_W, CANVAS_H):
                raise RuntimeError(f'Unexpected preview dimensions: {preview_path} {image.size}')

        append_history(history, selection)
        manifest.append(payload)

    quote_ids = [row['quote_id'] for row in manifest]
    books = [row['book'] for row in manifest]
    topics = [row['topic'] for row in manifest]
    objects = [row['object_id'] for row in manifest]
    backgrounds = [row['background'] for row in manifest]
    audiences = [row['audience'] for row in manifest]
    events = [row['event'] for row in manifest if row['event']]
    scores = [int(row.get('illustration_score', 0)) for row in manifest]
    captions = [row['caption'] for row in manifest]
    illustration_counts = Counter(objects)

    if len(set(quote_ids)) != COUNT:
        raise RuntimeError('Duplicate QuoteIDs in stress window')
    if set(quote_ids) & {clean(row.get('quote_id')) for row in seed_entries}:
        raise RuntimeError('Stress window reused a seeded QuoteID')
    if any(a == b for a, b in zip(objects, objects[1:])):
        raise RuntimeError('Immediate illustration repeat in stress window')
    if len(set(captions)) != COUNT:
        raise RuntimeError('Duplicate captions in stress window')
    if len(illustration_counts) < MIN_UNIQUE_ILLUSTRATIONS:
        raise RuntimeError(
            f'Illustration variety too low: {len(illustration_counts)} < {MIN_UNIQUE_ILLUSTRATIONS}'
        )
    if max(illustration_counts.values()) > MAX_ILLUSTRATION_USES:
        raise RuntimeError(
            f'Illustration reused too often: {max(illustration_counts.values())} > {MAX_ILLUSTRATION_USES}'
        )

    report = {
        'seed_entries': len(seed_entries),
        'stress_count': COUNT,
        'start_date': start.isoformat(),
        'end_date': (start + timedelta(days=COUNT - 1)).isoformat(),
        'unique_quote_ids': len(set(quote_ids)),
        'unique_books': len(set(books)),
        'unique_topics': len(set(topics)),
        'unique_illustrations': len(illustration_counts),
        'max_illustration_uses': max(illustration_counts.values()),
        'unique_backgrounds': len(set(backgrounds)),
        'unique_captions': len(set(captions)),
        'occasion_posts': len(events),
        'illustration_score_min': min(scores),
        'illustration_score_average': round(sum(scores) / len(scores), 1),
        'zero_semantic_illustrations': sum(score <= 0 for score in scores),
        'robotic_support_lines': sum(
            row['supporting_text'].casefold().startswith(ROBOTIC_SUPPORT_PREFIXES)
            for row in manifest
        ),
        'max_consecutive_same_book': max_run(books),
        'max_consecutive_same_topic': max_run(topics),
        'max_consecutive_same_illustration': max_run(objects),
        'book_counts': dict(Counter(books).most_common()),
        'topic_counts': dict(Counter(topics).most_common()),
        'illustration_counts': dict(illustration_counts.most_common()),
        'audience_metadata_counts': dict(Counter(audiences).most_common()),
        'background_counts': dict(Counter(backgrounds).most_common()),
        'event_counts': dict(Counter(events).most_common()),
    }

    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding='utf-8')
    write_history(STRESS_HISTORY_FILE, history)

    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
