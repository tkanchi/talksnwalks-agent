from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / 'data' / 'content_plan_month_01.csv'
SUPPORT = ROOT / 'data' / 'supporting_text_month_01.csv'
MIN_WORDS = 6
MAX_WORDS = 14


def clean(value: object) -> str:
    return str(value or '').strip()


def word_count(text: str) -> int:
    return len([part for part in clean(text).replace('—', ' ').split() if part])


def main() -> None:
    with SUPPORT.open(newline='', encoding='utf-8') as handle:
        support_rows = list(csv.DictReader(handle))

    approved = {
        clean(row.get('QuoteID')): clean(row.get('SupportingText'))
        for row in support_rows
        if clean(row.get('QCStatus')).lower() == 'approved'
    }
    if len(approved) != 70:
        raise RuntimeError(f'Expected 70 approved supporting lines, found {len(approved)}')

    duplicate_lines = len(set(approved.values())) != len(approved)
    if duplicate_lines:
        raise RuntimeError('Supporting text must be unique across all 70 posts')

    for quote_id, text in approved.items():
        count = word_count(text)
        if not MIN_WORDS <= count <= MAX_WORDS:
            raise RuntimeError(
                f'{quote_id} supporting text has {count} words; expected {MIN_WORDS}-{MAX_WORDS}'
            )

    with PLAN.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0].keys()) if rows else []

    plan_ids = {clean(row.get('QuoteID')) for row in rows}
    missing = sorted(plan_ids - set(approved))
    extra = sorted(set(approved) - plan_ids)
    if missing or extra:
        raise RuntimeError(f'Supporting text QuoteID mismatch. Missing={missing}; extra={extra}')

    for row in rows:
        row['SupportingText'] = approved[clean(row.get('QuoteID'))]

    with PLAN.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    counts = [word_count(row['SupportingText']) for row in rows]
    print(f'Applied and QC-approved supporting text to {len(rows)} posts')
    print(f'Word-count range: {min(counts)}-{max(counts)}')
    print(f'Unique supporting lines: {len(set(row["SupportingText"] for row in rows))}')


if __name__ == '__main__':
    main()
