#!/usr/bin/env python3
"""Select a quote using the new taxonomy and occasion calendar.

Build-only by design: this script writes a JSON selection report and never calls the
Instagram API or the existing Reel publishing workflows.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_content_master import build_master  # noqa: E402

PRIORITY = {"high": 3, "medium": 2, "low": 1}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split_tokens(value: str) -> list[str]:
    separators = value.replace("|", ",")
    return [part.strip() for part in separators.split(",") if part.strip()]


def audience_matches(content_audience: str, requested: str) -> bool:
    if requested.lower() == "all":
        return True
    tokens = {token.lower() for token in split_tokens(content_audience)}
    if "all" in tokens:
        return True
    requested = requested.lower()
    aliases = {
        "children": "kids",
        "child": "kids",
        "pre-teens": "kids",
        "preteens": "kids",
        "teen": "teens",
        "adult": "adults",
    }
    requested = aliases.get(requested, requested)
    if requested == "women" and "adults" in tokens:
        return True
    if requested == "men" and "adults" in tokens:
        return True
    return requested in tokens


def market_matches(event_market: str, market: str) -> bool:
    event_market_l = event_market.lower()
    market_l = market.lower()
    return (
        "global" in event_market_l
        or market_l in event_market_l
        or "selected markets" in event_market_l
    )


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    current = date(year, month, 1)
    offset = (weekday - current.weekday()) % 7
    return current + timedelta(days=offset + (n - 1) * 7)


def resolve_event_date(rule: str, year: int) -> date | None:
    if rule.startswith("FIXED:"):
        month, day = [int(part) for part in rule.split(":", 1)[1].split("-")]
        return date(year, month, day)
    if rule.startswith("NTH_WEEKDAY:"):
        _, n, weekday_name, month_name = rule.split(":")
        weekday_lookup = {
            "MON": 0,
            "TUE": 1,
            "WED": 2,
            "THU": 3,
            "FRI": 4,
            "SAT": 5,
            "SUN": 6,
        }
        month_lookup = {
            "JAN": 1,
            "FEB": 2,
            "MAR": 3,
            "APR": 4,
            "MAY": 5,
            "JUN": 6,
            "JUL": 7,
            "AUG": 8,
            "SEP": 9,
            "OCT": 10,
            "NOV": 11,
            "DEC": 12,
        }
        return nth_weekday(year, month_lookup[month_name], weekday_lookup[weekday_name], int(n))
    # LOOKUP:ANNUAL_CALENDAR events deliberately require an annual resolved date.
    return None


def active_events(selection_date: date, market: str) -> list[dict[str, str]]:
    active: list[dict[str, str]] = []
    for event in read_csv(DATA / "events.csv"):
        if not market_matches(event["Market"], market):
            continue
        for year in {selection_date.year - 1, selection_date.year, selection_date.year + 1}:
            event_date = resolve_event_date(event["DateRule"], year)
            if event_date is None:
                continue
            start = event_date - timedelta(days=int(event["LeadDays"]))
            end = event_date + timedelta(days=int(event["FollowDays"]))
            if start <= selection_date <= end:
                enriched = dict(event)
                enriched["ResolvedDate"] = event_date.isoformat()
                active.append(enriched)
                break
    return sorted(
        active,
        key=lambda event: (
            PRIORITY.get(event["Priority"].lower(), 0),
            -abs((date.fromisoformat(event["ResolvedDate"]) - selection_date).days),
        ),
        reverse=True,
    )


def event_topics(event: dict[str, str]) -> set[str]:
    topics = {event["PrimaryTopic"].strip()}
    topics.update(part.strip() for part in event["SecondaryTopics"].split(",") if part.strip())
    return topics


def content_topics(item: dict[str, str]) -> set[str]:
    topics = {item["PrimaryTopic"].strip()}
    topics.update(part.strip() for part in item["SecondaryTopics"].split(",") if part.strip())
    return topics


def score_for_event(item: dict[str, str], event: dict[str, str]) -> int:
    score = 0
    event_primary = event["PrimaryTopic"].strip()
    if item["PrimaryTopic"].strip() == event_primary:
        score += 10
    overlap = content_topics(item) & event_topics(event)
    score += 3 * len(overlap)
    if item["SourceType"] == "original":
        score += 1
    return score


def choose(
    items: list[dict[str, str]],
    audience: str,
    rng: random.Random,
    event: dict[str, str] | None = None,
    topic: str | None = None,
) -> dict[str, str]:
    candidates = [
        item
        for item in items
        if item["Status"] == "approved" and audience_matches(item["Audience"], audience)
    ]
    if topic:
        topic_l = topic.lower()
        candidates = [
            item for item in candidates if topic_l in {value.lower() for value in content_topics(item)}
        ]
    if event:
        relevant = [item for item in candidates if content_topics(item) & event_topics(event)]
        if relevant:
            best_score = max(score_for_event(item, event) for item in relevant)
            candidates = [item for item in relevant if score_for_event(item, event) == best_score]
    if not candidates:
        raise RuntimeError("No approved content matched the requested audience/topic/event")
    return rng.choice(candidates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat(), help="Selection date, YYYY-MM-DD")
    parser.add_argument("--audience", default="All", help="Women, Men, Kids, Teens, Adults or All")
    parser.add_argument("--market", default="India")
    parser.add_argument("--topic", default="", help="Optional canonical topic filter")
    parser.add_argument("--occasion", default="", help="Force a named occasion for testing")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--output", default=str(OUTPUTS / "content_selection.json"))
    args = parser.parse_args()

    selection_date = date.fromisoformat(args.date)
    master_path = DATA / "generated" / "content_master.csv"
    build_master(master_path)
    items = read_csv(master_path)
    events = read_csv(DATA / "events.csv")

    selected_event: dict[str, str] | None = None
    if args.occasion:
        selected_event = next(
            (event for event in events if event["Event"].lower() == args.occasion.lower()),
            None,
        )
        if selected_event is None:
            raise RuntimeError(f"Unknown occasion: {args.occasion}")
    else:
        active = active_events(selection_date, args.market)
        selected_event = active[0] if active else None

    rng = random.Random(args.seed)
    item = choose(
        items,
        audience=args.audience,
        rng=rng,
        event=selected_event,
        topic=args.topic or None,
    )

    report = {
        "mode": "build-only",
        "date": selection_date.isoformat(),
        "market": args.market,
        "requested_audience": args.audience,
        "requested_topic": args.topic or None,
        "active_or_forced_event": selected_event,
        "selection": item,
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Selected {item['ContentID']}: {item['Quote']}")
    print(f"Audience: {item['Audience']} | Topic: {item['PrimaryTopic']} | Highlight: {item['Highlight']}")
    if selected_event:
        print(f"Occasion context: {selected_event['Event']}")
    else:
        print("Occasion context: evergreen")
    print(f"Report: {output.relative_to(ROOT)}")
    print("No publishing action was performed.")


if __name__ == "__main__":
    main()
