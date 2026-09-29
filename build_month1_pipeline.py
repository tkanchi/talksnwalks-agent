from __future__ import annotations

import csv
import os
from pathlib import Path

from PIL import Image, ImageDraw

import build_reel
from apply_audio import apply_audio_to_build
from audio_quality_gate import require_real_audio
import build_feed_preview
from background_generator import generate_background
from illustration_pool import matched_illustration_names

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "data" / "content_plan_month_01.csv"
OUTPUT_DIR = ROOT / "outputs" / "unified"
PUBLIC_DIR = ROOT / "public" / "unified"
RUNTIME_QUOTES = OUTPUT_DIR / "quotes_runtime.csv"
ROOT_ILLUSTRATIONS = ROOT / "illustrations"
TOPICS_FILE = ROOT / "data" / "topics.csv"
HANDLE = "@talksnwalks101"
REEL_W = 1080
REEL_H = 1920
REEL_ART_MAX_W = 520
REEL_ART_MAX_H = 520
REEL_TEXT_PRIMARY = (79, 61, 52)
REEL_TEXT_SECONDARY = (112, 91, 80)
REEL_HANDLE_FILL = (110, 92, 82)

# Proven-Reel control palette: warm, soft, and visually quiet.
REEL_PALETTES = {
    "vanilla": (255, 239, 214),
    "powder": (237, 245, 252),
    "blush": (252, 226, 214),
    "seafoam": (232, 246, 238),
    "lavender": (242, 236, 250),
    "apricot": (252, 229, 207),
}

REEL_TOPIC_PALETTE = {
    "Authenticity & Identity": "blush",
    "Career": "powder",
    "Communication & Social Skills": "blush",
    "Courage": "apricot",
    "Digital Responsibility": "seafoam",
    "Discipline": "vanilla",
    "Execution": "powder",
    "Fitness": "seafoam",
    "Friendship": "blush",
    "Goals": "apricot",
    "Growth": "powder",
    "Happiness": "apricot",
    "Integrity & Character": "vanilla",
    "Justice & Equality": "blush",
    "Kindness": "blush",
    "Leadership": "powder",
    "Money Mindset": "vanilla",
    "Peace": "seafoam",
    "Purpose & Meaning": "lavender",
    "Resilience": "lavender",
    "Self-Belief": "lavender",
    "Strategy & Decision-Making": "powder",
    "Study & Learning": "powder",
}

