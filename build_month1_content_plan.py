from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUOTES = ROOT / 'data' / 'quotes_master_clean.csv'
OBJECTS = ROOT / 'data' / 'illustration_objects.csv'
OUTPUT = ROOT / 'data' / 'content_plan_month_01.csv'

# Current approved book-only pool has general and women-specific material.
# Men/youth book libraries will be added separately before restoring those quotas.
TARGET = 50
BACKGROUND_FAMILIES = [
    'vanilla', 'seafoam', 'powder', 'blush', 'lavender',
    'apricot', 'ice', 'mint', 'petal', 'sky',
]
AUDIENCE_QUOTAS = {
    'all': 40,
    'women': 10,
}

SEMANTIC_TOPIC_KEYWORDS = {
    'Leadership': ('leadership', 'leader', 'lead '),
    'Self-Belief': ('confidence', 'believe in yourself', 'self-belief'),
    'Authenticity & Identity': ('authentic', 'identity', 'pretend', 'be yourself', 'yourself', 'self-knowledge'),
    'Friendship': ('friend', 'friendship', 'circle'),
    'Brothers': ('brother', 'brothers'),
    'Mother': ('mother', ' mom ', "mom's"),
    'Father': ('father', ' dad ', "dad's"),
    'Family': ('family', 'home'),
    'Career': ('career', 'job', 'workplace'),
    'Entrepreneurship': ('business', 'startup', 'entrepreneur'),
    'Strategy & Decision-Making': ('strategy', 'decision', 'choice', 'priorit'),
    'Discipline': ('discipline', 'consistency', 'routine', 'practice', 'habit'),
    'Goals': ('goal', 'dream', 'vision'),
    'Peace': ('peace', 'calm', 'quiet'),
    'Rest & Recovery': ('rest', 'sleep', 'recover'),
    'Health': ('health', 'wellness', 'hydrate'),
    'Fitness': ('fitness', 'workout', 'gym', 'training', 'body'),
    'Reading & Books': ('book', 'read', 'library'),
    'Study & Learning': ('study', 'learn', 'homework', 'curiosity'),
    'Travel & Adventure': ('travel', 'adventure', 'journey', 'trip'),
    'Kindness': ('kind', 'kindness', 'compassion'),
    'Love': ('love', 'romance', 'relationship'),
    'Hope': ('hope', 'optimis'),
    'Resilience': ('resilien', 'setback', 'comeback', 'recover from'),
    'Courage': ('courage', 'brave', 'bold', 'fear'),
    'Purpose & Meaning': ('purpose', 'meaning', 'calling'),
    'Gratitude': ('gratitude', 'grateful', 'thankful', 'thank you'),
}


def clean(v: object) -> str:
    return str(v or '').strip()


def split_pipe(v: str) -> set[str]:
    return {x.strip() for x in clean(v).split('|') if x.strip()}


def split_tags(v: str) -> set[str]:
    return {x.strip().lower() for x in clean(v).split(',') if x.strip()}


def audience_bucket(audience: str) -> str:
    vals = split_pipe(audience)
    if vals and vals <= {'Kids', 'Teens'}:
        return 'youth'
    if vals == {'Women'}:
        return 'women'
    if vals == {'Men'}:
        return 'men'
    return 'all'


def is_book_based(row: dict[str, str]) -> bool:
    return (
        clean(row.get('SourceType')).lower() == 'inspired_by'
        and bool(clean(row.get('InspiredBy')))
        and bool(clean(row.get('Author')))
    )


def source_score(row: dict[str, str]) -> int:
    score = 100 if is_book_based(row) else 0
    if audience_bucket(row.get('Audience', '')) == 'all':
        score += 12
    if clean(row.get('SupportingText')):
        score += 2
    return score


