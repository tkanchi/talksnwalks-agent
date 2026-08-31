from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def clean(value: object) -> str:
    return str(value or "").strip()


def max_run(values: list[str]) -> int:
    best = current = 0
    previous = None
    for value in values:
        if value and value == previous:
            current += 1
        else:
            current = 1 if value else 0
        best = max(best, current)
        previous = value
    return best


def repeat_pairs(rows: list[dict], field: str, distance: int) -> list[dict]:
    repeats: list[dict] = []
    for index, row in enumerate(rows):
        value = clean(row.get(field))
        if not value:
            continue
        for prior in range(max(0, index - distance), index):
            if clean(rows[prior].get(field)) == value:
                repeats.append(
                    {
                        "field": field,
                        "value": value,
                        "first_index": prior + 1,
                        "second_index": index + 1,
                        "gap": index - prior,
                    }
                )
    return repeats


def tag_overlap_pairs(rows: list[dict], distance: int = 3) -> list[dict]:
    overlaps: list[dict] = []
    for index, row in enumerate(rows):
        current = {clean(tag).lower() for tag in row.get("illustration_tags", []) if clean(tag)}
        for prior in range(max(0, index - distance), index):
            before = {
                clean(tag).lower()
                for tag in rows[prior].get("illustration_tags", [])
                if clean(tag)
            }
            shared = sorted(current & before)
            if shared:
                overlaps.append(
                    {
                        "first_index": prior + 1,
                        "second_index": index + 1,
                        "gap": index - prior,
                        "shared_tags": shared,
                        "first_illustration": clean(rows[prior].get("illustration")),
                        "second_illustration": clean(row.get("illustration")),
                    }
                )
    return overlaps