SEO_BY_TOPIC = {
    # Caption copy deliberately uses natural Instagram-search keywords.
    # Hashtags follow the 2026 precision-over-volume approach: exactly five
    # highly relevant tags, mixing broad discovery terms with topic-specific ones.
    "Authenticity & Identity": (
        "Self-confidence and personal growth become stronger when you know yourself instead of chasing approval.",
        ["SelfConfidence", "PersonalGrowth", "SelfImprovement", "Mindset", "Motivation"],
    ),
    "Career": (
        "Career growth becomes easier when clear goals, confidence and consistent action work together.",
        ["CareerGrowth", "CareerAdvice", "Productivity", "SelfImprovement", "Motivation"],
    ),
    "Communication & Social Skills": (
        "Healthy relationships grow through better communication, listening and emotional intelligence.",
        ["HealthyRelationships", "Communication", "RelationshipAdvice", "EmotionalIntelligence", "PersonalGrowth"],
    ),
    "Courage": (
        "Confidence and courage grow when you take action even before fear disappears.",
        ["Confidence", "Courage", "SelfImprovement", "Mindset", "Motivation"],
    ),
    "Digital Responsibility": (
        "Digital wellbeing improves when healthy screen habits protect your focus and mental health.",
        ["DigitalWellbeing", "HealthyHabits", "MentalHealth", "Focus", "SelfImprovement"],
    ),
    "Discipline": (
        "Discipline, consistency and small habits are the foundation of lasting self-improvement.",
        ["Discipline", "Habits", "SelfImprovement", "Mindset", "Motivation"],
    ),
    "Execution": (
        "Deep work, focus and productivity help turn good intentions into meaningful results.",
        ["Productivity", "DeepWork", "Focus", "SelfImprovement", "Mindset"],
    ),
    "Fitness": (
        "Fitness, healthy habits and self-confidence grow through consistent daily choices.",
        ["Fitness", "HealthyHabits", "Wellness", "SelfImprovement", "Motivation"],
    ),
    "Friendship": (
        "Strong friendships grow through support, trust and healthy relationships.",
        ["Friendship", "Relationships", "HealthyRelationships", "PersonalGrowth", "Mindset"],
    ),
    "Goals": (
        "Goal setting turns motivation into clear action and steady personal growth.",
        ["Goals", "GoalSetting", "PersonalGrowth", "SelfImprovement", "Motivation"],
    ),
    "Growth": (
        "Personal growth and a growth mindset begin with staying curious, teachable and consistent.",
        ["PersonalGrowth", "GrowthMindset", "SelfImprovement", "Mindset", "Motivation"],
    ),
    "Happiness": (
        "Positive thinking, gratitude and a healthy mindset help you notice more of what is already good.",
        ["PositiveMindset", "Gratitude", "Happiness", "Mindset", "SelfImprovement"],
    ),
    "Integrity & Character": (
        "Integrity, character and strong values make everyday decisions easier to trust.",
        ["Integrity", "Character", "Values", "PersonalGrowth", "Mindset"],
    ),
    "Justice & Equality": (
        "Equality and women empowerment grow when girls are raised with confidence, choice and opportunity.",
        ["Equality", "WomenEmpowerment", "Confidence", "PersonalGrowth", "Mindset"],
    ),
    "Kindness": (
        "Kindness, empathy and emotional intelligence can change the way someone experiences a hard day.",
        ["Kindness", "Empathy", "EmotionalIntelligence", "PersonalGrowth", "Motivation"],
    ),
    "Leadership": (
        "Leadership, accountability and personal growth start with taking responsibility for the next action.",
        ["Leadership", "Accountability", "PersonalGrowth", "Business", "Motivation"],
    ),
    "Money Mindset": (
        "Money mindset improves when financial goals, better decisions and consistent habits work together.",
        ["MoneyMindset", "FinancialFreedom", "PersonalFinance", "SelfImprovement", "Motivation"],
    ),
    "Peace": (
        "Inner peace and mental wellness grow when you protect your energy, slow down and practice self-care.",
        ["InnerPeace", "MentalHealth", "SelfCare", "Wellness", "Mindset"],
    ),
    "Purpose & Meaning": (
        "Purpose, resilience and personal growth give difficult seasons a clearer reason to keep going.",
        ["Purpose", "Resilience", "PersonalGrowth", "SelfImprovement", "Motivation"],
    ),
    "Resilience": (
        "Resilience and mental strength grow when setbacks become lessons instead of endings.",
        ["Resilience", "MentalStrength", "SelfImprovement", "Mindset", "Motivation"],
    ),
    "Self-Belief": (
        "Self-belief and confidence grow when you take action before you feel completely ready.",
        ["SelfBelief", "Confidence", "SelfImprovement", "Mindset", "Motivation"],
    ),
    "Strategy & Decision-Making": (
        "Better decision making, productivity and focus help protect your time, energy and priorities.",
        ["DecisionMaking", "Productivity", "Focus", "SelfImprovement", "Mindset"],
    ),
    "Study & Learning": (
        "Study motivation gets stronger when learning, consistency and a growth mindset work together.",
        ["StudyMotivation", "Learning", "GrowthMindset", "SelfImprovement", "Motivation"],
    ),
}