def choose_quotes(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[audience_bucket(row.get('Audience', ''))].append(row)

    for bucket in grouped:
        grouped[bucket].sort(key=lambda r: (-source_score(r), clean(r.get('Topic')), clean(r.get('QuoteID'))))

    selected: list[dict[str, str]] = []
    topic_counts: Counter[str] = Counter()

    for bucket, quota in AUDIENCE_QUOTAS.items():
        candidates = grouped.get(bucket, [])
        picked_ids: set[str] = set()

        for row in candidates:
            if len(picked_ids) >= quota:
                break
            topic = clean(row.get('Topic'))
            if topic_counts[topic] >= 4:
                continue
            qid = clean(row.get('QuoteID'))
            selected.append(row)
            picked_ids.add(qid)
            topic_counts[topic] += 1

        if len(picked_ids) < quota:
            for row in candidates:
                if len(picked_ids) >= quota:
                    break
                qid = clean(row.get('QuoteID'))
                if qid in picked_ids:
                    continue
                selected.append(row)
                picked_ids.add(qid)
                topic_counts[clean(row.get('Topic'))] += 1

    buckets = defaultdict(list)
    for row in selected:
        buckets[audience_bucket(row.get('Audience', ''))].append(row)
    order = ['all', 'women', 'all']
    mixed: list[dict[str, str]] = []
    while len(mixed) < TARGET:
        progressed = False
        for bucket in order:
            if buckets[bucket]:
                mixed.append(buckets[bucket].pop(0))
                progressed = True
                if len(mixed) == TARGET:
                    break
        if not progressed:
            break

    if len(mixed) != TARGET:
        raise RuntimeError(f'Expected {TARGET} selected book-inspired quotes, got {len(mixed)}')
    return mixed


def filename_for_stem(stem: str) -> str:
    stem = clean(stem)
    if stem.endswith('_02'):
        return f'{stem}.png'
    return f'{stem}_01.png'


def semantic_topics(quote: dict[str, str]) -> set[str]:
    # Use only the actual copy shown to the audience. Legacy Theme fields can be
    # stale and must not override clear quote semantics for illustration choice.
    text = ' ' + ' '.join([
        clean(quote.get('Quote')),
        clean(quote.get('SupportingText')),
    ]).lower() + ' '
    found = set()
    for topic, needles in SEMANTIC_TOPIC_KEYWORDS.items():
        if any(needle in text for needle in needles):
            found.add(topic)
    return found


def object_score(obj: dict[str, str], quote: dict[str, str]) -> int:
    topic = clean(quote.get('Topic'))
    hints = semantic_topics(quote)
    qtags = split_tags(quote.get('IllustrationTags', ''))
    primary = split_pipe(obj.get('PrimaryTopics', ''))
    secondary = split_pipe(obj.get('SecondaryTopics', ''))
    otags = split_tags(obj.get('Tags', ''))
    score = 0

    if hints:
        score += 170 * len(hints & primary)
        score += 90 * len(hints & secondary)
        if topic in primary:
            score += 25
        if topic in secondary:
            score += 15
    else:
        if topic in primary:
            score += 100
        if topic in secondary:
            score += 55

    score += 8 * len(qtags & otags)
    return score


def assign_objects(quotes: list[dict[str, str]], objects: list[dict[str, str]]) -> list[tuple[dict[str, str], dict[str, str], str]]:
    usage: Counter[str] = Counter()
    recent: list[str] = []
    placement_usage: Counter[str] = Counter()
    prev_placement = ''
    result = []

    for quote in quotes:
        ranked = sorted(
            objects,
            key=lambda o: (
                -object_score(o, quote),
                usage[clean(o.get('ObjectID'))],
                clean(o.get('ObjectID')),
            ),
        )
        eligible = [o for o in ranked if clean(o.get('ObjectID')) not in recent[-5:]] or ranked
        obj = eligible[0]
        oid = clean(obj.get('ObjectID'))
        usage[oid] += 1
        recent.append(oid)

        prefs = [p for p in clean(obj.get('PreferredPlacements')).split('|') if p]
        if not prefs:
            prefs = ['bottom_left', 'bottom_right']
        placement_candidates = [p for p in prefs if p != prev_placement] or prefs
        placement = min(placement_candidates, key=lambda p: (placement_usage[p], p))
        placement_usage[placement] += 1
        prev_placement = placement
        result.append((quote, obj, placement))

    return result


def main() -> None:
    with QUOTES.open(newline='', encoding='utf-8') as f:
        quote_rows = [
            r for r in csv.DictReader(f)
            if clean(r.get('QualityStatus')) == 'approved' and is_book_based(r)
        ]
    with OBJECTS.open(newline='', encoding='utf-8') as f:
        object_rows = [r for r in csv.DictReader(f) if clean(r.get('StyleStatus')) == 'approved']

    selected = choose_quotes(quote_rows)
    mapped = assign_objects(selected, object_rows)

    fields = [
        'PostNumber', 'QuoteID', 'Quote', 'SupportingText', 'Audience', 'TopicCategory', 'Topic',
        'SemanticHints', 'SourceType', 'InspiredBy', 'Author', 'SourceLine', 'ObjectID', 'Illustration',
        'Placement', 'BackgroundFamily', 'Occasion', 'PlanStatus'
    ]
    rows = []
    for idx, (quote, obj, placement) in enumerate(mapped, start=1):
        source_line = f"Inspired by Book: {clean(quote.get('InspiredBy'))} — {clean(quote.get('Author'))}"
        rows.append({
            'PostNumber': f'{idx:03d}',
            'QuoteID': clean(quote.get('QuoteID')),
            'Quote': clean(quote.get('Quote')),
            'SupportingText': clean(quote.get('SupportingText')),
            'Audience': clean(quote.get('Audience')),
            'TopicCategory': clean(quote.get('TopicCategory')),
            'Topic': clean(quote.get('Topic')),
            'SemanticHints': '|'.join(sorted(semantic_topics(quote))),
            'SourceType': clean(quote.get('SourceType')),
            'InspiredBy': clean(quote.get('InspiredBy')),
            'Author': clean(quote.get('Author')),
            'SourceLine': source_line,
            'ObjectID': clean(obj.get('ObjectID')),
            'Illustration': filename_for_stem(obj.get('FileStem', '')),
            'Placement': placement,
            'BackgroundFamily': BACKGROUND_FAMILIES[(idx - 1) % len(BACKGROUND_FAMILIES)],
            'Occasion': clean(quote.get('Occasion')),
            'PlanStatus': 'mapped',
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f'Built {len(rows)} mapped book-inspired posts -> {OUTPUT}')
    print('Audience mix:', dict(Counter(audience_bucket(r['Audience']) for r in rows)))
    print('Unique topics:', len({r['Topic'] for r in rows}))
    print('Unique illustrations:', len({r['Illustration'] for r in rows}))
    print('Book-inspired:', sum(1 for r in rows if r['SourceLine']))


if __name__ == '__main__':
    main()