def support_prefix(text: str, words: int = 3) -> str:
    tokens = re.findall(r"[A-Za-z0-9’'-]+", clean(text).casefold())
    return " ".join(tokens[:words])


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a long-horizon unified shadow simulation.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    rows = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Stress manifest is empty or invalid")

    count = len(rows)
    fields = {
        "audience": [clean(row.get("audience")) for row in rows],
        "topic_category": [clean(row.get("topic_category")) for row in rows],
        "topic": [clean(row.get("topic")) for row in rows],
        "book": [clean(row.get("book")) for row in rows],
        "object_id": [clean(row.get("object_id")) for row in rows],
        "illustration": [clean(row.get("illustration")) for row in rows],
        "background": [clean(row.get("background")) for row in rows],
        "event": [clean(row.get("event")) for row in rows],
    }

    exact_hashtag_sets = Counter(" ".join(row.get("hashtags", [])) for row in rows)
    support_prefixes = Counter(support_prefix(row.get("supporting_text", "")) for row in rows)

    report = {
        "count": count,
        "date_start": clean(rows[0].get("selection_date")),
        "date_end": clean(rows[-1].get("selection_date")),
        "unique_quote_ids": len({clean(row.get("quote_id")) for row in rows}),
        "unique_books": len(set(fields["book"])),
        "unique_topics": len(set(fields["topic"])),
        "unique_topic_categories": len(set(fields["topic_category"])),
        "unique_audiences": len(set(fields["audience"])),
        "unique_objects": len(set(fields["object_id"])),
        "unique_illustrations": len(set(fields["illustration"])),
        "unique_backgrounds": len(set(fields["background"])),
        "audience_counts": dict(Counter(fields["audience"])),
        "category_counts": dict(Counter(fields["topic_category"])),
        "topic_counts": dict(Counter(fields["topic"])),
        "book_counts": dict(Counter(fields["book"])),
        "event_counts": dict(Counter(value for value in fields["event"] if value)),
        "background_counts": dict(Counter(fields["background"])),
        "max_consecutive_same_book": max_run(fields["book"]),
        "max_consecutive_same_topic": max_run(fields["topic"]),
        "max_consecutive_same_object": max_run(fields["object_id"]),
        "max_consecutive_same_event": max_run(fields["event"]),
        "book_repeats_within_5": repeat_pairs(rows, "book", 5),
        "topic_repeats_within_3": repeat_pairs(rows, "topic", 3),
        "object_repeats_within_5": repeat_pairs(rows, "object_id", 5),
        "illustration_tag_overlaps_within_3": tag_overlap_pairs(rows, 3),
        "hashtag_set_counts": dict(exact_hashtag_sets),
        "support_prefix_counts": dict(support_prefixes),
        "most_repeated_hashtag_set": max(exact_hashtag_sets.values()),
        "most_repeated_support_prefix": max(support_prefixes.values()),
    }

    hard_checks = {
        "30_rows": count == 30,
        "unique_quote_ids": report["unique_quote_ids"] == count,
        "book_only": all(clean(row.get("source_type")) == "inspired_by" for row in rows),
        "support_present": all(clean(row.get("supporting_text")) for row in rows),
        "book_author_present": all(clean(row.get("book")) and clean(row.get("author")) for row in rows),
        "published_false": all(row.get("published") is False for row in rows),
        "five_hashtags": all(len(row.get("hashtags", [])) == 5 for row in rows),
        "no_back_to_back_book": report["max_consecutive_same_book"] <= 1,
        "no_back_to_back_topic": report["max_consecutive_same_topic"] <= 1,
        "no_back_to_back_object": report["max_consecutive_same_object"] <= 1,
    }
    report["hard_checks"] = hard_checks
    report["warnings"] = []

    if report["unique_books"] < 20:
        report["warnings"].append("Book diversity below 20 unique books across 30 posts")
    if report["unique_topics"] < 12:
        report["warnings"].append("Topic diversity below 12 unique topics across 30 posts")
    if report["unique_illustrations"] < 20:
        report["warnings"].append("Illustration diversity below 20 unique illustrations across 30 posts")
    if report["most_repeated_hashtag_set"] >= 8:
        report["warnings"].append("One exact hashtag set repeats at least 8 times")
    if report["most_repeated_support_prefix"] >= 4:
        report["warnings"].append("SupportingText openings show repeated template language")
    if len(report["illustration_tag_overlaps_within_3"]) >= 8:
        report["warnings"].append("Frequent semantic illustration-tag overlap within three posts")

    if not all(hard_checks.values()):
        failed = [name for name, ok in hard_checks.items() if not ok]
        raise RuntimeError(f"Stress test hard checks failed: {failed}")

    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Unified shadow 30-post stress report",
        "",
        f"- Window: {report['date_start']} to {report['date_end']}",
        f"- Posts: {count}",
        f"- Unique books: {report['unique_books']}",
        f"- Unique topics: {report['unique_topics']}",
        f"- Unique illustrations: {report['unique_illustrations']}",
        f"- Unique backgrounds: {report['unique_backgrounds']}",
        f"- Occasion posts: {sum(report['event_counts'].values())}",
        f"- Book repeats within 5 posts: {len(report['book_repeats_within_5'])}",
        f"- Topic repeats within 3 posts: {len(report['topic_repeats_within_3'])}",
        f"- Object repeats within 5 posts: {len(report['object_repeats_within_5'])}",
        f"- Illustration tag overlaps within 3 posts: {len(report['illustration_tag_overlaps_within_3'])}",
        f"- Most repeated exact hashtag set: {report['most_repeated_hashtag_set']} times",
        f"- Most repeated SupportingText three-word opening: {report['most_repeated_support_prefix']} times",
        "",
        "## Audience metadata distribution",
    ]
    for name, value in sorted(report["audience_counts"].items()):
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Topic category distribution"])
    for name, value in sorted(report["category_counts"].items()):
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Occasions"])
    if report["event_counts"]:
        for name, value in sorted(report["event_counts"].items()):
            lines.append(f"- {name}: {value}")
    else:
        lines.append("- None")
    lines.extend(["", "## Warnings"])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None")

    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Stress test hard checks passed")
    print(json.dumps({key: report[key] for key in (
        "unique_books", "unique_topics", "unique_illustrations", "unique_backgrounds",
        "most_repeated_hashtag_set", "most_repeated_support_prefix", "warnings"
    )}, indent=2))


if __name__ == "__main__":
    main()