SEO_BY_CATEGORY = {
    "Relationships": (
        "Healthy relationships grow through communication, trust and emotional intelligence.",
        ["Relationships", "HealthyRelationships", "Communication", "PersonalGrowth", "Mindset"],
    ),
    "Family": (
        "Strong family relationships grow through care, communication and consistent support.",
        ["Family", "Parenting", "Relationships", "PersonalGrowth", "Mindset"],
    ),
    "Wellness": (
        "Wellness, mental health and healthy habits support a calmer, stronger life.",
        ["Wellness", "MentalHealth", "HealthyHabits", "SelfCare", "SelfImprovement"],
    ),
    "Mindset": (
        "Mindset, self-improvement and personal growth are built through small choices repeated daily.",
        ["Mindset", "SelfImprovement", "PersonalGrowth", "PositiveMindset", "Motivation"],
    ),
    "Business": (
        "Business growth improves when productivity, focus and better decisions work together.",
        ["Business", "Productivity", "Entrepreneurship", "CareerGrowth", "Motivation"],
    ),
    "Youth": (
        "Learning, confidence and a growth mindset become stronger through consistent practice.",
        ["Learning", "Confidence", "GrowthMindset", "SelfImprovement", "Motivation"],
    ),
    "Values": (
        "Kindness, integrity and strong values shape the decisions that build character.",
        ["Kindness", "Integrity", "Values", "PersonalGrowth", "Mindset"],
    ),
    "Lifestyle": (
        "Healthy habits and intentional daily choices support personal growth and a better lifestyle.",
        ["Lifestyle", "HealthyHabits", "PersonalGrowth", "SelfImprovement", "Motivation"],
    ),
}

def load_plan() -> list[dict[str, str]]:
    with PLAN.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No content plan rows found in {PLAN}")
    return rows


def resolve_post_number(rows: list[dict[str, str]]) -> int:
    raw = (os.getenv("POST_NUMBER") or os.getenv("DAY_NUMBER") or "1").strip()
    post_number = int(raw)
    if post_number < 1 or post_number > len(rows):
        raise ValueError(f"POST_NUMBER must be between 1 and {len(rows)}, got {post_number}")
    return post_number


def stream_for_audience(audience: str) -> str:
    value = (audience or "All").strip().lower()
    if "men" in value and "women" not in value:
        return "men"
    if any(token in value for token in ("kid", "teen", "youth", "child")):
        return "children"
    return "women"


def select_reel_illustration(
    rows: list[dict[str, str]],
    post_number: int,
) -> tuple[Path, str]:
    """Select a colored topic-aware illustration from the approved root library."""
    current_index = post_number - 1
    current_row = rows[current_index]
    stream = stream_for_audience(current_row.get("Audience", ""))

    stream_rows: list[tuple[int, dict[str, str]]] = [
        (index, row)
        for index, row in enumerate(rows)
        if stream_for_audience(row.get("Audience", "")) == stream
    ]
    position = next(
        pos for pos, (index, _) in enumerate(stream_rows)
        if index == current_index
    )

    runtime_file = OUTPUT_DIR / f"illustration_runtime_{stream}.csv"
    fieldnames = list(rows[0].keys())
    if "Theme" not in fieldnames:
        fieldnames.append("Theme")

    with runtime_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for _, row in stream_rows:
            item = dict(row)
            item["Theme"] = (item.get("Topic") or item.get("TopicCategory") or "Mindset").strip()
            writer.writerow(item)

    assignments = matched_illustration_names(
        ROOT_ILLUSTRATIONS,
        runtime_file,
        stream=stream,
        topics_file=TOPICS_FILE,
    )
    illustration_name = assignments[position]
    illustration_path = ROOT_ILLUSTRATIONS / illustration_name
    if not illustration_path.exists():
        raise FileNotFoundError(illustration_path)

    return illustration_path, illustration_name


