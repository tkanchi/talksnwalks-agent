"""Women-only quote clarity rules for the live publishing pool.

The source libraries remain attribution-rich reference data. These overrides
simplify selected production copy so a reader around age 10 can understand the
message on the first read. Shared Self-Growth rows are not changed for Men.
"""

from __future__ import annotations

import re


WOMEN_QUOTE_OVERRIDES: dict[str, str] = {
    "SG006": "Improve the way you work instead of staring only at the result.",
    "SG015": "Rest before you are too tired to care about what matters.",
    "SG023": "Correct someone without making them feel small.",
    "SG031": "Belief helps, but action is what moves you forward.",
    "SG039": "Be present. See what is happening before you act.",
    "SG042": "People's reactions often say more about them than about your worth.",
    "SG045": "You feel freer when other people's opinions stop defining you.",
    "SG064": "Where you are today does not decide where you can go.",
    "SG083": "A solution that worked before may not work forever.",
    "SG084": "Move on before anger keeps you stuck in the old place.",
    "SG085": "Fear gets smaller when you explore instead of only imagining.",
    "SG094": "Build income that can keep helping you even when you are not working.",
    "SG102": "Make a money plan that fits you, not someone else.",
    "SG118": "Free time is not wasted time. It makes room for what matters.",
    "SG121": "Progress gets faster when your best attention goes to one important task first.",
    "SG125": "Do the work that matters most before the noisy work takes over.",
    "SG129": "Write down your commitments so your brain does not have to hold them all.",
    "SG139": "Talent opens the door, but steady effort takes you farther.",
    "SG155": "Strong teams grow where people practice courage, not just praise it.",
    "SG170": "Other people's choices feel lighter when you stop trying to control them.",
    "SG171": "Watch what people do. Their actions can answer many questions.",
    "SG173": "People can misunderstand you. You can still keep going.",
    "SG174": "Stop forcing closeness, approval, or agreement. Save your energy.",
    "SG179": "Growth may mean leaving pain that feels familiar for something new.",
    "SG180": "Your triggers can be clues. They do not have to control you.",
    "SG187": "Old patterns are easier to change when you stop making excuses for them.",
    "SG189": "Notice the reactions you keep repeating. They can teach you something.",
    "SG193": "Daily discipline can build a calm life without making your dreams smaller.",
    "SG204": "Your morning routine should help your life, not prove you are better.",
    "SG205": "Your life changes when your choices become stronger than your good intentions.",
    "SG211": "You grow stronger when you stop treating old habits as permanent.",
    "SG218": "Your body can help you feel confident before your mind catches up.",
    "SG220": "Confidence grows when you act before you feel fully sure.",
    "SG237": "The way you talk to yourself can help you or hold you back.",
    "SG242": "Life can be hard, but your habits still shape how you respond.",
    "SG261": "Do the hardest useful task before easy work steals your time.",
    "SG262": "Your priorities are real only when your actions show them.",
    "SG266": "You get more done when you stop perfecting work that matters less.",
    "SG267": "Start with the task that will bring the most progress or relief.",
    "SG279": "Track the actions you can control, not only the final result.",
    "SG288": "Build money habits that still work when motivation is low.",
    "SG289": "Save for your future before spending everything on today.",
    "SG291": "Do not put money into something you do not understand.",
    "SG316": "Try different ways to live instead of assuming one path fits everyone.",
    "SG339": "Treat your bedtime like an important appointment. Protect your sleep.",
    "SG363": "Failure can teach you when you return and try with more discipline.",
    "WEMP003": "One hard chapter does not define your whole story.",
    "WEMP014": "Your body deserves respect at every size and shape.",
    "WEMP018": "Your inner critic can be loud without being right.",
    "WEMP019": "Being kind at work does not mean making yourself easy to ignore.",
    "WEMP026": "Create before you know if anyone will praise it.",
    "WEMP027": "Do not talk yourself out of a chance before life answers.",
    "WEMP032": "You are worthy now. You do not have to become perfect first.",
    "WEMP034": "A boundary is not cruel just because someone wanted more access to you.",
    "WEMP040": "Notice the lessons life keeps trying to teach you.",
    "WEMP069": "Say what you mean. Do not hide your skill behind weak words.",
    "WEMP075": "Being seen gets easier each time you show up as yourself.",
    "WEMP077": "Do not let your own voice be the one that puts you down.",
    "WEMP079": "Not every misunderstanding needs a long fight to fix your image.",
    "WEMP081": "Trust grows through actions you repeat, not words that sound good.",
    "WEMP084": "Say what you need before anger becomes the only way you speak.",
    "WEMP086": "Small caring habits can remind your body that you are safe.",
    "WEMP100": "You can care about equality and still admit when you get things wrong.",
    "WEMP102": "Trust yourself before you ask everyone else what they think.",
    "WEMP103": "Confidence grows when you remember what you have learned and overcome.",
    "WEMP123": "Build money safety before you try to look successful.",
    "WEMP134": "Set clear limits for your time, energy, body, money, and attention.",
    "WEMP136": "Care for yourself like your well-being matters.",
    "WEMP152": "You can disappoint people if pleasing them means betraying yourself.",
    "WEMP161": "Outgrowing your old self can feel strange before it feels freeing.",
    "WEMP164": "Caring for your health should never mean hating your body.",
    "WEMP204": "Strong women still need rest, support, routines, and good friends.",
    "WEMP207": "Women should not need extra courage just to speak in public.",
    "WEMP212": "You are allowed to name your pain, even when others want silence.",
    "WEMP216": "Speak before your answer feels perfect. It can still be useful.",
    "WEMP229": "Stop chasing equal effort from people who keep giving you less.",
    "WEMP233": "Listen to people who are different from you without losing your own values.",
    "WEMP234": "You do not need a long speech to explain a clear limit.",
    "WEMP238": "Make room for quiet before being busy becomes your whole life.",
    "WEMP243": "Your wild side can mean truth, joy, imagination, and being fully yourself.",
    "WEMP246": "Build relationships where people share useful information and work toward the same goal.",
    "WEMP248": "Freedom is rarely given. People work together to create it.",
    "WEMP253": "Success matters, but liking the woman you become matters more.",
    "WEMP256": "Let her love science, sports, leadership, softness, strength, and whatever else fits her.",
    "WEMP268": "Your gifts cannot help anyone if you hide them forever.",
    "WEMP271": "Let your money choices match what matters to you.",
    "WEMP274": "Spend time with people who think women earning well is normal.",
    "WEMP275": "Success should give you more life, not take your life away.",
    "WEMP277": "Be more loyal to your goals than to your excuses.",
    "WEMP282": "Your worth is not measured by how much you get done.",
    "WEMP283": "Know who you are, even when someone disagrees with you.",
    "WEMP287": "Use your voice after wins and losses. Both can show leadership.",
    "WEMP289": "Hard times can change you without deciding your whole future.",
    "WEMP290": "Choose relationships where you can grow without always having to defend yourself.",
    "WEMP291": "Changing direction does not mean your earlier path was wasted.",
    "WEMP297": "Good leaders care about people and still keep clear standards.",
    "WEMP298": "Stay curious. Do not decide you know everything before listening.",
    "WEMP304": "Your inner life needs care too, not just your public life.",
    "WEMP308": "Point out double standards before people start treating them as normal.",
    "WEMP311": "Becoming someone new may mean leaving places where you had to stay quiet.",
    "WEMP314": "Your body can change and still deserve full respect.",
    "WEMP315": "You do not have to survive everything perfectly to be worthy.",
    "WEMP321": "Shame makes money harder. Learning makes money easier to manage.",
    "WEMP326": "Your creativity can be joyful, bold, private, public, or just for you.",
    "WEMP327": "Make choices today that help your future self.",
    "WEMP330": "A woman can be strong and still be open with her feelings.",
    "WEMP334": "Boundaries can protect relationships from anger that builds in silence.",
    "WEMP340": "Success means less when you lose touch with yourself.",
    "WEMP342": "Love still needs respect, honesty, and clear limits.",
    "WEMP345": "Girls and boys both need education that teaches freedom and respect.",
    "WEMP352": "Being yourself may cost approval. Pretending costs even more.",
}


