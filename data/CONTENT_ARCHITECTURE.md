# TalksNWalks Content Architecture

This layer is intentionally data-driven. Adding a new topic or occasion should normally require adding rows to CSV files, not adding a new Python script or workflow.

## Core files

- `data/topics.csv` — canonical topic taxonomy and default Highlight mapping.
- `data/events.csv` — occasion/awareness-day calendar with lead windows.
- `data/content_master_template.csv` — future unified quote schema.

Existing audience libraries remain valid and unchanged for now:

- `data/quotes.csv` — current women/live library
- `data/men/quotes.csv`
- `data/children/quotes.csv`
- `data/references/*.csv`

Migration into a unified master library should happen gradually after the publishing system is stable.

## Content model

Each content item can answer three separate questions:

1. **Audience** — who is it for? (`Women`, `Men`, `Kids`, `Teens`, `Adults`, `All`)
2. **Topic** — what is it about? (`Friendship`, `Fitness`, `CEO Mindset`, `Mother`, etc.)
3. **Occasion** — when is it especially relevant? (`Valentine's Day`, `Mother's Day`, `New Year`, etc.)

A quote may have one primary topic and multiple secondary topics.

## Instagram Highlight strategy

Keep Highlights broad enough to remain usable. Recommended starting set:

- Love
- Friends
- Family
- Fitness
- Mindset
- CEO
- Kids
- Occasions

Do not create a separate Highlight for every tiny topic. Promote a topic into its own Highlight only when enough strong content exists to make it useful.

## Occasion lead windows

`LeadDays` in `events.csv` allows the future selector to begin surfacing relevant content before the actual day.

Example: New Year has a seven-day lead window, so content can progress from reflection to letting go to new beginnings instead of posting only on January 1.

`FollowDays` allows a limited amount of after-event content when appropriate.

## Date rules

Supported design forms:

- `FIXED:MM-DD` — fixed annual date.
- `NTH_WEEKDAY:N:DAY:MON` — e.g. second Sunday in May.
- `LOOKUP:ANNUAL_CALENDAR` — date varies each year and must be resolved from a trusted calendar before scheduling.

Variable religious/lunar observances must never be guessed from a fixed date.

## Future selector priority

When smart selection is implemented, the intended order is:

1. Check active occasion windows.
2. Filter by audience.
3. Choose a relevant primary/secondary topic.
4. Avoid recently used quote IDs and illustration tags.
5. Select matching illustration assets.
6. Fall back to evergreen content if no occasion applies.

## Folder strategy

Asset folders are useful for organization, but topic-specific code is not.

Future illustration folders can look like:

```text
illustrations/
  friendship/
  fitness/
  family/
  couples/
  ceo/
  childhood/
```

The selection engine should use metadata/tags to choose among them.

## Source and attribution rules

`SourceType` in the future master content file should distinguish at least:

- `original`
- `inspired_by`
- `direct_quote`
- `public_domain`

Never present an `inspired_by` paraphrase as a verbatim quote from an author. Direct quotations should be short, accurately sourced, and verified before publishing.

### Display attribution

- `original`: no author name is required. Treat it as Talk N Walks original/editorial copy.
- `inspired_by`: do **not** place the author's name after the sentence as if they said those exact words. When useful, add `Inspired by <book/source>` in the caption or metadata.
- `direct_quote`: display the verified speaker/author and retain a source reference in the library.
- `public_domain`: display the verified author/speaker and retain the source/work when known.
- Unknown or social-media-only attribution is not sufficient for a named-author quote.

The visual itself should stay uncluttered. Attribution may appear in the caption rather than on the artwork unless the author is central to the post.

## Current safety rule

This architecture is not yet wired into the live workflows. The existing women, men, and children publishing behavior should remain unchanged until the selector is built and tested in build-only mode.