def write_audio_runtime(rows: list[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    if "Theme" not in fieldnames:
        fieldnames.append("Theme")

    with RUNTIME_QUOTES.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            item = dict(row)
            item["Theme"] = (item.get("Topic") or item.get("TopicCategory") or "Mindset").strip()
            writer.writerow(item)


def _lighten(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(channel + (255 - channel) * amount) for channel in rgb)


def reel_palette_name(row: dict[str, str]) -> str:
    topic = (row.get("Topic") or "").strip()
    return REEL_TOPIC_PALETTE.get(topic, "vanilla")


def build_reel_background(row: dict[str, str], index: int) -> Image.Image:
    """
    Control format from proven Reels:
    - 70% plain pastel
    - 20% almost-invisible vertical tonal movement
    - 10% soft radial glow experiment
    """
    palette_name = reel_palette_name(row)
    base = REEL_PALETTES[palette_name]
    bucket = index % 10

    if bucket < 7:
        return Image.new("RGB", (REEL_W, REEL_H), base)

    lighter = _lighten(base, 0.20)

    if bucket < 9:
        mask = Image.new("L", (1, REEL_H))
        px = mask.load()
        for y in range(REEL_H):
            px[0, y] = round(34 * y / max(1, REEL_H - 1))
        mask = mask.resize((REEL_W, REEL_H), Image.Resampling.BILINEAR)
        return Image.composite(
            Image.new("RGB", (REEL_W, REEL_H), lighter),
            Image.new("RGB", (REEL_W, REEL_H), base),
            mask,
        )

    radial = Image.radial_gradient("L").resize(
        (REEL_W, REEL_H),
        Image.Resampling.BILINEAR,
    )
    radial = radial.point(lambda value: round(30 * (255 - value) / 255))
    return Image.composite(
        Image.new("RGB", (REEL_W, REEL_H), lighter),
        Image.new("RGB", (REEL_W, REEL_H), base),
        radial,
    )


def fit_source_font(draw, text: str, max_width: int = 900):
    for size in range(19, 13, -1):
        font = build_feed_preview.find_font(size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font, box
    font = build_feed_preview.find_font(13)
    return font, draw.textbbox((0, 0), text, font=font)


def compose_reel_image(
    row: dict[str, str],
    art_path: Path,
    output_path: Path,
    index: int = 0,
) -> None:
    """Render the Month-1 Reel in the proven clean editorial control format."""
    canvas = build_reel_background(row, index)
    draw = ImageDraw.Draw(canvas)

    quote = (row.get("Quote") or "").strip()
    build_feed_preview.validate_quote_585(quote)

    source_type = (row.get("SourceType") or "").strip().lower()
    book = (row.get("InspiredBy") or "").strip()
    author = (row.get("Author") or "").strip()

    quote_wrapped, quote_font, quote_h = build_feed_preview.fit_char_wrapped(
        draw,
        quote,
        char_width=40,
        max_width=900,
        max_height=420,
        max_size=48,
        min_size=36,
        spacing=12,
    )
    quote_box = draw.multiline_textbbox(
        (0, 0),
        quote_wrapped,
        font=quote_font,
        spacing=12,
        align="center",
    )
    quote_w = quote_box[2] - quote_box[0]

    art = build_feed_preview.fit_art(
        art_path,
        max_w=REEL_ART_MAX_W,
        max_h=REEL_ART_MAX_H,
    )

    handle_font = build_feed_preview.find_font(20)
    handle_w, handle_h = build_feed_preview.text_size(draw, HANDLE, handle_font)

    has_source = source_type == "inspired_by" and book and author
    source_text = f"Inspired by Book: {book} — {author}" if has_source else ""
    if has_source:
        source_font, source_box = fit_source_font(draw, source_text)
        source_w = source_box[2] - source_box[0]
        source_h = source_box[3] - source_box[1]
    else:
        source_font = None
        source_w = source_h = 0

    quote_to_source = 22 if has_source else 0
    source_to_art = 54 if has_source else 48
    art_to_handle = 38

    total_h = quote_h
    if has_source:
        total_h += quote_to_source + source_h
    total_h += source_to_art + art.height + art_to_handle + handle_h

    # Keep the visual block slightly above exact centre, matching the proven Reels.
    y = max(210, int((REEL_H - total_h) / 2) - 35)

    draw.multiline_text(
        ((REEL_W - quote_w) / 2 - quote_box[0], y - quote_box[1]),
        quote_wrapped,
        font=quote_font,
        fill=REEL_TEXT_PRIMARY,
        spacing=12,
        align="center",
    )
    y += quote_h

    if has_source:
        y += quote_to_source
        draw.text(
            ((REEL_W - source_w) / 2 - source_box[0], y - source_box[1]),
            source_text,
            font=source_font,
            fill=REEL_TEXT_SECONDARY,
        )
        y += source_h

    art_y = y + source_to_art
    art_x = (REEL_W - art.width) // 2
    canvas.paste(art, (art_x, art_y), art)

    handle_y = art_y + art.height + art_to_handle
    draw.text(
        ((REEL_W - handle_w) / 2, handle_y),
        HANDLE,
        font=handle_font,
        fill=REEL_HANDLE_FILL,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "JPEG", quality=95, optimize=True, progressive=True)

def hashtag_token(value: str) -> str:
    return "".join(ch for ch in value.title() if ch.isalnum())


def build_caption(row: dict[str, str]) -> str:
    quote = (row.get("Quote") or "").strip()
    topic = (row.get("Topic") or "Mindset").strip()
    category = (row.get("TopicCategory") or "Mindset").strip()

    seo_line, tags = SEO_BY_TOPIC.get(
        topic,
        SEO_BY_CATEGORY.get(
            category,
            (
                "Self-improvement and personal growth start with small mindset shifts repeated consistently.",
                ["Mindset", "SelfImprovement", "PersonalGrowth", "PositiveMindset", "Motivation"],
            ),
        ),
    )

    # Instagram discovery now rewards precise classification over hashtag stuffing.
    # Keep exactly five highly relevant tags and do not use our own channel hashtag.
    tags = list(dict.fromkeys(tags))[:5]
    caption_parts = [
        quote,
        seo_line,
        HANDLE,
        " ".join(f"#{tag}" for tag in tags),
    ]
    return "\n\n".join(caption_parts)


def main() -> None:
    rows = load_plan()
    post_number = resolve_post_number(rows)
    row = rows[post_number - 1]
    padded = f"{post_number:03d}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    write_audio_runtime(rows)

    feed_png = OUTPUT_DIR / f"day_{padded}_feed.png"
    reel_jpg = OUTPUT_DIR / f"day_{padded}_reel.jpg"
    fallback_wav = OUTPUT_DIR / f"day_{padded}_fallback.wav"
    reel_mp4 = PUBLIC_DIR / f"day_{padded}.mp4"
    caption_file = OUTPUT_DIR / "caption.txt"
    env_file = OUTPUT_DIR / "publish.env"

    reel_art_path, reel_illustration = select_reel_illustration(rows, post_number)

    build_feed_preview.compose(row, feed_png, index=post_number - 1)
    compose_reel_image(
        row,
        reel_art_path,
        reel_jpg,
        index=post_number - 1,
    )
    build_reel.write_fallback_audio(fallback_wav, duration=build_reel.REEL_SECONDS)
    build_reel.make_mp4(reel_jpg, fallback_wav, reel_mp4)
    caption_file.write_text(build_caption(row), encoding="utf-8")

    env_file.write_text(
        "\n".join(
            [
                "SKIP=false",
                f"DAY_NUMBER={post_number}",
                f"DAY_PADDED={padded}",
                f"POST_NUMBER={post_number}",
                f"QUOTE_ID={(row.get('QuoteID') or '').strip()}",
                f"AUDIENCE={(row.get('Audience') or '').strip()}",
                f"TOPIC={(row.get('Topic') or '').strip()}",
                f"VIDEO_FILE={reel_mp4.as_posix()}",
                f"IMAGE_FILE={reel_jpg.as_posix()}",
                f"REEL_FRAME={reel_jpg.as_posix()}",
                f"FEED_PREVIEW_FILE={feed_png.as_posix()}",
                f"ILLUSTRATION={reel_illustration}",
                f"FEED_PREVIEW_ILLUSTRATION={(row.get('Illustration') or '').strip()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stream = stream_for_audience(row.get("Audience", "All"))
    apply_audio_to_build(
        RUNTIME_QUOTES,
        OUTPUT_DIR,
        duration=build_reel.REEL_SECONDS,
        stream=stream,
    )

    if os.getenv("REQUIRE_REAL_AUDIO", "false").strip().lower() == "true":
        require_real_audio(OUTPUT_DIR)

    print(f"Built unified Post {post_number}: {(row.get('QuoteID') or '').strip()}")
    print(f"Audience: {(row.get('Audience') or '').strip()} | Topic: {(row.get('Topic') or '').strip()}")
    print(f"Colored Reel illustration: {reel_illustration}")
    print(f"Feed preview image: {feed_png}")
    print(f"Reel: {reel_mp4}")


if __name__ == "__main__":
    main()