_HARD_WORDS = re.compile(
    r"\b(?:"
    r"abandon|authority|conditioning|conformity|conviction|diminishment|"
    r"disposable|economic|expertise|financial independence|influence|"
    r"institution|intentional|negotiation|perfectionism|political awareness|"
    r"professional commitment|psychologically|reciprocity|resentment|scarcity|"
    r"scrutiny|solidarity|superiority|sustainable|visibility|vulnerable|"
    r"destabilize|material conditions|physiology|passivity|speculation|"
    r"authorship|obligation|capital"
    r")\b",
    re.IGNORECASE,
)


def apply_women_quote_clarity(row: dict[str, str]) -> dict[str, str]:
    """Apply a Women-only simple-language override without changing metadata."""
    updated = dict(row)
    quote_id = (updated.get("QuoteID") or updated.get("ID") or "").strip()
    if quote_id in WOMEN_QUOTE_OVERRIDES:
        updated["Quote"] = WOMEN_QUOTE_OVERRIDES[quote_id]
    return updated


def is_clear_women_quote(row: dict[str, str]) -> bool:
    """Return True when production copy is short and easy to understand."""
    quote = (row.get("Quote") or "").strip()
    words = re.findall(r"[A-Za-z’'-]+", quote)
    if not words or len(words) > 16:
        return False

    letter_counts = [len(re.sub(r"[^A-Za-z]", "", word)) for word in words]
    average_word_length = sum(letter_counts) / len(letter_counts)
    if average_word_length > 5.2:
        return False

    if ";" in quote or ":" in quote:
        return False

    if _HARD_WORDS.search(quote):
        return False

    return True
