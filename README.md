# talksnwalks-agent

Agentic content pipeline for **@talksnwalks101**.

## Brand contract

Every post is 9:16, pure white, monochrome, centered, and follows exactly this vertical order:

1. **Quote** — small serif font, centered, forced to one line.
2. **Illustration** — tiny black hand-drawn line art, centered.
3. **@talksnwalks101** — small centered handle.

The illustration changes daily to match the quote/theme; the layout does not.

## MVP workflow

`quote -> illustration generation -> deterministic layout -> QA -> output`

The quote and handle are rendered by code (Pillow), not by the image model. This is intentional: it guarantees spelling, alignment and the one-line quote rule.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."
export DAY_NUMBER=1
python main.py
```

Output is written to `outputs/day_001.png`.

## GitHub Actions

The workflow can be run manually from **Actions > Daily Quote Post > Run workflow**. Add `OPENAI_API_KEY` as a repository secret before running it.

For now the workflow creates the finished branded image as an artifact. Instagram publishing and live trending-audio selection are intentionally kept behind feature flags until the Meta credentials/API access are configured and verified.
