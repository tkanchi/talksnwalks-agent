# Quote grounding rules

Talk N Walks publishes modern book ideas as **grounded paraphrases**, not as
sentences invented to sound as if an author wrote them.

## Required review standard

Review each book-inspired line against reliable book-linked material before it
is approved. Preserve the complete idea: a reader should understand the lesson
without having to guess what a vague word, missing object, or compressed phrase
means.

The source CSV wording is the production wording. Women/Men runtime code must
not simplify or paraphrase it again.

## Grounding manifest

`part_01.csv` and `part_02.csv` are the reviewed snapshots for every
book-inspired source row that has a complete book and author attribution.

`ReviewStatus=approved_grounded_paraphrase` means the line was approved as a
paraphrase faithful to the cited book idea. It does **not** mean the sentence is
a verbatim quotation from the author.

If a quote, book, or author changes, the matching manifest row must be reviewed
and updated. The master audit rejects mismatches.

## Direct quotations

Use a direct quotation from a modern copyrighted book only when it is brief,
verified word-for-word from a reliable source, and intentionally presented as a
direct quote. Do not convert a paraphrase into an author quotation merely
because the wording sounds strong.
